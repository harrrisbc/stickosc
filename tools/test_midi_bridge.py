#!/usr/bin/env python3
"""Offline unit checks for StickOSC MIDI mapping (no ALSA required)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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


def test_float_to_midi_cc() -> None:
    assert float_to_midi_cc(0.0, "axis") == 64
    assert float_to_midi_cc(-1.0, "axis") == 0
    assert float_to_midi_cc(1.0, "axis") == 127
    assert float_to_midi_cc(0.0, "trigger") == 0
    assert float_to_midi_cc(1.0, "trigger") == 127


def test_send_changed_with_fake_port() -> None:
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


def test_windows_refuses_virtual_port() -> None:
    fake_mido = MagicMock()
    fake_mido.get_output_names.return_value = []

    with patch.dict("sys.modules", {"mido": fake_mido}):
        with patch.object(MidiBridge, "_is_windows", return_value=True):
            try:
                MidiBridge("StickOSC", 1, {})
                raise AssertionError("expected RuntimeError on Windows with no ports")
            except RuntimeError as exc:
                msg = str(exc).lower()
                assert "loopmidi" in msg
                assert "windows" in msg
    fake_mido.open_output.assert_not_called()


def test_non_windows_tries_virtual() -> None:
    fake_port = MagicMock()
    fake_port.name = "StickOSC"
    fake_mido = MagicMock()
    fake_mido.get_output_names.return_value = []
    fake_mido.open_output.return_value = fake_port

    with patch.dict("sys.modules", {"mido": fake_mido}):
        with patch.object(MidiBridge, "_is_windows", return_value=False):
            midi = MidiBridge("StickOSC", 1, {})
            assert midi.label == "StickOSC (virtual)"
    fake_mido.open_output.assert_called_once_with("StickOSC", virtual=True)


def test_auto_select_single_port_when_name_empty() -> None:
    fake_port = MagicMock()
    fake_port.name = "loopMIDI Port"
    fake_mido = MagicMock()
    fake_mido.get_output_names.return_value = ["loopMIDI Port"]
    fake_mido.open_output.return_value = fake_port

    with patch.dict("sys.modules", {"mido": fake_mido}):
        with patch.object(MidiBridge, "_is_windows", return_value=True):
            midi = MidiBridge("", 1, {})
            assert midi.label == "loopMIDI Port"
    fake_mido.open_output.assert_called_once_with("loopMIDI Port")


def main() -> int:
    test_float_to_midi_cc()
    test_send_changed_with_fake_port()
    test_windows_refuses_virtual_port()
    test_non_windows_tries_virtual()
    test_auto_select_single_port_when_name_empty()
    print("ok — MIDI bridge + platform open tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
