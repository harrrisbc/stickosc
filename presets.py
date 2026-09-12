"""Show-control OSC/MIDI mapping presets for StickOSC."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from stickosc import MAP_KEYS

# Control types must stay stable across presets (engine relies on them).
_TYPES: dict[str, str] = {
    "a": "button",
    "b": "button",
    "x": "button",
    "y": "button",
    "lb": "button",
    "rb": "button",
    "back": "button",
    "start": "button",
    "l3": "button",
    "r3": "button",
    "dpad_x": "hat_x",
    "dpad_y": "hat_y",
    "left_x": "axis",
    "left_y": "axis",
    "right_x": "axis",
    "right_y": "axis",
    "lt": "trigger",
    "rt": "trigger",
}

_DEFAULT_MIDI: dict[str, dict[str, Any]] = {
    "a": {"kind": "note", "note": 60},
    "b": {"kind": "note", "note": 62},
    "x": {"kind": "note", "note": 64},
    "y": {"kind": "note", "note": 65},
    "lb": {"kind": "note", "note": 67},
    "rb": {"kind": "note", "note": 69},
    "back": {"kind": "note", "note": 71},
    "start": {"kind": "note", "note": 72},
    "l3": {"kind": "note", "note": 74},
    "r3": {"kind": "note", "note": 76},
    "dpad_x": {"kind": "cc", "cc": 20},
    "dpad_y": {"kind": "cc", "cc": 21},
    "left_x": {"kind": "cc", "cc": 1},
    "left_y": {"kind": "cc", "cc": 2},
    "right_x": {"kind": "cc", "cc": 3},
    "right_y": {"kind": "cc", "cc": 4},
    "lt": {"kind": "cc", "cc": 11},
    "rt": {"kind": "cc", "cc": 12},
}


def _entry(
    key: str,
    address: str,
    *,
    label: str = "",
    midi: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "address": address,
        "type": _TYPES[key],
    }
    if label:
        out["label"] = label
    if midi is not None:
        out["midi"] = deepcopy(midi)
    elif key in _DEFAULT_MIDI:
        out["midi"] = deepcopy(_DEFAULT_MIDI[key])
    return out


def _build_map(spec: dict[str, dict[str, Any]]) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key in MAP_KEYS:
        info = spec[key]
        mapping[key] = _entry(
            key,
            info["address"],
            label=str(info.get("label", "")),
            midi=info.get("midi"),
        )
    return mapping


PRESET_STICKOSC_MAP = _build_map(
    {
        "a": {"address": "/stickosc/btn/a", "label": "A/Cross"},
        "b": {"address": "/stickosc/btn/b", "label": "B/Circle"},
        "x": {"address": "/stickosc/btn/x", "label": "X/Square"},
        "y": {"address": "/stickosc/btn/y", "label": "Y/Triangle"},
        "lb": {"address": "/stickosc/btn/lb", "label": "LB/L1"},
        "rb": {"address": "/stickosc/btn/rb", "label": "RB/R1"},
        "back": {"address": "/stickosc/btn/back", "label": "Back/Create"},
        "start": {"address": "/stickosc/btn/start", "label": "Start/Options"},
        "l3": {"address": "/stickosc/btn/l3", "label": "L3"},
        "r3": {"address": "/stickosc/btn/r3", "label": "R3"},
        "dpad_x": {"address": "/stickosc/dpad/x", "label": "D-pad X"},
        "dpad_y": {"address": "/stickosc/dpad/y", "label": "D-pad Y"},
        "left_x": {"address": "/stickosc/stick/left/x", "label": "Left X"},
        "left_y": {"address": "/stickosc/stick/left/y", "label": "Left Y"},
        "right_x": {"address": "/stickosc/stick/right/x", "label": "Right X"},
        "right_y": {"address": "/stickosc/stick/right/y", "label": "Right Y"},
        "lt": {"address": "/stickosc/trigger/left", "label": "LT/L2"},
        "rt": {"address": "/stickosc/trigger/right", "label": "RT/R2"},
    }
)

# QLab 5 workspace-level + selected-cue helpers. Continuous axes keep /stickosc paths.
PRESET_QLAB_MAP = _build_map(
    {
        "a": {"address": "/go", "label": "GO"},
        "b": {"address": "/stop", "label": "Stop"},
        "x": {"address": "/panic", "label": "Panic"},
        "y": {"address": "/hardStop", "label": "Hard stop"},
        "lb": {"address": "/cue/selected/start", "label": "Start selected"},
        "rb": {"address": "/cue/selected/stop", "label": "Stop selected"},
        "back": {"address": "/reset", "label": "Reset"},
        "start": {"address": "/save", "label": "Save"},
        "l3": {"address": "/cue/selected/pause", "label": "Pause selected"},
        "r3": {"address": "/cue/selected/load", "label": "Load selected"},
        "dpad_x": {"address": "/playhead/previous", "label": "Playhead prev"},
        "dpad_y": {"address": "/playhead/next", "label": "Playhead next"},
        "left_x": {"address": "/stickosc/stick/left/x", "label": "Left X"},
        "left_y": {"address": "/stickosc/stick/left/y", "label": "Left Y"},
        "right_x": {"address": "/stickosc/stick/right/x", "label": "Right X"},
        "right_y": {"address": "/stickosc/stick/right/y", "label": "Right Y"},
        "lt": {"address": "/stickosc/trigger/left", "label": "LT/L2"},
        "rt": {"address": "/stickosc/trigger/right", "label": "RT/R2"},
    }
)

PRESET_EOS_MAP = _build_map(
    {
        "a": {"address": "/eos/key/go_0", "label": "Go"},
        "b": {"address": "/eos/key/stop", "label": "Stop"},
        "x": {"address": "/eos/key/go_to_cue", "label": "Go To Cue"},
        "y": {"address": "/eos/key/assert", "label": "Assert"},
        "lb": {"address": "/eos/key/last_time", "label": "Last Time"},
        "rb": {"address": "/eos/key/next", "label": "Next"},
        "back": {"address": "/eos/key/clear_cmd", "label": "Clear"},
        "start": {"address": "/eos/key/enter", "label": "Enter"},
        "l3": {"address": "/eos/key/select_last", "label": "Select Last"},
        "r3": {"address": "/eos/key/full", "label": "Full"},
        "dpad_x": {"address": "/eos/key/last", "label": "Last"},
        "dpad_y": {"address": "/eos/key/next", "label": "Next"},
        "left_x": {"address": "/eos/chan/1/param/pan", "label": "Chan1 pan"},
        "left_y": {"address": "/eos/chan/1/param/tilt", "label": "Chan1 tilt"},
        "right_x": {"address": "/eos/chan/2/param/pan", "label": "Chan2 pan"},
        "right_y": {"address": "/eos/chan/2/param/tilt", "label": "Chan2 tilt"},
        "lt": {"address": "/eos/chan/1", "label": "Chan 1 level"},
        "rt": {"address": "/eos/chan/2", "label": "Chan 2 level"},
    }
)

PRESETS: dict[str, dict[str, Any]] = {
    "StickOSC": {
        "map": PRESET_STICKOSC_MAP,
        "osc_port": 9000,
        "osc_prefix": "/stickosc",
        "description": "Generic /stickosc/... addresses for TD, Max, Unreal, etc.",
    },
    "QLab": {
        "map": PRESET_QLAB_MAP,
        "osc_port": 53000,
        "osc_prefix": "",
        "description": "QLab workspace GO/Stop/Panic + selected cue helpers (UDP 53000).",
    },
    "ETC Eos": {
        "map": PRESET_EOS_MAP,
        "osc_port": 8000,
        "osc_prefix": "/eos",
        "description": "Eos keys + chan 1/2 levels and pan/tilt (UDP 8000).",
    },
}


def list_presets() -> list[str]:
    return list(PRESETS.keys())


def apply_preset(cfg: dict[str, Any], name: str) -> dict[str, Any]:
    """Return a deep-copied config with preset map + suggested OSC port applied.

    Preserves existing control ``type`` values when present; fills from preset otherwise.
    """
    if name not in PRESETS:
        raise KeyError(f"unknown preset {name!r}; choose from {list_presets()}")
    preset = PRESETS[name]
    out = deepcopy(cfg)
    out.setdefault("osc", {})
    out.setdefault("map", {})
    base_map = out.get("map") or {}
    new_map: dict[str, Any] = {}
    for key in MAP_KEYS:
        preset_entry = deepcopy(preset["map"][key])
        existing = base_map.get(key) or {}
        # Keep engine type from existing config if set
        if existing.get("type"):
            preset_entry["type"] = existing["type"]
        new_map[key] = preset_entry
    out["map"] = new_map
    if preset.get("osc_port") is not None:
        out["osc"]["port"] = int(preset["osc_port"])
    if preset.get("osc_prefix") is not None:
        out["osc"]["prefix"] = preset["osc_prefix"]
    return out
