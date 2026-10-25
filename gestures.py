from collections import deque
import math

WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

TILT_THRESH_DEG = 16.0
TILT_RESET_DEG = 8.0
SWIPE_THRESH = 0.05
SMOOTH = 0.40
HISTORY = 4
LANE_DEADZONE = 0.12
RETURN_ZONE = 0.05
EXTEND_MARGIN = 0.02


def dist(p1, p2):
    return math.hypot(p1.x - p2.x, p1.y - p2.y)


def palm_center(landmarks):
    pts = (landmarks[WRIST], landmarks[INDEX_MCP], landmarks[PINKY_MCP])
    return (
        sum(p.x for p in pts) / 3,
        sum(p.y for p in pts) / 3,
    )


def is_extended_up(lms, tip, pip, mcp):
    return lms[tip].y < lms[pip].y - 0.02 and lms[tip].y < lms[mcp].y - 0.03


def is_folded(lms, tip, pip, mcp, wrist=0):
    return (lms[tip].y > lms[pip].y - 0.01) or (dist(lms[tip], lms[wrist]) < dist(lms[pip], lms[wrist]) * 1.15)


def get_hand_tilt_deg(landmarks):
    # Wrist to middle knuckle angle relative to vertical
    wrist = landmarks[WRIST]
    mcp = landmarks[MIDDLE_MCP]
    dx = mcp.x - wrist.x
    dy = mcp.y - wrist.y
    return math.degrees(math.atan2(dx, -dy))


def is_pointing_horiz(landmarks, direction="left"):
    tip = landmarks[INDEX_TIP]
    pip = landmarks[INDEX_PIP]
    mcp = landmarks[INDEX_MCP]
    dx = tip.x - mcp.x
    dy = tip.y - mcp.y
    length = math.hypot(dx, dy)
    if length < 0.06 or abs(dx) < 1.1 * abs(dy):
        return False
    mid_fold = is_folded(landmarks, MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP)
    rng_fold = is_folded(landmarks, RING_TIP, RING_PIP, RING_MCP)
    pnk_fold = is_folded(landmarks, PINKY_TIP, PINKY_PIP, PINKY_MCP)
    if not (mid_fold and rng_fold and pnk_fold):
        return False
    return (dx < -0.05) if direction == "left" else (dx > 0.05)


def is_thumb_pointing(landmarks, direction="left"):
    tip = landmarks[THUMB_TIP]
    mcp = landmarks[THUMB_MCP]
    dx = tip.x - mcp.x
    mid_fold = is_folded(landmarks, MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP)
    rng_fold = is_folded(landmarks, RING_TIP, RING_PIP, RING_MCP)
    pnk_fold = is_folded(landmarks, PINKY_TIP, PINKY_PIP, PINKY_MCP)
    idx_fold = is_folded(landmarks, INDEX_TIP, INDEX_PIP, INDEX_MCP)
    if not (idx_fold and mid_fold and rng_fold and pnk_fold):
        return False
    return (dx < -0.05) if direction == "left" else (dx > 0.05)


class GestureTracker:
    def __init__(self):
        self.sx = None
        self.sy = None
        self.raw_hist = deque(maxlen=HISTORY)
        self.origin = (0.5, 0.5)
        self.prev_pose = None
        self.current_pose = None
        self.tilt_armed = True
        self.lane_armed = True
        self.current_tilt_deg = 0.0

    def reset_origin(self, x=0.5, y=0.5):
        self.origin = (x, y)
        self.tilt_armed = True
        self.lane_armed = True

    def update(self, landmarks):
        raw_x, raw_y = palm_center(landmarks)
        if self.sx is None:
            self.sx, self.sy = raw_x, raw_y
        else:
            self.sx = SMOOTH * raw_x + (1 - SMOOTH) * self.sx
            self.sy = SMOOTH * raw_y + (1 - SMOOTH) * self.sy

        self.raw_hist.append((raw_x, raw_y))

        # 1. Hand tilt steering
        tilt = get_hand_tilt_deg(landmarks)
        self.current_tilt_deg = tilt
        if self.tilt_armed:
            if tilt < -TILT_THRESH_DEG:
                self.tilt_armed = False
                self.current_pose = "TILT_LEFT"
                return "LEFT", (self.sx, self.sy)
            elif tilt > TILT_THRESH_DEG:
                self.tilt_armed = False
                self.current_pose = "TILT_RIGHT"
                return "RIGHT", (self.sx, self.sy)
        elif abs(tilt) < TILT_RESET_DEG:
            self.tilt_armed = True

        # 2. Pointing left or right
        if is_pointing_horiz(landmarks, "left"):
            pose = "POINT_LEFT"
            if self.prev_pose != pose:
                self.prev_pose = pose
                self.current_pose = pose
                return "LEFT", (self.sx, self.sy)
        elif is_pointing_horiz(landmarks, "right"):
            pose = "POINT_RIGHT"
            if self.prev_pose != pose:
                self.prev_pose = pose
                self.current_pose = pose
                return "RIGHT", (self.sx, self.sy)

        # 3. Thumb left or right (hitchhiker sign)
        elif is_thumb_pointing(landmarks, "left"):
            pose = "THUMB_LEFT"
            if self.prev_pose != pose:
                self.prev_pose = pose
                self.current_pose = pose
                return "LEFT", (self.sx, self.sy)
        elif is_thumb_pointing(landmarks, "right"):
            pose = "THUMB_RIGHT"
            if self.prev_pose != pose:
                self.prev_pose = pose
                self.current_pose = pose
                return "RIGHT", (self.sx, self.sy)

        # 4. Standard poses: hoverboard, jump, slide
        elif (
            is_extended_up(landmarks, INDEX_TIP, INDEX_PIP, INDEX_MCP)
            and is_extended_up(landmarks, MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP)
            and not is_extended_up(landmarks, RING_TIP, RING_PIP, RING_MCP)
            and not is_extended_up(landmarks, PINKY_TIP, PINKY_PIP, PINKY_MCP)
        ):
            pose = "HOVER"
            if self.prev_pose != pose:
                self.prev_pose = pose
                self.current_pose = pose
                return "HOVER", (self.sx, self.sy)

        elif (
            is_extended_up(landmarks, INDEX_TIP, INDEX_PIP, INDEX_MCP)
            and is_folded(landmarks, MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP)
            and is_folded(landmarks, RING_TIP, RING_PIP, RING_MCP)
            and is_folded(landmarks, PINKY_TIP, PINKY_PIP, PINKY_MCP)
        ):
            pose = "JUMP"
            if self.prev_pose != pose:
                self.prev_pose = pose
                self.current_pose = pose
                return "JUMP", (self.sx, self.sy)

        elif (
            is_folded(landmarks, INDEX_TIP, INDEX_PIP, INDEX_MCP)
            and is_folded(landmarks, MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP)
            and is_folded(landmarks, RING_TIP, RING_PIP, RING_MCP)
            and is_folded(landmarks, PINKY_TIP, PINKY_PIP, PINKY_MCP)
        ):
            pose = "SLIDE"
            if self.prev_pose != pose:
                self.prev_pose = pose
                self.current_pose = pose
                return "SLIDE", (self.sx, self.sy)
        else:
            self.prev_pose = None
            self.current_pose = None

        # 5. Fast swipe flicks
        if len(self.raw_hist) >= 3:
            dx = self.raw_hist[-1][0] - self.raw_hist[0][0]
            dy = self.raw_hist[-1][1] - self.raw_hist[0][1]
            if abs(dx) > SWIPE_THRESH or abs(dy) > SWIPE_THRESH:
                self.raw_hist.clear()
                if abs(dx) > abs(dy):
                    if dx < -SWIPE_THRESH:
                        return "LEFT", (self.sx, self.sy)
                    elif dx > SWIPE_THRESH:
                        return "RIGHT", (self.sx, self.sy)
                else:
                    if dy < -SWIPE_THRESH:
                        return "JUMP", (self.sx, self.sy)
                    elif dy > SWIPE_THRESH:
                        return "SLIDE", (self.sx, self.sy)

        # 6. Hand lane position shift
        ox = self.origin[0]
        dx = self.sx - ox
        if self.lane_armed:
            if dx < -LANE_DEADZONE:
                self.lane_armed = False
                return "LEFT", (self.sx, self.sy)
            elif dx > LANE_DEADZONE:
                self.lane_armed = False
                return "RIGHT", (self.sx, self.sy)
        elif abs(dx) < RETURN_ZONE:
            self.lane_armed = True

        return None, (self.sx, self.sy)


if __name__ == "__main__":
    class P:
        def __init__(self, x, y):
            self.x, self.y = x, y

    def hand(palm_x=0.5, palm_y=0.5, index=False, middle=False):
        lms = [P(palm_x, palm_y)] * 21
        lms[WRIST] = P(palm_x, palm_y + 0.15)
        lms[INDEX_MCP] = P(palm_x - 0.04, palm_y - 0.02)
        lms[MIDDLE_MCP] = P(palm_x, palm_y - 0.02)
        lms[PINKY_MCP] = P(palm_x + 0.04, palm_y - 0.02)

        lms[INDEX_PIP] = P(palm_x - 0.04, palm_y - 0.08)
        lms[MIDDLE_PIP] = P(palm_x, palm_y - 0.08)
        lms[RING_PIP] = P(palm_x + 0.03, palm_y - 0.08)
        lms[PINKY_PIP] = P(palm_x + 0.05, palm_y - 0.07)

        lms[INDEX_TIP] = P(palm_x - 0.04, palm_y - (0.16 if index else 0.04))
        lms[MIDDLE_TIP] = P(palm_x, palm_y - (0.16 if middle else 0.04))
        lms[RING_TIP] = P(palm_x + 0.03, palm_y - 0.04)
        lms[PINKY_TIP] = P(palm_x + 0.05, palm_y - 0.04)
        return lms

    t = GestureTracker()
    assert t.update(hand(index=True))[0] == "JUMP"
    t = GestureTracker()
    assert t.update(hand(index=True, middle=True))[0] == "HOVER"
    t = GestureTracker()
    assert t.update(hand())[0] == "SLIDE"
    print("gestures ok")
