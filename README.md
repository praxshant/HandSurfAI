# HandSurf AI

Play **Subway Surfers** on PC using your webcam and real-time hand gestures.

## Controls

### Steering (Left & Right)
Multiple gestures are supported for lane switching:

| Method | Left | Right | Description |
|---|---|---|---|
| **Hand Tilt** | Tilt hand left ($\le -16^\circ$) | Tilt hand right ($\ge +16^\circ$) | Tilt your wrist like a steering wheel. Straighten to center to re-arm. |
| **Pointing** | Point index finger left | Point index finger right | Extend your index finger horizontally in either direction. |
| **Thumb** | Thumb out to left | Thumb out to right | Make a fist and stick your thumb out sideways. |
| **Swipe** | Flick hand left | Flick hand right | Quick flick of your hand in the air. |
| **Position** | Hand in left lane | Hand in right lane | Shift your hand left or right of center. |

### Actions (Jump, Slide, Hoverboard)

| Action | Pose | Motion | Keys Dispatched |
|---|---|---|---|
| **Jump** | 1 Finger up (index extended) | Flick hand up | Up Arrow + `W` |
| **Slide / Roll** | Fist (all fingers folded) | Flick hand down | Down Arrow + `S` |
| **Hoverboard** | Two fingers up (peace sign) | — | Space |
| **Neutral** | Open hand upright | Centered | None |

## Installation & Setup

Requires Python 3.10 and a webcam.

### Quick Start (PowerShell)

```powershell
cd C:\Users\ACER\OneDrive\Desktop\HandSurfAI
.\run.ps1
```

### Manual Setup

```powershell
cd C:\Users\ACER\OneDrive\Desktop\HandSurfAI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

## Tips for Best Performance

- **Hand Tilt**: Tilting your wrist left or right gives the lowest latency for quick consecutive lane changes.
- **Calibration**: Press `c` at any time while holding your hand in a comfortable resting position to set your neutral center.
- **Window Focus**: If your game window isn't receiving key inputs, click anywhere inside the Subway Surfers window once. Press `q` or `Esc` to quit the overlay.
