import ctypes
import time

import cv2
import mediapipe as mp

from game_controller import (
    COOLDOWN_S,
    GameController,
    find_game_hwnd,
    is_game_focused,
    launch_subway_surfers,
)
from gestures import GestureTracker, LANE_DEADZONE, TILT_THRESH_DEG

WIN = "HandSurf AI"
FONT = cv2.FONT_HERSHEY_SIMPLEX
VK_Q, VK_C, VK_ESC = 0x51, 0x43, 0x1B
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x00000008
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010


def _overlay_noactivate():
    hwnd = ctypes.windll.user32.FindWindowW(None, WIN)
    if not hwnd:
        return
    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOPMOST)
    ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)


def _held(vk):
    return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x0001)


GESTURE_DESCRIPTIONS = {
    "TILT_LEFT": "TILT LEFT  [<--]",
    "POINT_LEFT": "POINT LEFT [<-]",
    "THUMB_LEFT": "THUMB LEFT [<-]",
    "LEFT": "LEFT  [<--]",
    "TILT_RIGHT": "TILT RIGHT [-->]",
    "POINT_RIGHT": "POINT RIGHT [->]",
    "THUMB_RIGHT": "THUMB RIGHT [->]",
    "RIGHT": "RIGHT [-->]",
    "JUMP": "JUMP  [^ UP]",
    "SLIDE": "SLIDE [v DOWN]",
    "HOVER": "HOVERBOARD [ACTIVE]",
}


def draw_hud(frame, status, active_label, fired_recent, fps, tracker, ctrl, hwnd):
    h, w = frame.shape[:2]

    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (380, 190), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)
    cv2.rectangle(frame, (10, 10), (380, 190), (70, 70, 70), 1)

    cv2.putText(frame, "HandSurf AI", (20, 34), FONT, 0.7, (0, 255, 180), 2)
    s_col = (0, 255, 0) if "DETECTED" in status else (0, 160, 255)
    cv2.putText(frame, status, (20, 58), FONT, 0.52, s_col, 1)

    label = active_label or "—"
    g_col = (0, 255, 255) if fired_recent else (200, 200, 200)
    cv2.putText(frame, f"ACTION: {label}", (20, 84), FONT, 0.62, g_col, 2)

    tilt = tracker.current_tilt_deg
    tilt_status = "CENTER"
    tilt_col = (180, 180, 180)
    if tilt < -TILT_THRESH_DEG:
        tilt_status = "STEER LEFT"
        tilt_col = (0, 255, 180)
    elif tilt > TILT_THRESH_DEG:
        tilt_status = "STEER RIGHT"
        tilt_col = (0, 255, 180)
    cv2.putText(frame, f"TILT: {tilt:+.0f} deg ({tilt_status})", (20, 108), FONT, 0.48, tilt_col, 1)

    cv2.putText(frame, f"FPS: {fps:.0f}", (20, 130), FONT, 0.48, (180, 180, 180), 1)
    if is_game_focused(hwnd):
        cv2.putText(frame, "GAME: FOCUSED", (140, 130), FONT, 0.48, (0, 255, 0), 1)
    elif hwnd:
        cv2.putText(frame, "CLICK GAME TO FOCUS", (140, 130), FONT, 0.45, (0, 200, 255), 1)
    else:
        cv2.putText(frame, "GAME: NOT FOUND", (140, 130), FONT, 0.45, (0, 120, 255), 1)

    cool = max(ctrl.cooldown_left(g) for g in COOLDOWN_S)
    bar_w = int(340 * (1 - min(1.0, cool / 0.35)))
    cv2.rectangle(frame, (20, 142), (360, 154), (40, 40, 40), -1)
    cv2.rectangle(frame, (20, 142), (20 + bar_w, 154), (0, 200, 255), -1)

    ox = tracker.origin[0] if tracker.origin else 0.5
    lane = "CENTER"
    if tracker.sx is not None:
        if tracker.sx < ox - LANE_DEADZONE:
            lane = "LEFT"
        elif tracker.sx > ox + LANE_DEADZONE:
            lane = "RIGHT"
    lane_text = f"LANE: [ {'*' if lane=='LEFT' else ' '} LEFT | {'*' if lane=='CENTER' else ' '} CENTER | {'*' if lane=='RIGHT' else ' '} RIGHT ]"
    cv2.putText(frame, lane_text, (20, 176), FONT, 0.45, (0, 255, 180) if lane != "CENTER" else (170, 170, 170), 1)

    if tracker.origin:
        ox_px = int(tracker.origin[0] * w)
        deadzone_px = int(LANE_DEADZONE * w)
        cv2.line(frame, (ox_px - deadzone_px, 0), (ox_px - deadzone_px, h), (40, 40, 60), 1)
        cv2.line(frame, (ox_px + deadzone_px, 0), (ox_px + deadzone_px, h), (40, 40, 60), 1)

    if tracker.sx is not None:
        px, py = int(tracker.sx * w), int(tracker.sy * h)
        cv2.circle(frame, (px, py), 9, (0, 255, 180), -1)
        cv2.circle(frame, (px, py), 12, (255, 255, 255), 1)

    cv2.rectangle(frame, (0, h - 28), (w, h), (15, 15, 15), -1)
    cv2.putText(
        frame,
        "Steer: Tilt Hand / Point / Thumb / Swipe | 1 Finger: JUMP | Fist: SLIDE | 2: HOVER | c: Calibrate",
        (8, h - 8),
        FONT,
        0.38,
        (220, 220, 220),
        1,
    )


def main():
    print("HandSurf AI starting...")
    target = launch_subway_surfers()
    print("Game shortcut/URL:", target)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise SystemExit("No webcam found. Plug one in and retry.")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    mp_hands = mp.solutions.hands
    mp_draw = mp.solutions.drawing_utils
    tracker = GestureTracker()
    ctrl = GameController()

    prev_t = time.monotonic()
    fps = 0.0
    overlay_set = False

    last_action = None
    last_action_time = 0.0

    print("Subway Surfers controller ready!")
    print("Steer Left/Right: Tilt hand, Point index finger, Thumb out, or Swipe!")
    print("Jump: 1 finger up. Slide: Fist. Hoverboard: 2 fingers up.")
    print("q or Esc to quit | c to calibrate center.")

    with mp_hands.Hands(
        max_num_hands=1,
        model_complexity=0,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6,
    ) as hands:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb)

            now = time.monotonic()
            dt = now - prev_t
            prev_t = now
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1 / dt)

            status = "NO HAND"
            if result.multi_hand_landmarks:
                status = "HAND DETECTED"
                lms = result.multi_hand_landmarks[0]
                mp_draw.draw_landmarks(frame, lms, mp_hands.HAND_CONNECTIONS)
                gesture, _ = tracker.update(lms.landmark)
                if gesture:
                    fired = ctrl.fire(gesture)
                    if fired:
                        action_name = tracker.current_pose or gesture
                        last_action = GESTURE_DESCRIPTIONS.get(action_name, gesture)
                        last_action_time = now
            else:
                tracker.sx = tracker.sy = None
                tracker.raw_hist.clear()
                tracker.prev_pose = None
                tracker.current_pose = None

            fired_recent = (now - last_action_time) < 0.6
            display_label = last_action if fired_recent else None
            if not display_label and tracker.current_pose:
                display_label = GESTURE_DESCRIPTIONS.get(tracker.current_pose, tracker.current_pose)

            hwnd = find_game_hwnd()
            draw_hud(frame, status, display_label, fired_recent, fps, tracker, ctrl, hwnd)

            cv2.imshow(WIN, frame)
            if not overlay_set:
                _overlay_noactivate()
                overlay_set = True

            cv2.waitKey(1)
            if _held(VK_Q) or _held(VK_ESC):
                break
            if _held(VK_C) and tracker.sx is not None:
                tracker.reset_origin(tracker.sx, tracker.sy)
                print(f"Origin calibrated to ({tracker.sx:.2f}, {tracker.sy:.2f})")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
