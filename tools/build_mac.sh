#!/usr/bin/env bash
# Build StickOSC on macOS → dist/StickOSC.app (windowed) or dist/StickOSC.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install -r requirements.txt -r requirements-dev.txt
python3 -m PyInstaller --noconfirm --clean --windowed stickosc.spec
# PyInstaller windowed builds on macOS also emit StickOSC.app when using onedir;
# onefile + windowed yields dist/StickOSC (double-clickable). Prefer .app via onedir:
if [[ ! -d dist/StickOSC.app ]]; then
  python3 -m PyInstaller --noconfirm --clean --windowed --name StickOSC \
    --add-data "mapping.yaml:." \
    --hidden-import stickosc \
    --hidden-import pygame \
    --hidden-import yaml \
    --hidden-import pythonosc \
    --hidden-import mido \
    gui_app.py
fi
echo "Built under dist/ (StickOSC.app and/or StickOSC)"
ls -la dist || true
