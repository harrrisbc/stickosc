#!/usr/bin/env python3
"""Offline checks for dual OSC destinations (no UDP required)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from stickosc import OscBridge, load_config, osc_status_line  # noqa: E402


class FakeOscClient:
    def __init__(self) -> None:
        self.messages: list[tuple[str, float]] = []

    def send_message(self, address: str, value: float) -> None:
        self.messages.append((address, float(value)))


def main() -> int:
    cfg = load_config(ROOT / "mapping.yaml")
    extra = cfg["osc"]["extra"]
    assert extra["enabled"] is False
    assert int(extra["port"]) == 9001

    mapping = cfg["map"]
    a = FakeOscClient()
    b = FakeOscClient()
    osc1 = OscBridge("127.0.0.1", 9000, mapping, client=a)
    osc2 = OscBridge("192.168.1.10", 8000, mapping, client=b)

    values = {k: 0.0 for k in mapping}
    assert osc1.send_changed(values) is True
    assert osc2.send_changed(values) is True
    assert a.messages and b.messages
    assert a.messages == b.messages

    values["a"] = 1.0
    assert osc1.send_changed(values) is True
    assert osc2.send_changed(values) is True
    assert a.messages[-1] == ("/xbox/btn/a", 1.0)
    assert b.messages[-1] == ("/xbox/btn/a", 1.0)

    # unchanged → no extra send
    before = (len(a.messages), len(b.messages))
    assert osc1.send_changed(values) is False
    assert osc2.send_changed(values) is False
    assert (len(a.messages), len(b.messages)) == before

    assert osc_status_line(osc1, osc2) == "127.0.0.1:9000 + 192.168.1.10:8000"
    assert osc_status_line(None, None) == "off"
    print(f"ok — dual OSC {len(a.messages)} msgs each")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
