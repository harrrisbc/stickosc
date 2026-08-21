#!/usr/bin/env python3
"""Offline unit checks for StickOSC MIDI mapping (no ALSA required)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from stickosc import MidiBridge, float_to_midi_cc, load_config  # noqa: E402


class FakePort:
    name = "fake"

    def __init__(self) -> None:
        self.messages: list = []

    def send(self, msg) -> None:
        self.messages.append(msg)

    def close(self) -> None:
        pass


def main() -> int:
    assert float_to_midi_cc(0.0, "axis") == 64
    assert float_to_midi_cc(-1.0, "axis") == 0
    assert float_to_midi_cc(1.0, "axis") == 127
    assert float_to_midi_cc(0.0, "trigger") == 0
    assert float_to_midi_cc(1.0, "trigger") == 127

    cfg = load_config(ROOT / "mapping.yaml")
    port = FakePort()
    midi = MidiBridge("fake", 1, cfg["map"], port=port)

    values = {k: 0.0 for k in cfg["map"]}
    # First pass seeds CC defaults (buttons stay silent until pressed)
    assert midi.send_changed(values) is True
    assert any(m.type == "control_change" for m in port.messages)
    assert not any(m.type.startswith("note_") for m in port.messages)

    values["a"] = 1.0
    assert midi.send_changed(values) is True
    assert port.messages[-1].type == "note_on"
    assert port.messages[-1].note == 60

    values["a"] = 0.0
    assert midi.send_changed(values) is True
    assert port.messages[-1].type == "note_off"

    values["left_x"] = 1.0
    assert midi.send_changed(values) is True
    assert port.messages[-1].type == "control_change"
    assert port.messages[-1].control == 1
    assert port.messages[-1].value == 127

    values["lt"] = 0.5
    assert midi.send_changed(values) is True
    assert port.messages[-1].control == 11
    assert port.messages[-1].value == 64

    # unchanged → no extra send
    before = len(port.messages)
    assert midi.send_changed(values) is False
    assert len(port.messages) == before

    print(f"ok — {len(port.messages)} MIDI messages exercised")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
