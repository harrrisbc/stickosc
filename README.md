# StickOSC

Maps your **Xbox** or **PS5 (DualSense)** controller to **OSC** and/or **MIDI** messages you can remap in a YAML file.

Works with TouchDesigner, Max/MSP, Unreal, Processing, Ableton, Bitwig, and any OSC / MIDI listener.

## Quick start

```bash
cd stickosc
pip install -r requirements.txt
python stickosc.py
```

### GUI

```bash
python stickosc.py --gui
# or
python gui_app.py
```

Controls: Start/Stop, OSC host/port, MIDI on/off, layout (`auto`/`xbox`/`ps5`), pad index, demo mode, live stick meters. **Save** writes settings into `mapping.yaml`.

### Standalone app (Mac / Windows)

**Mac — clone from GitHub + build (one shot):**

```bash
# pygame needs Python 3.9–3.13 (3.14 will fail). Recommended:
brew install python@3.12

curl -fsSL https://raw.githubusercontent.com/harrrisbc/stickosc/cursor/gui-standalone-app-5a6a/tools/clone_and_build_mac.sh | bash
```

If you already tried with Python 3.14 and it failed:

```bash
brew install python@3.12
rm -rf ~/stickosc/.venv
PYTHON=python3.12 ~/stickosc/tools/build_mac.sh
# or re-run:
PYTHON=python3.12 bash ~/stickosc/tools/clone_and_build_mac.sh
open ~/stickosc/dist/StickOSC.app
```

This clones into `~/stickosc`, installs deps in a venv, and builds `~/stickosc/dist/StickOSC.app`.

Or step by step:

```bash
# already have the repo
chmod +x tools/build_mac.sh
./tools/build_mac.sh
open dist/StickOSC.app

# clone + build helper (from anywhere on a Mac)
chmod +x tools/clone_and_build_mac.sh
./tools/clone_and_build_mac.sh
# optional: BRANCH=main DEST=~/src/stickosc ./tools/clone_and_build_mac.sh
```

**Windows (cmd) → `dist\StickOSC.exe`:**

```bat
tools\build_win.bat
```

The Mac build uses `stickosc.macos.spec`. Frozen apps store user config at `~/.stickosc/mapping.yaml` (copied from the bundled default on first run).

Plug in an Xbox or PS5 pad first. CLI mode shows a live status board:

```
StickOSC  ·  Pad → OSC / MIDI
────────────────────────────────────────
controller  DualSense Wireless Contro…  ✓
layout      ps5 (auto)
OSC         127.0.0.1:9000
MIDI        off
...
```

Default OSC target: **`127.0.0.1:9000`**

## Controllers (Xbox + PS5)

StickOSC auto-detects the pad from its name and picks a button/axis **layout**.

| Logical key | Xbox | PS5 |
|-------------|------|-----|
| `a` / `b` / `x` / `y` | A B X Y | Cross Circle Square Triangle |
| `lb` / `rb` | LB RB | L1 R1 |
| `lt` / `rt` | LT RT | L2 R2 |
| `back` / `start` | Back/View Start/Menu | Create Options |
| `l3` / `r3` | stick clicks | stick clicks |

OSC addresses stay under `/xbox/...` by default so existing patches keep working — remap in YAML if you want `/ps5/...`.

```bash
# force a layout if auto-detect is wrong
python stickosc.py --layout ps5
python stickosc.py --layout xbox

# or in mapping.yaml
# controller:
#   layout: auto   # or xbox / ps5
```

## MIDI output

Enable MIDI (keeps OSC on by default):

```bash
python stickosc.py --midi
```

Or set `midi.enabled: true` in `mapping.yaml`.

StickOSC opens / creates a port named **`StickOSC`** (virtual when possible). Point your DAW or synth at that port.

```bash
# see ports
python stickosc.py --list-midi-ports

# MIDI only
python stickosc.py --midi --no-osc

# custom port / channel
python stickosc.py --midi --midi-port "IAC Driver Bus 1" --midi-channel 2
```

### Default MIDI map

| Control | MIDI | Range |
|---------|------|-------|
| A B X Y / LB RB / Back Start / L3 R3 | Note On/Off (60, 62, 64…) | velocity 100 |
| Left / right sticks | CC 1–4 | `-1…1` → `0…127` (center ≈ 64) |
| Triggers LT / RT | CC 11 / 12 | `0…1` → `0…127` |
| D-pad X / Y | CC 20 / 21 | `-1 / 0 / +1` → `0 / 64 / 127` |

Edit the `midi:` block on each control in `mapping.yaml` — no code edits needed.

```yaml
a:  { address: /xbox/btn/a, type: button, midi: { kind: note, note: 60, velocity: 100 } }
lt: { address: /xbox/trigger/left, type: trigger, midi: { kind: cc, cc: 11 } }
```

## Demo (no controller)

```bash
python stickosc.py --demo
python stickosc.py --demo --midi
python stickosc.py --demo --layout ps5
```

Simulates stick / trigger motion so you can verify OSC / MIDI without hardware.

## CLI options

| Flag | Meaning |
|------|---------|
| `--gui` | open the control window |
| `--host 192.168.1.10` | OSC destination IP |
| `--port 8000` | OSC destination port |
| `--config path.yaml` | custom mapping file |
| `--index 0` | which pad (if several) |
| `--layout auto\|xbox\|ps5` | controller button/axis layout |
| `--demo` | simulate inputs |
| `--midi` | enable MIDI output |
| `--no-midi` | disable MIDI |
| `--no-osc` | disable OSC |
| `--midi-port NAME` | MIDI output / virtual port name |
| `--midi-channel N` | MIDI channel 1–16 |
| `--list-midi-ports` | print MIDI outs and exit |
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

OSC — in another terminal:

```bash
python tools/osc_listen.py --port 9000
```

Then run `python stickosc.py --demo` and watch addresses print.

MIDI — start StickOSC with `--midi` first, then:

```bash
python tools/midi_listen.py --port StickOSC
```

## Notes

- Stick deadzone default: `0.12` (in `mapping.yaml`)
- Sends **only on change** (not a flood every frame)
- MIDI uses **mido** + **python-rtmidi** (virtual port on most OSes)
- PS5 touchpad / gyro / adaptive triggers are not mapped yet
- `Ctrl+C` to quit cleanly (also sends MIDI All Notes Off)
- Set `NO_COLOR=1` to disable ANSI colours
- Dev packaging dependency: `pip install -r requirements-dev.txt` (PyInstaller)
