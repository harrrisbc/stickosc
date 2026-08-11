#!/usr/bin/env python3
"""Tiny OSC UDP listener for verifying StickOSC output."""

from __future__ import annotations

import argparse
from datetime import datetime

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer


def make_handler(verbose: bool):
    def handler(address: str, *args) -> None:
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        payload = ", ".join(str(a) for a in args)
        if verbose or address.startswith("/xbox/btn") or address.startswith("/xbox/dpad"):
            print(f"{ts}  {address}  {payload}")
        else:
            # axes / triggers: overwrite one status line-ish
            print(f"{ts}  {address}  {payload}")

    return handler


def main() -> int:
    p = argparse.ArgumentParser(description="Listen for StickOSC UDP messages")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=9000)
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    dispatcher = Dispatcher()
    dispatcher.set_default_handler(make_handler(args.verbose))

    server = BlockingOSCUDPServer((args.host, args.port), dispatcher)
    print(f"listening OSC on {args.host}:{args.port}  (Ctrl+C to quit)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
