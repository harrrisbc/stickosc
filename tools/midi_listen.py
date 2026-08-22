#!/usr/bin/env python3
"""Tiny MIDI input listener for verifying StickOSC MIDI output."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime


def main() -> int:
    p = argparse.ArgumentParser(description="Listen for MIDI messages (e.g. from StickOSC)")
    p.add_argument("--port", default="StickOSC", help="input port name (substring match OK)")
    p.add_argument("--list", action="store_true", help="list MIDI input ports and exit")
    args = p.parse_args()

    try:
        import mido
    except ImportError:
        print("install deps: pip install -r requirements.txt", file=sys.stderr)
        return 1

    inputs = mido.get_input_names()
    if args.list:
        if not inputs:
            print("no MIDI input ports found")
        else:
            print("MIDI input ports:")
            for name in inputs:
                print(f"  · {name}")
        return 0

    match = None
    for name in inputs:
        if name == args.port or args.port.lower() in name.lower():
            match = name
            break
    if match is None:
        print(f"port {args.port!r} not found. Available:", file=sys.stderr)
        for name in inputs or ["(none)"]:
            print(f"  · {name}", file=sys.stderr)
        print("Tip: start StickOSC with --midi first (creates virtual StickOSC).", file=sys.stderr)
        return 1

    print(f"listening MIDI on {match}  (Ctrl+C to quit)")
    try:
        with mido.open_input(match) as port:
            while True:
                for msg in port.iter_pending():
                    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    print(f"{ts}  {msg}")
                time.sleep(0.005)
    except KeyboardInterrupt:
        print("\nstopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
