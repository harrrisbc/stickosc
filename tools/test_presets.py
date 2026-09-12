#!/usr/bin/env python3
"""Unit checks for StickOSC show-control presets."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from presets import apply_preset, list_presets  # noqa: E402
from stickosc import load_config  # noqa: E402


def main() -> int:
    names = list_presets()
    assert names == ["StickOSC", "QLab", "ETC Eos"]

    cfg = load_config(ROOT / "mapping.yaml")
    assert cfg["map"]["a"]["type"] == "button"

    qlab = apply_preset(cfg, "QLab")
    assert qlab["map"]["a"]["address"] == "/go"
    assert qlab["map"]["a"]["type"] == "button"  # type preserved
    assert qlab["map"]["b"]["address"] == "/stop"
    assert qlab["map"]["x"]["address"] == "/panic"
    assert qlab["osc"]["port"] == 53000

    eos = apply_preset(cfg, "ETC Eos")
    assert eos["map"]["a"]["address"] == "/eos/key/go_0"
    assert eos["map"]["lt"]["address"] == "/eos/chan/1"
    assert eos["map"]["lt"]["type"] == "trigger"
    assert eos["osc"]["port"] == 8000

    stick = apply_preset(cfg, "StickOSC")
    assert stick["map"]["a"]["address"] == "/stickosc/btn/a"
    assert stick["osc"]["port"] == 9000

    try:
        apply_preset(cfg, "Nope")
        raise AssertionError("expected KeyError")
    except KeyError:
        pass

    print("ok — presets applied with types preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
