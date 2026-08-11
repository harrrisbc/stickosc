# StickOSC

Maps your Xbox controller to OSC messages you can remap in a YAML file.

Works with TouchDesigner, Max/MSP, Unreal, Processing, and any OSC listener.

## Quick start

```bash
cd stickosc
pip install -r requirements.txt
python stickosc.py
```

Plug in an Xbox (or compatible) pad first. You should see a live status board:

```
StickOSC  ·  Xbox → OSC
────────────────────────────────────────
controller  Xbox Controller #0          ✓
sending to  127.0.0.1:9000
...
```

Default OSC target: **`127.0.0.1:9000`**

## Demo (no controller)

```bash
python stickosc.py --demo
```

Simulates stick / trigger motion so you can verify OSC without hardware.

## CLI options

| Flag | Meaning |
|------|---------|
| `--host 192.168.1.10` | OSC destination IP |
| `--port 8000` | OSC destination port |
| `--config path.yaml` | custom mapping file |
| `--index 0` | which pad (if several) |
| `--demo` | simulate inputs |
| `--verbose` | log button presses |
| `--static` | no pulse animation |

## OSC addresses (default)

| Control | Address | Range |
|---------|---------|-------|
| A B X Y / LB RB / Back Start / L3 R3 | `/xbox/btn/...` | `0` or `1` |
| D-pad | `/xbox/dpad/x`, `/xbox/dpad/y` | `-1` / `0` / `1` |
| Left stick | `/xbox/stick/left/x`, `.../y` | `-1…1` (up = +1) |
| Right stick | `/xbox/stick/right/x`, `.../y` | `-1…1` |
| Triggers | `/xbox/trigger/left`, `.../right` | `0…1` |

Edit `mapping.yaml` to change any address — no code edits needed. If the file is missing, StickOSC writes a default copy on first run.

## Listen test (Python)

In another terminal:

```bash
python tools/osc_listen.py --port 9000
```

Then run `python stickosc.py --demo` and watch addresses print.

## Notes

- Stick deadzone default: `0.12` (in `mapping.yaml`)
- Sends **only on change** (not a flood every frame)
- `Ctrl+C` to quit cleanly
- Set `NO_COLOR=1` to disable ANSI colours
