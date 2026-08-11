#!/usr/bin/env python3
"""StickOSC — map an Xbox controller to OSC messages."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import pygame
import yaml
from pythonosc import udp_client

# ---------------------------------------------------------------------------
# Defaults / Xbox layout (SDL / pygame)
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "mapping.yaml"

# Common Xbox / XInput button indices under pygame
BTN = {
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
}

# Axis layout varies slightly by OS; this matches typical Xbox pads on Windows/macOS/Linux
AXIS = {
    "left_x": 0,
    "left_y": 1,
    "right_x": 2,
    "right_y": 3,
    "lt": 4,
    "rt": 5,
}

EPSILON = 0.001
POLL_HZ = 60
REDRAW_HZ = 30

DEFAULT_YAML = """# StickOSC config — remap by changing `address` only
osc:
  host: 127.0.0.1
  port: 9000
  prefix: /xbox

controller:
  index: 0
  deadzone: 0.12

map:
  a:       { address: /xbox/btn/a,         type: button }
  b:       { address: /xbox/btn/b,         type: button }
  x:       { address: /xbox/btn/x,         type: button }
  y:       { address: /xbox/btn/y,         type: button }
  lb:      { address: /xbox/btn/lb,        type: button }
  rb:      { address: /xbox/btn/rb,        type: button }
  back:    { address: /xbox/btn/back,      type: button }
  start:   { address: /xbox/btn/start,     type: button }
  l3:      { address: /xbox/btn/l3,        type: button }
  r3:      { address: /xbox/btn/r3,        type: button }
  dpad_x:  { address: /xbox/dpad/x,        type: hat_x }
  dpad_y:  { address: /xbox/dpad/y,        type: hat_y }
  left_x:  { address: /xbox/stick/left/x,  type: axis }
  left_y:  { address: /xbox/stick/left/y,  type: axis }
  right_x: { address: /xbox/stick/right/x, type: axis }
  right_y: { address: /xbox/stick/right/y, type: axis }
  lt:      { address: /xbox/trigger/left,  type: trigger }
  rt:      { address: /xbox/trigger/right, type: trigger }
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
    data.setdefault("controller", {})
    data.setdefault("map", {})
    data["osc"].setdefault("host", "127.0.0.1")
    data["osc"].setdefault("port", 9000)
    data["osc"].setdefault("prefix", "/xbox")
    data["controller"].setdefault("index", 0)
    data["controller"].setdefault("deadzone", 0.12)
    return data


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


def read_controls(joy, deadzone: float) -> dict[str, float]:
    values: dict[str, float] = {}

    # buttons
    nbtn = joy.get_numbuttons()
    for name, idx in BTN.items():
        values[name] = 1.0 if (idx < nbtn and joy.get_button(idx)) else 0.0

    # axes
    naxis = joy.get_numaxes()

    def axis(name: str, default: float = 0.0) -> float:
        idx = AXIS[name]
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

    # D-pad (hat)
    dx, dy = 0.0, 0.0
    if joy.get_numhats() > 0:
        hx, hy = joy.get_hat(0)
        dx = float(hx)  # L=-1 R=+1
        dy = float(hy)  # pygame: U=+1 D=-1 already
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
    host: str,
    port: int,
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

    buttons = button_row(
        values,
        ansi,
        ["a", "b", "x", "y", "lb", "rb", "back", "start", "l3", "r3"],
        ["A", "B", "X", "Y", "LB", "RB", "▢", "≡", "L3", "R3"],
    )
    dpad = dpad_glyph(values)
    dpad_s = ansi.hot(f"D-pad  {dpad}") if dpad != "·" else ansi.dim(f"D-pad  {dpad}")

    if static:
        pulse = "●" if sent_pulse else "○"
    else:
        pulse = ansi.hot("●") if sent_pulse else ansi.dim("○")

    lines = [
        "StickOSC  ·  Xbox → OSC",
        rule,
        ctrl,
        f"sending to  {host}:{port}",
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
        lines.insert(-1, ansi.warn("  plug in an Xbox controller…"))
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
        description="StickOSC maps your Xbox pad to OSC addresses you can remap in a YAML file.",
    )
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="path to mapping.yaml")
    p.add_argument("--host", default=None, help="OSC host (overrides config)")
    p.add_argument("--port", type=int, default=None, help="OSC port (overrides config)")
    p.add_argument("--index", type=int, default=None, help="controller index (overrides config)")
    p.add_argument("--demo", action="store_true", help="simulate pad motion without hardware")
    p.add_argument("--static", action="store_true", help="disable pulse animation")
    p.add_argument("--verbose", action="store_true", help="print button events to stderr")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config)

    host = args.host or cfg["osc"]["host"]
    port = int(args.port if args.port is not None else cfg["osc"]["port"])
    index = int(args.index if args.index is not None else cfg["controller"]["index"])
    deadzone = float(cfg["controller"]["deadzone"])
    mapping = cfg["map"]

    ansi = Ansi(use_color() and not args.static)
    osc = OscBridge(host, port, mapping)

    # Headless-friendly pygame init (no window)
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.joystick.init()

    joy = None if args.demo else open_joystick(index)
    joy_name = "Demo Pad" if args.demo else (joy.get_name() if joy else None)

    values = {k: 0.0 for k in mapping}
    last_redraw = 0.0
    last_lines = 0
    t0 = time.monotonic()
    interactive = sys.stdout.isatty()

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
            host=host,
            port=port,
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
            else:
                # reconnect if unplugged
                if joy is None:
                    joy = open_joystick(index)
                    joy_name = joy.get_name() if joy else None
                else:
                    try:
                        # get_name raises if disconnected on some platforms
                        _ = joy.get_name()
                        values = read_controls(joy, deadzone)
                        joy_name = joy.get_name()
                    except pygame.error:
                        joy = None
                        joy_name = None
                        values = {k: 0.0 for k in mapping}

            sent = osc.send_changed(values)

            if args.verbose and sent:
                for k, v in values.items():
                    if mapping.get(k, {}).get("type") == "button" and v >= 0.5:
                        print(f"[btn] {k}=1 → {mapping[k]['address']}", file=sys.stderr)

            if now - last_redraw >= 1.0 / REDRAW_HZ:
                frame = render_status(
                    ansi,
                    joy_name=joy_name,
                    host=host,
                    port=port,
                    config_name=args.config.name,
                    values=values,
                    deadzone=deadzone,
                    sent_pulse=sent or osc.sent_recently,
                    static=args.static,
                )
                clear_and_print(frame)
                last_redraw = now
                if not sent:
                    osc.sent_recently = False

            time.sleep(1.0 / POLL_HZ)
    except KeyboardInterrupt:
        if interactive:
            print()
        print(ansi.dim("StickOSC stopped."))
        return 0
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
