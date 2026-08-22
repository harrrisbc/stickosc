#!/usr/bin/env bash
# Build StickOSC.app on a Mac.
#
# Usage:
#   chmod +x tools/build_mac.sh
#   ./tools/build_mac.sh
#
# Important: use Python 3.11–3.13 (NOT 3.14+).
# pygame has no 3.14 wheels yet, so pip tries to compile and fails without SDL.
#
#   brew install python@3.12
#   PYTHON=python3.12 ./tools/build_mac.sh
#
# Output: dist/StickOSC.app

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: this script must run on macOS (found: $(uname -s))" >&2
  exit 1
fi

python_version() {
  local bin="$1"
  "$bin" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' 2>/dev/null || true
}

python_ok() {
  local bin="$1"
  [[ -x "$(command -v "$bin" 2>/dev/null || true)" ]] || command -v "$bin" >/dev/null 2>&1 || return 1
  local ver
  ver="$(python_version "$bin")"
  [[ -n "$ver" ]] || return 1
  local major minor
  IFS=. read -r major minor <<<"$ver"
  # pygame binary wheels: reliably 3.9–3.13 today; reject 3.14+
  if (( major == 3 && minor >= 9 && minor <= 13 )); then
    return 0
  fi
  return 1
}

pick_python() {
  if [[ -n "${PYTHON:-}" ]]; then
    if python_ok "$PYTHON"; then
      echo "$PYTHON"
      return 0
    fi
    echo "error: PYTHON=$PYTHON is not usable (need CPython 3.9–3.13)." >&2
    echo "       got: $($PYTHON --version 2>&1 || true)" >&2
    return 1
  fi

  local candidate
  for candidate in python3.12 python3.11 python3.13 python3.10 python3.9; do
    if command -v "$candidate" >/dev/null 2>&1 && python_ok "$candidate"; then
      echo "$candidate"
      return 0
    fi
  done

  if command -v python3 >/dev/null 2>&1 && python_ok python3; then
    echo python3
    return 0
  fi

  return 1
}

if ! PYTHON_BIN="$(pick_python)"; then
  echo "error: need Python 3.9–3.13 for pygame wheels." >&2
  echo >&2
  if command -v python3 >/dev/null 2>&1; then
    echo "  Your default python3 is: $(python3 --version 2>&1)" >&2
  fi
  echo "  Python 3.14+ cannot install pygame from pip yet (no wheel / needs SDL)." >&2
  echo >&2
  echo "Fix:" >&2
  echo "  brew install python@3.12" >&2
  echo "  rm -rf \"$ROOT/.venv\"" >&2
  echo "  PYTHON=python3.12 ./tools/build_mac.sh" >&2
  exit 1
fi

echo "==> StickOSC macOS build"
echo "    repo:    $ROOT"
echo "    python:  $PYTHON_BIN ($($PYTHON_BIN --version 2>&1))"

# Recreate venv if it points at a bad / missing interpreter (e.g. old 3.14 venv)
if [[ "${NO_VENV:-0}" != "1" ]]; then
  if [[ -d .venv ]]; then
    if [[ ! -x .venv/bin/python ]] || ! python_ok .venv/bin/python; then
      echo "==> Removing incompatible .venv (need Python 3.9–3.13)"
      rm -rf .venv
    fi
  fi
  if [[ ! -d .venv ]]; then
    echo "==> Creating .venv with $PYTHON_BIN"
    "$PYTHON_BIN" -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  PYTHON_BIN=python
  echo "    venv:    $ROOT/.venv ($($PYTHON_BIN --version 2>&1))"
fi

echo "==> Installing dependencies (binary wheels preferred)"
"$PYTHON_BIN" -m pip install --upgrade pip wheel
# Fail fast with a clear message if pip still tries to build pygame from source
if ! "$PYTHON_BIN" -m pip install -r requirements.txt -r requirements-dev.txt; then
  echo >&2
  echo "error: pip install failed." >&2
  echo "If you see pygame / SDL.h errors, you are on an unsupported Python." >&2
  echo "Use Python 3.12:" >&2
  echo "  brew install python@3.12" >&2
  echo "  rm -rf .venv && PYTHON=python3.12 ./tools/build_mac.sh" >&2
  exit 1
fi

echo "==> Cleaning previous build"
rm -rf build/macos dist/StickOSC.app dist/StickOSC

echo "==> Running PyInstaller (StickOSC.app)"
"$PYTHON_BIN" -m PyInstaller \
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
echo "If the app beachballs / Not Responding, rebuild after pull:"
echo "  cd ~/stickosc && git pull && rm -rf .venv dist build"
echo "  PYTHON=python3.12 ./tools/build_mac.sh"
echo
echo "Config file (after first run): ~/.stickosc/mapping.yaml"
