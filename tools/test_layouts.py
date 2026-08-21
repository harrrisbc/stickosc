#!/usr/bin/env python3
"""Offline checks for controller layout detection / profiles."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from stickosc import LAYOUTS, detect_layout, load_config, resolve_layout  # noqa: E402

LOGICAL = {
    "a",
    "b",
    "x",
    "y",
    "lb",
    "rb",
    "back",
    "start",
    "l3",
    "r3",
    "left_x",
    "left_y",
    "right_x",
    "right_y",
    "lt",
    "rt",
}


def main() -> int:
    assert detect_layout("Xbox Series X Controller") == "xbox"
    assert detect_layout("Xbox Wireless Controller") == "xbox"
    assert detect_layout("DualSense Wireless Controller") == "ps5"
    assert detect_layout("Sony Interactive Entertainment DualSense") == "ps5"
    assert detect_layout("PS5 Controller") == "ps5"
    assert detect_layout("Wireless Controller") == "ps5"
    assert detect_layout(None) == "xbox"
    assert detect_layout("Generic USB Gamepad") == "xbox"

    assert resolve_layout("ps5", "Xbox Controller") == "ps5"
    assert resolve_layout("xbox", "DualSense") == "xbox"
    assert resolve_layout("auto", "DualSense Wireless Controller") == "ps5"

    for name, profile in LAYOUTS.items():
        assert set(profile["btn"]) == {
            "a",
            "b",
            "x",
            "y",
            "lb",
            "rb",
            "back",
            "start",
            "l3",
            "r3",
        }, name
        assert set(profile["axis"]) == {
            "left_x",
            "left_y",
            "right_x",
            "right_y",
            "lt",
            "rt",
        }, name

    cfg = load_config(ROOT / "mapping.yaml")
    assert cfg["controller"].get("layout", "auto") == "auto"
    assert LOGICAL.issubset(set(cfg["map"]))
    # shoulder indices differ between layouts (the whole point of ps5 profile)
    assert LAYOUTS["xbox"]["btn"]["lb"] != LAYOUTS["ps5"]["btn"]["lb"]

    print("ok — layout detect + profiles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
