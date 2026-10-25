import ctypes
from ctypes import wintypes
import os
import threading
import time

LAUNCH_URL = "googleplaygames://launch/?id=com.kiloo.subwaysurf&lid=1&pid=1"
SHORTCUT = os.path.join(
    os.environ.get("APPDATA", ""),
    r"Microsoft\Windows\Start Menu\Programs\Google Play Games\Subway Surfers.lnk",
)
WINDOW_HINTS = ("subway surfers", "google play games", "subway", "surfers")

COOLDOWN_S = {
    "LEFT": 0.15,
    "RIGHT": 0.15,
    "JUMP": 0.35,
    "SLIDE": 0.35,
    "HOVER": 0.60,
}

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL

PUL = ctypes.POINTER(ctypes.c_ulong)


class KeyBdInput(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]


class HardwareInput(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]


class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput), ("mi", MouseInput), ("hi", HardwareInput)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("ii", Input_I)]


INPUT_KEYBOARD = 1
KEYEVENTF_KEYDOWN = 0x0000
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

KEY_MAPPINGS = {
    "LEFT": [
        (0x25, 0x4B, True),   # Left Arrow
        (0x41, 0x1E, False),  # A
    ],
    "RIGHT": [
        (0x27, 0x4D, True),   # Right Arrow
        (0x44, 0x20, False),  # D
    ],
    "JUMP": [
        (0x26, 0x48, True),   # Up Arrow
        (0x57, 0x11, False),  # W
    ],
    "SLIDE": [
        (0x28, 0x50, True),   # Down Arrow
        (0x53, 0x1F, False),  # S
    ],
    "HOVER": [
        (0x20, 0x39, False),  # Space
    ],
}


def launch_subway_surfers():
    if os.path.isfile(SHORTCUT):
        os.startfile(SHORTCUT)
        return SHORTCUT
    try:
        os.startfile(LAUNCH_URL)
        return LAUNCH_URL
    except Exception:
        return "Not found"


def _title(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def find_game_hwnd():
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _lp):
        if user32.IsWindowVisible(hwnd):
            t = _title(hwnd).lower()
            if any(h in t for h in WINDOW_HINTS) and "handsurf" not in t:
                found.append(hwnd)
        return True

    user32.EnumWindows(cb, 0)
    return found[0] if found else None


def is_game_focused(hwnd):
    if not hwnd:
        return False
    fg = user32.GetForegroundWindow()
    if fg == hwnd:
        return True
    pid_game = wintypes.DWORD()
    pid_fg = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_game))
    user32.GetWindowThreadProcessId(fg, ctypes.byref(pid_fg))
    return pid_game.value != 0 and pid_game.value == pid_fg.value


def focus_game(hwnd):
    if not hwnd or is_game_focused(hwnd):
        return bool(hwnd)
    try:
        fg = user32.GetForegroundWindow()
        cur = kernel32.GetCurrentThreadId()
        pid = wintypes.DWORD()
        other = user32.GetWindowThreadProcessId(fg, ctypes.byref(pid))
        user32.AttachThreadInput(cur, other, True)
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
        user32.AttachThreadInput(cur, other, False)
        return True
    except Exception:
        return False


def _send_single_key(vk, scan, down=True, extended=False):
    extra = ctypes.c_ulong(0)
    flags = KEYEVENTF_SCANCODE
    if not down:
        flags |= KEYEVENTF_KEYUP
    if extended:
        flags |= KEYEVENTF_EXTENDEDKEY

    ii_ = Input_I()
    ii_.ki = KeyBdInput(vk, scan, flags, 0, ctypes.pointer(extra))
    inp = INPUT(INPUT_KEYBOARD, ii_)
    user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(inp))


def tap_keys_async(key_list, hold_sec=0.045):
    def worker():
        for vk, scan, ext in key_list:
            _send_single_key(vk, scan, down=True, extended=ext)
        time.sleep(hold_sec)
        for vk, scan, ext in key_list:
            _send_single_key(vk, scan, down=False, extended=ext)

    threading.Thread(target=worker, daemon=True).start()


def deploy_hoverboard(hwnd=None):
    def worker():
        # Spacebar double-tap
        _send_single_key(0x20, 0x39, down=True, extended=False)
        time.sleep(0.04)
        _send_single_key(0x20, 0x39, down=False, extended=False)
        time.sleep(0.05)
        _send_single_key(0x20, 0x39, down=True, extended=False)
        time.sleep(0.04)
        _send_single_key(0x20, 0x39, down=False, extended=False)

        # In-window screen double-click
        if hwnd:
            rect = wintypes.RECT()
            user32.GetClientRect(hwnd, ctypes.byref(rect))
            cx = (rect.right - rect.left) // 2
            cy = (rect.bottom - rect.top) // 2
            lparam = (cy << 16) | (cx & 0xFFFF)
            WM_LBUTTONDOWN = 0x0201
            WM_LBUTTONUP = 0x0202
            user32.PostMessageW(hwnd, WM_LBUTTONDOWN, 1, lparam)
            user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam)
            time.sleep(0.04)
            user32.PostMessageW(hwnd, WM_LBUTTONDOWN, 1, lparam)
            user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam)

    threading.Thread(target=worker, daemon=True).start()


class GameController:
    def __init__(self):
        self._last = {name: 0.0 for name in KEY_MAPPINGS}
        self.enabled = True
        self.hwnd = None

    def ready(self, gesture):
        if gesture not in KEY_MAPPINGS:
            return False
        return (time.monotonic() - self._last[gesture]) >= COOLDOWN_S[gesture]

    def cooldown_left(self, gesture):
        if gesture not in KEY_MAPPINGS:
            return 0.0
        return max(0.0, COOLDOWN_S[gesture] - (time.monotonic() - self._last[gesture]))

    def fire(self, gesture):
        if not self.enabled or gesture not in KEY_MAPPINGS or not self.ready(gesture):
            return False

        self.hwnd = find_game_hwnd() or self.hwnd
        if self.hwnd:
            focus_game(self.hwnd)

        if gesture == "HOVER":
            deploy_hoverboard(self.hwnd)
        else:
            tap_keys_async(KEY_MAPPINGS[gesture], hold_sec=0.045)

        self._last[gesture] = time.monotonic()
        return True
