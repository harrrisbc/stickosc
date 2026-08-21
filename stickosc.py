#!/usr/bin/env python3
"""StickOSC — map Xbox / PS5 controllers to OSC and/or MIDI messages."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any

import pygame
import yaml
from pythonosc import udp_client

# ---------------------------------------------------------------------------
# Defaults / controller layouts (SDL / pygame joystick indices)
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "mapping.yaml"

# Logical control names stay stable across layouts so mapping.yaml keeps working.
# PS5 face synonyms: Cross→a, Circle→b, Square→x, Triangle→y.
LAYOUTS: dict[str, dict[str, Any]] = {
    "xbox": {
        "btn": {
            "a": 0,
            "b": 1,
            "x": 2,
            "y": 3,
            "lb": 4,
            "rb": 5,
            "back": 6,
            "start": 7,
            "l3": 8,
            "r3": 9,
        },
        "axis": {
            "left_x": 0,
            "left_y": 1,
            "right_x": 2,
            "right_y": 3,
            "lt": 4,
            "rt": 5,
        },
        # D-pad via hat 0 when present
        "dpad_buttons": None,
    },
    # DualSense / DualShock-style indices commonly reported by pygame on macOS/Linux.
    # L1/R1 and Create/Options differ from Xbox; sticks/triggers usually match.
    "ps5": {
        "btn": {
            "a": 0,  # Cross
            "b": 1,  # Circle
            "x": 2,  # Square
            "y": 3,  # Triangle
            "back": 4,  # Create / Share
            "start": 6,  # Options
            "l3": 7,
            "r3": 8,
            "lb": 9,  # L1
            "rb": 10,  # R1
        },
        "axis": {
            "left_x": 0,
            "left_y": 1,
            "right_x": 2,
            "right_y": 3,
            "lt": 4,  # L2
            "rt": 5,  # R2
        },
        # Used when the pad exposes D-pad as buttons instead of a hat
        "dpad_buttons": {"up": 11, "right": 12, "down": 13, "left": 14},
    },
}

VALID_LAYOUTS = ("auto", "xbox", "ps5")

EPSILON = 0.001
POLL_HZ = 60
REDRAW_HZ = 30

DEFAULT_YAML = """# StickOSC config — remap OSC `address` and optional `midi` per control
osc:
  enabled: true
  host: 127.0.0.1
  port: 9000
  prefix: /xbox

midi:
  enabled: false
  port: StickOSC
  channel: 1

controller:
  index: 0
  deadzone: 0.12
  layout: auto

map:
  a:       { address: /xbox/btn/a,         type: button,  midi: { kind: note, note: 60 } }
  b:       { address: /xbox/btn/b,         type: button,  midi: { kind: note, note: 62 } }
  x:       { address: /xbox/btn/x,         type: button,  midi: { kind: note, note: 64 } }
  y:       { address: /xbox/btn/y,         type: button,  midi: { kind: note, note: 65 } }
  lb:      { address: /xbox/btn/lb,        type: button,  midi: { kind: note, note: 67 } }
  rb:      { address: /xbox/btn/rb,        type: button,  midi: { kind: note, note: 69 } }
  back:    { address: /xbox/btn/back,      type: button,  midi: { kind: note, note: 71 } }
  start:   { address: /xbox/btn/start,     type: button,  midi: { kind: note, note: 72 } }
  l3:      { address: /xbox/btn/l3,        type: button,  midi: { kind: note, note: 74 } }
  r3:      { address: /xbox/btn/r3,        type: button,  midi: { kind: note, note: 76 } }
  dpad_x:  { address: /xbox/dpad/x,        type: hat_x,   midi: { kind: cc, cc: 20 } }
  dpad_y:  { address: /xbox/dpad/y,        type: hat_y,   midi: { kind: cc, cc: 21 } }
  left_x:  { address: /xbox/stick/left/x,  type: axis,    midi: { kind: cc, cc: 1 } }
  left_y:  { address: /xbox/stick/left/y,  type: axis,    midi: { kind: cc, cc: 2 } }
  right_x: { address: /xbox/stick/right/x, type: axis,    midi: { kind: cc, cc: 3 } }
  right_y: { address: /xbox/stick/right/y, type: axis,    midi: { kind: cc, cc: 4 } }
  lt:      { address: /xbox/trigger/left,  type: trigger, midi: { kind: cc, cc: 11 } }
  rt:      { address: /xbox/trigger/right, type: trigger, midi: { kind: cc, cc: 12 } }
"""

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------


class Ansi:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def wrap(self, code: str, text: str) -> str:
        if not self.enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    def dim(self, t: str) -> str:
        return self.wrap("90", t)

    def ok(self, t: str) -> str:
        return self.wrap("32", t)

    def warn(self, t: str) -> str:
        return self.wrap("33", t)

    def hot(self, t: str) -> str:
        return self.wrap("36", t)


def use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        path.write_text(DEFAULT_YAML, encoding="utf-8")
        print(f"wrote {path} — edit addresses anytime")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("osc", {})
    data.setdefault("midi", {})
    data.setdefault("controller", {})
    data.setdefault("map", {})
    data["osc"].setdefault("enabled", True)
    data["osc"].setdefault("host", "127.0.0.1")
    data["osc"].setdefault("port", 9000)
    data["osc"].setdefault("prefix", "/xbox")
    data["midi"].setdefault("enabled", False)
    data["midi"].setdefault("port", "StickOSC")
    data["midi"].setdefault("channel", 1)
    data["controller"].setdefault("index", 0)
    data["controller"].setdefault("deadzone", 0.12)
    data["controller"].setdefault("layout", "auto")
    return data


def detect_layout(joy_name: str | None) -> str:
    """Guess xbox vs ps5 from the pygame joystick name."""
    if not joy_name:
        return "xbox"
    n = joy_name.lower()
    if any(k in n for k in ("xbox", "x-box", "xinput")):
        return "xbox"
    if any(
        k in n
        for k in (
            "dualsense",
            "dual sense",
            "dualshock",
            "dual shock",
            "ps5",
            "ps4",
            "playstation",
        )
    ):
        return "ps5"
    # Bare "Wireless Controller" is the classic Sony BT name (not Xbox Wireless…)
    if "wireless controller" in n:
        return "ps5"
    return "xbox"


def resolve_layout(preference: str, joy_name: str | None) -> str:
    pref = (preference or "auto").lower()
    if pref in ("xbox", "ps5"):
        return pref
    return detect_layout(joy_name)


# ---------------------------------------------------------------------------
# Normalize / deadzone
# ---------------------------------------------------------------------------


def apply_deadzone(value: float, deadzone: float) -> float:
    if abs(value) < deadzone:
        return 0.0
    # rescale so edge of deadzone → 0 and full throw → ±1
    sign = 1.0 if value > 0 else -1.0
    scaled = (abs(value) - deadzone) / (1.0 - deadzone)
    return sign * max(0.0, min(1.0, scaled))


def normalize_trigger(raw: float) -> float:
    """Map trigger axis to 0..1.

    On many platforms triggers are -1..1 (rest at -1). Some report 0..1.
    """
    if raw < -0.05:
        # classic -1 (rest) .. +1 (full)
        return max(0.0, min(1.0, (raw + 1.0) * 0.5))
    return max(0.0, min(1.0, raw))


def flip_y(value: float) -> float:
    """pygame Y: down = +1 → StickOSC: up = +1."""
    return -value


def clamp_midi(value: int) -> int:
    return max(0, min(127, int(value)))


def float_to_midi_cc(value: float, control_type: str) -> int:
    """Map normalized controller values to MIDI CC 0..127."""
    if control_type in ("axis", "hat_x", "hat_y"):
        # bipolar -1..1 → 0..127 (center ≈ 64)
        return clamp_midi(round((value + 1.0) * 63.5))
    # trigger / button-as-cc style: 0..1 → 0..127
    return clamp_midi(round(max(0.0, min(1.0, value)) * 127.0))


# ---------------------------------------------------------------------------
# Controller read
# ---------------------------------------------------------------------------


def open_joystick(index: int):
    pygame.joystick.quit()
    pygame.joystick.init()
    count = pygame.joystick.get_count()
    if count <= 0 or index >= count:
        return None
    joy = pygame.joystick.Joystick(index)
    joy.init()
    return joy


def read_controls(joy, deadzone: float, layout: str = "xbox") -> dict[str, float]:
    values: dict[str, float] = {}
    profile = LAYOUTS.get(layout) or LAYOUTS["xbox"]
    btn_map: dict[str, int] = profile["btn"]
    axis_map: dict[str, int] = profile["axis"]
    dpad_buttons: dict[str, int] | None = profile.get("dpad_buttons")

    # buttons
    nbtn = joy.get_numbuttons()
    for name, idx in btn_map.items():
        values[name] = 1.0 if (idx < nbtn and joy.get_button(idx)) else 0.0

    # axes
    naxis = joy.get_numaxes()

    def axis(name: str, default: float = 0.0) -> float:
        idx = axis_map[name]
        if idx >= naxis:
            return default
        return float(joy.get_axis(idx))

    values["left_x"] = apply_deadzone(axis("left_x"), deadzone)
    values["left_y"] = apply_deadzone(flip_y(axis("left_y")), deadzone)
    values["right_x"] = apply_deadzone(axis("right_x"), deadzone)
    values["right_y"] = apply_deadzone(flip_y(axis("right_y")), deadzone)

    # Triggers: if only 4 axes, LT/RT may be missing or combined — keep 0
    if naxis > 4:
        values["lt"] = normalize_trigger(axis("lt", -1.0))
        values["rt"] = normalize_trigger(axis("rt", -1.0))
    else:
        values["lt"] = 0.0
        values["rt"] = 0.0

    # D-pad (hat preferred; PS5 may expose buttons instead)
    dx, dy = 0.0, 0.0
    if joy.get_numhats() > 0:
        hx, hy = joy.get_hat(0)
        dx = float(hx)  # L=-1 R=+1
        dy = float(hy)  # pygame: U=+1 D=-1 already
    elif dpad_buttons:
        up = dpad_buttons.get("up", -1)
        down = dpad_buttons.get("down", -1)
        left = dpad_buttons.get("left", -1)
        right = dpad_buttons.get("right", -1)
        if 0 <= up < nbtn and joy.get_button(up):
            dy = 1.0
        elif 0 <= down < nbtn and joy.get_button(down):
            dy = -1.0
        if 0 <= left < nbtn and joy.get_button(left):
            dx = -1.0
        elif 0 <= right < nbtn and joy.get_button(right):
            dx = 1.0
    values["dpad_x"] = dx
    values["dpad_y"] = dy

    return values


# ---------------------------------------------------------------------------
# Status UI
# ---------------------------------------------------------------------------

STATUS_LINES = 14  # header + body + footer (for cursor restore)


def bar_center(value: float, width: int = 19) -> str:
    """Center-zero meter for sticks: ░░░│░░░"""
    mid = width // 2
    cells = ["░"] * width
    cells[mid] = "│"
    if abs(value) < EPSILON:
        return "".join(cells)
    fill = int(round(abs(value) * mid))
    fill = max(1, min(mid, fill))
    if value > 0:
        for i in range(mid + 1, mid + 1 + fill):
            if i < width:
                cells[i] = "█"
    else:
        for i in range(mid - fill, mid):
            if i >= 0:
                cells[i] = "█"
    return "".join(cells)


def bar_fill(value: float, width: int = 19) -> str:
    """Left-fill meter for triggers."""
    fill = int(round(max(0.0, min(1.0, value)) * width))
    return "█" * fill + "░" * (width - fill)


def button_row(values: dict[str, float], ansi: Ansi, names: list[str], labels: list[str]) -> str:
    parts = []
    for name, label in zip(names, labels):
        on = values.get(name, 0.0) >= 0.5
        parts.append(ansi.hot(label) if on else ansi.dim(label))
    return " · ".join(parts)


def dpad_glyph(values: dict[str, float]) -> str:
    dx = values.get("dpad_x", 0.0)
    dy = values.get("dpad_y", 0.0)
    if abs(dx) < 0.5 and abs(dy) < 0.5:
        return "·"
    bits = []
    if dy > 0.5:
        bits.append("↑")
    if dy < -0.5:
        bits.append("↓")
    if dx < -0.5:
        bits.append("←")
    if dx > 0.5:
        bits.append("→")
    return "".join(bits) or "·"


def render_status(
    ansi: Ansi,
    *,
    joy_name: str | None,
    layout: str,
    layout_source: str,
    osc_line: str,
    midi_line: str,
    config_name: str,
    values: dict[str, float],
    deadzone: float,
    sent_pulse: bool,
    static: bool,
) -> str:
    rule = ansi.dim("─" * 40)
    if joy_name:
        ctrl = f"controller  {joy_name:<24} {ansi.ok('✓')}"
    else:
        ctrl = f"controller  {'(none found)':<24} {ansi.warn('✗')}"

    def meter_line(label: str, key: str, kind: str) -> str:
        v = values.get(key, 0.0)
        bar = bar_center(v) if kind == "stick" else bar_fill(v)
        active = abs(v) > (deadzone if kind == "stick" else EPSILON)
        lab = ansi.hot(f"{label:<3}") if active else f"{label:<3}"
        num = ansi.hot(f"{v:5.2f}") if active else ansi.dim(f"{v:5.2f}")
        return f"  {lab} {bar}  {num}"

    if layout == "ps5":
        face_labels = ["✕", "○", "□", "△", "L1", "R1", "Cre", "Opt", "L3", "R3"]
    else:
        face_labels = ["A", "B", "X", "Y", "LB", "RB", "▢", "≡", "L3", "R3"]

    buttons = button_row(
        values,
        ansi,
        ["a", "b", "x", "y", "lb", "rb", "back", "start", "l3", "r3"],
        face_labels,
    )
    dpad = dpad_glyph(values)
    dpad_s = ansi.hot(f"D-pad  {dpad}") if dpad != "·" else ansi.dim(f"D-pad  {dpad}")

    if static:
        pulse = "●" if sent_pulse else "○"
    else:
        pulse = ansi.hot("●") if sent_pulse else ansi.dim("○")

    layout_note = f"{layout}" if layout_source == layout else f"{layout} ({layout_source})"

    lines = [
        "StickOSC  ·  Pad → OSC / MIDI",
        rule,
        ctrl,
        f"layout      {layout_note}",
        f"OSC         {osc_line}",
        f"MIDI        {midi_line}",
        f"config      {config_name}",
        rule,
        meter_line("LX", "left_x", "stick"),
        meter_line("LY", "left_y", "stick"),
        meter_line("RX", "right_x", "stick"),
        meter_line("RY", "right_y", "stick"),
        meter_line("LT", "lt", "trigger"),
        meter_line("RT", "rt", "trigger"),
        f"  {buttons}",
        f"  {dpad_s}",
        rule,
        f"listening… {pulse}  Ctrl+C to quit",
    ]
    if not joy_name:
        lines.insert(-1, ansi.warn("  plug in an Xbox or PS5 controller…"))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# OSC send-on-change
# ---------------------------------------------------------------------------


class OscBridge:
    def __init__(self, host: str, port: int, mapping: dict[str, Any]) -> None:
        self.client = udp_client.SimpleUDPClient(host, port)
        self.mapping = mapping
        self.last: dict[str, float] = {}
        self.sent_recently = False
        self.label = f"{host}:{port}"

    def send_changed(self, values: dict[str, float]) -> bool:
        any_sent = False
        for key, meta in self.mapping.items():
            if key not in values:
                continue
            address = meta.get("address")
            if not address:
                continue
            value = float(values[key])
            prev = self.last.get(key)
            if prev is None or abs(value - prev) > EPSILON:
                self.client.send_message(address, value)
                self.last[key] = value
                any_sent = True
        self.sent_recently = any_sent
        return any_sent


# ---------------------------------------------------------------------------
# MIDI send-on-change
# ---------------------------------------------------------------------------


class MidiBridge:
    """Send note / CC messages on change via mido (+ rtmidi backend)."""

    def __init__(
        self,
        port_name: str,
        channel: int,
        mapping: dict[str, Any],
        *,
        port: Any | None = None,
    ) -> None:
        import mido

        self.mido = mido
        self.mapping = mapping
        self.channel = max(0, min(15, int(channel) - 1))  # YAML 1..16 → mido 0..15
        self.last_cc: dict[str, int] = {}
        self.last_note_on: dict[str, bool] = {}
        self.sent_recently = False
        self.port = None
        self.label = "off"
        if port is not None:
            self.port = port
            self.label = getattr(port, "name", port_name) or port_name
        else:
            self._open_port(port_name)

    def _open_port(self, port_name: str) -> None:
        mido = self.mido
        try:
            outputs = mido.get_output_names()
        except Exception as exc:
            raise RuntimeError(
                "MIDI backend unavailable (need a system sequencer such as "
                f"ALSA/CoreMIDI). Details: {exc}"
            ) from exc

        # Exact / substring match on an existing output first
        match = None
        for name in outputs:
            if name == port_name or port_name.lower() in name.lower():
                match = name
                break

        if match is not None:
            self.port = mido.open_output(match)
            self.label = match
            return

        # Create a virtual port (ALSA/CoreMIDI/JACK depending on OS)
        try:
            self.port = mido.open_output(port_name, virtual=True)
            self.label = f"{port_name} (virtual)"
        except Exception as exc:
            raise RuntimeError(
                f"could not open MIDI port {port_name!r} "
                f"(available: {outputs or 'none'}): {exc}"
            ) from exc

    @staticmethod
    def list_ports() -> list[str]:
        import mido

        try:
            return list(mido.get_output_names())
        except Exception as exc:
            raise RuntimeError(
                "MIDI backend unavailable (need ALSA/CoreMIDI). "
                f"Details: {exc}"
            ) from exc
    def send_changed(self, values: dict[str, float]) -> bool:
        if self.port is None:
            return False
        any_sent = False
        for key, meta in self.mapping.items():
            if key not in values:
                continue
            midi_meta = meta.get("midi")
            if not midi_meta:
                continue
            kind = str(midi_meta.get("kind", "")).lower()
            value = float(values[key])
            control_type = str(meta.get("type", "axis"))

            if kind == "note":
                if self._send_note(key, midi_meta, value):
                    any_sent = True
            elif kind == "cc":
                if self._send_cc(key, midi_meta, value, control_type):
                    any_sent = True
        self.sent_recently = any_sent
        return any_sent

    def _send_note(self, key: str, midi_meta: dict[str, Any], value: float) -> bool:
        note = clamp_midi(midi_meta.get("note", 60))
        velocity = clamp_midi(midi_meta.get("velocity", 100))
        pressed = value >= 0.5
        was = self.last_note_on.get(key)
        if was is None:
            # first sample: only fire if already held
            self.last_note_on[key] = pressed
            if not pressed:
                return False
        elif was == pressed:
            return False
        else:
            self.last_note_on[key] = pressed

        msg_type = "note_on" if pressed else "note_off"
        vel = velocity if pressed else 0
        self.port.send(
            self.mido.Message(msg_type, note=note, velocity=vel, channel=self.channel)
        )
        return True

    def _send_cc(
        self,
        key: str,
        midi_meta: dict[str, Any],
        value: float,
        control_type: str,
    ) -> bool:
        cc = clamp_midi(midi_meta.get("cc", midi_meta.get("controller", 1)))
        midi_val = float_to_midi_cc(value, control_type)
        prev = self.last_cc.get(key)
        if prev is not None and prev == midi_val:
            return False
        self.last_cc[key] = midi_val
        self.port.send(
            self.mido.Message("control_change", control=cc, value=midi_val, channel=self.channel)
        )
        return True

    def close(self) -> None:
        if self.port is None:
            return
        try:
            # silence hanging notes
            self.port.send(self.mido.Message("control_change", control=123, value=0, channel=self.channel))
        except Exception:
            pass
        try:
            self.port.close()
        except Exception:
            pass
        self.port = None


# ---------------------------------------------------------------------------
# Demo mode (no hardware)
# ---------------------------------------------------------------------------


def demo_values(t: float) -> dict[str, float]:
    import math

    return {
        "a": 1.0 if int(t) % 4 == 0 else 0.0,
        "b": 0.0,
        "x": 0.0,
        "y": 0.0,
        "lb": 0.0,
        "rb": 0.0,
        "back": 0.0,
        "start": 0.0,
        "l3": 0.0,
        "r3": 0.0,
        "dpad_x": 0.0,
        "dpad_y": 0.0,
        "left_x": math.sin(t),
        "left_y": math.cos(t * 0.7),
        "right_x": math.sin(t * 1.3) * 0.5,
        "right_y": math.cos(t * 0.9) * 0.5,
        "lt": (math.sin(t * 0.5) + 1) * 0.5,
        "rt": (math.cos(t * 0.4) + 1) * 0.5,
    }


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="stickosc",
        description="StickOSC maps Xbox / PS5 pads to OSC and/or MIDI (remap in YAML).",
    )
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="path to mapping.yaml")
    p.add_argument("--host", default=None, help="OSC host (overrides config)")
    p.add_argument("--port", type=int, default=None, help="OSC port (overrides config)")
    p.add_argument("--index", type=int, default=None, help="controller index (overrides config)")
    p.add_argument(
        "--layout",
        choices=VALID_LAYOUTS,
        default=None,
        help="controller layout: auto (default), xbox, or ps5",
    )
    p.add_argument("--demo", action="store_true", help="simulate pad motion without hardware")
    p.add_argument("--static", action="store_true", help="disable pulse animation")
    p.add_argument("--verbose", action="store_true", help="print button events to stderr")
    p.add_argument("--midi", action="store_true", help="enable MIDI output (overrides config)")
    p.add_argument("--no-midi", action="store_true", help="disable MIDI output")
    p.add_argument("--no-osc", action="store_true", help="disable OSC output")
    p.add_argument("--midi-port", default=None, help="MIDI output port name (or virtual name)")
    p.add_argument("--midi-channel", type=int, default=None, help="MIDI channel 1-16")
    p.add_argument("--list-midi-ports", action="store_true", help="list MIDI output ports and exit")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.list_midi_ports:
        try:
            ports = MidiBridge.list_ports()
        except Exception as exc:
            print(f"MIDI backend unavailable: {exc}", file=sys.stderr)
            return 1
        if not ports:
            print("no MIDI output ports found")
        else:
            print("MIDI output ports:")
            for name in ports:
                print(f"  · {name}")
        return 0

    cfg = load_config(args.config)

    osc_enabled = bool(cfg["osc"].get("enabled", True)) and not args.no_osc
    midi_enabled = bool(cfg["midi"].get("enabled", False))
    if args.midi:
        midi_enabled = True
    if args.no_midi:
        midi_enabled = False

    host = args.host or cfg["osc"]["host"]
    port = int(args.port if args.port is not None else cfg["osc"]["port"])
    index = int(args.index if args.index is not None else cfg["controller"]["index"])
    deadzone = float(cfg["controller"]["deadzone"])
    layout_pref = (args.layout or str(cfg["controller"].get("layout", "auto"))).lower()
    if layout_pref not in VALID_LAYOUTS:
        print(f"unknown layout {layout_pref!r}; using auto", file=sys.stderr)
        layout_pref = "auto"
    mapping = cfg["map"]
    midi_port_name = args.midi_port or str(cfg["midi"].get("port", "StickOSC"))
    midi_channel = int(
        args.midi_channel if args.midi_channel is not None else cfg["midi"].get("channel", 1)
    )

    if not osc_enabled and not midi_enabled:
        print("nothing to send: enable OSC and/or MIDI", file=sys.stderr)
        return 2

    ansi = Ansi(use_color() and not args.static)
    osc: OscBridge | None = None
    midi: MidiBridge | None = None

    if osc_enabled:
        osc = OscBridge(host, port, mapping)

    if midi_enabled:
        try:
            midi = MidiBridge(midi_port_name, midi_channel, mapping)
        except Exception as exc:
            print(f"MIDI open failed: {exc}", file=sys.stderr)
            if not osc_enabled:
                return 1
            print("continuing with OSC only…", file=sys.stderr)
            midi = None
            midi_enabled = False

    # Headless-friendly pygame init (no window)
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.joystick.init()

    joy = None if args.demo else open_joystick(index)
    joy_name = "Demo Pad" if args.demo else (joy.get_name() if joy else None)
    if args.demo:
        active_layout = layout_pref if layout_pref in ("xbox", "ps5") else "xbox"
    else:
        active_layout = resolve_layout(layout_pref, joy_name)

    values = {k: 0.0 for k in mapping}
    last_redraw = 0.0
    last_lines = 0
    t0 = time.monotonic()
    interactive = sys.stdout.isatty()

    def osc_line() -> str:
        if osc is None:
            return ansi.dim("off")
        return f"{osc.label}"

    def midi_line() -> str:
        if midi is None:
            return ansi.dim("off")
        return f"ch{midi_channel} → {midi.label}"

    def clear_and_print(text: str) -> None:
        nonlocal last_lines
        if not interactive:
            # Avoid flooding pipes/logs: print status once, then stay quiet.
            if last_lines == 0:
                print(text)
                last_lines = text.count("\n") + 1
                sys.stdout.flush()
            return
        if last_lines > 0:
            # move cursor up and clear
            sys.stdout.write(f"\033[{last_lines}A")
            for _ in range(last_lines):
                sys.stdout.write("\033[2K\n")
            sys.stdout.write(f"\033[{last_lines}A")
        print(text)
        last_lines = text.count("\n") + 1
        sys.stdout.flush()

    try:
        # first paint
        frame = render_status(
            ansi,
            joy_name=joy_name,
            layout=active_layout,
            layout_source=layout_pref,
            osc_line=osc_line(),
            midi_line=midi_line(),
            config_name=args.config.name,
            values=values,
            deadzone=deadzone,
            sent_pulse=False,
            static=args.static,
        )
        clear_and_print(frame)

        while True:
            now = time.monotonic()
            pygame.event.pump()

            if args.demo:
                values = demo_values(now - t0)
                joy_name = "Demo Pad"
                if layout_pref in ("xbox", "ps5"):
                    active_layout = layout_pref
                else:
                    active_layout = "xbox"
            else:
                # reconnect if unplugged
                if joy is None:
                    joy = open_joystick(index)
                    joy_name = joy.get_name() if joy else None
                    active_layout = resolve_layout(layout_pref, joy_name)
                else:
                    try:
                        # get_name raises if disconnected on some platforms
                        joy_name = joy.get_name()
                        active_layout = resolve_layout(layout_pref, joy_name)
                        values = read_controls(joy, deadzone, active_layout)
                    except pygame.error:
                        joy = None
                        joy_name = None
                        active_layout = resolve_layout(layout_pref, None)
                        values = {k: 0.0 for k in mapping}

            sent = False
            if osc is not None:
                sent = osc.send_changed(values) or sent
            if midi is not None:
                sent = midi.send_changed(values) or sent

            if args.verbose and sent:
                for k, v in values.items():
                    if mapping.get(k, {}).get("type") == "button" and v >= 0.5:
                        addr = mapping[k].get("address", "?")
                        midi_meta = mapping[k].get("midi") or {}
                        extra = ""
                        if midi is not None and midi_meta.get("kind") == "note":
                            extra = f"  midi note {midi_meta.get('note')}"
                        print(f"[btn] {k}=1 → {addr}{extra}", file=sys.stderr)

            if now - last_redraw >= 1.0 / REDRAW_HZ:
                pulse = sent
                if osc is not None and osc.sent_recently:
                    pulse = True
                if midi is not None and midi.sent_recently:
                    pulse = True
                frame = render_status(
                    ansi,
                    joy_name=joy_name,
                    layout=active_layout,
                    layout_source=layout_pref,
                    osc_line=osc_line(),
                    midi_line=midi_line(),
                    config_name=args.config.name,
                    values=values,
                    deadzone=deadzone,
                    sent_pulse=pulse,
                    static=args.static,
                )
                clear_and_print(frame)
                last_redraw = now
                if not sent:
                    if osc is not None:
                        osc.sent_recently = False
                    if midi is not None:
                        midi.sent_recently = False

            time.sleep(1.0 / POLL_HZ)
    except KeyboardInterrupt:
        if interactive:
            print()
        print(ansi.dim("StickOSC stopped."))
        return 0
    finally:
        if midi is not None:
            midi.close()
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
