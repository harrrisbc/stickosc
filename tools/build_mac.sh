#!/usr/bin/env bash
# Build StickOSC.app on a Mac.
#
# Usage (from repo root OR from anywhere):
#   chmod +x tools/build_mac.sh
#   ./tools/build_mac.sh
#
# Output:
#   dist/StickOSC.app
#
# Then:
#   open dist/StickOSC.app
#   # optional: drag into /Applications

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: this script must run on macOS (found: $(uname -s))" >&2
  exit 1
fi

PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "error: python3 not found. Install Python 3 from python.org or brew." >&2
  exit 1
fi

echo "==> StickOSC macOS build"
echo "    repo: $ROOT"
echo "    python: $($PYTHON --version 2>&1)"

# Optional local venv so system Python stays clean
if [[ "${NO_VENV:-0}" != "1" ]]; then
  if [[ ! -d .venv ]]; then
    echo "==> Creating .venv"
    "$PYTHON" -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  PYTHON=python
  echo "    using venv: $ROOT/.venv"
fi

echo "==> Installing dependencies"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r requirements.txt -r requirements-dev.txt

echo "==> Cleaning previous build"
rm -rf build/macos dist/StickOSC.app dist/StickOSC

echo "==> Running PyInstaller (StickOSC.app)"
"$PYTHON" -m PyInstaller \
  --noconfirm \
  --clean \
  --distpath dist \
  --workpath build/macos \
  stickosc.macos.spec

APP="$ROOT/dist/StickOSC.app"
if [[ ! -d "$APP" ]]; then
  echo "error: dist/StickOSC.app was not created" >&2
  ls -la dist || true
  exit 1
fi

echo
echo "✓ Built: $APP"
echo
echo "Run it:"
echo "  open \"$APP\""
echo
echo "Optional — copy to Applications:"
echo "  cp -R \"$APP\" /Applications/"
echo
echo "First launch: if Gatekeeper blocks it,"
echo "  right-click StickOSC.app → Open  (or System Settings → Privacy & Security)"
echo
echo "Config file (after first run): ~/.stickosc/mapping.yaml"
