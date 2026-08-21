#!/usr/bin/env bash
# Clone StickOSC from GitHub and build StickOSC.app on macOS.
#
# One-shot:
#   curl -fsSL https://raw.githubusercontent.com/harrrisbc/stickosc/cursor/gui-standalone-app-5a6a/tools/clone_and_build_mac.sh | bash
#
# Needs Python 3.9–3.13 (NOT 3.14). Recommended:
#   brew install python@3.12
#
# Env overrides:
#   REPO_URL   default: https://github.com/harrrisbc/stickosc.git
#   BRANCH     default: cursor/gui-standalone-app-5a6a
#   DEST       default: ~/stickosc
#   PYTHON     e.g. python3.12

set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: this script must run on macOS (found: $(uname -s))" >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "error: git not found. Install Xcode Command Line Tools:" >&2
  echo "  xcode-select --install" >&2
  exit 1
fi

REPO_URL="${REPO_URL:-https://github.com/harrrisbc/stickosc.git}"
BRANCH="${BRANCH:-cursor/gui-standalone-app-5a6a}"
DEST="${DEST:-$HOME/stickosc}"

echo "==> StickOSC clone + Mac build"
echo "    repo:   $REPO_URL"
echo "    branch: $BRANCH"
echo "    dest:   $DEST"

# Soft preflight: warn early about Python 3.14
if command -v python3 >/dev/null 2>&1; then
  PYVER="$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' 2>/dev/null || true)"
  if [[ "$PYVER" == "3.14" || "$PYVER" == "3.15" ]]; then
    echo
    echo "warning: default python3 is $PYVER — pygame will fail to install."
    echo "Install 3.12 first, then re-run:"
    echo "  brew install python@3.12"
    echo "  PYTHON=python3.12 DEST=\"$DEST\" bash $0"
    echo
    if ! command -v python3.12 >/dev/null 2>&1 && ! command -v python3.11 >/dev/null 2>&1; then
      echo "error: no Python 3.11/3.12 found on PATH." >&2
      exit 1
    fi
    export PYTHON="${PYTHON:-$(command -v python3.12 || command -v python3.11)}"
    echo "    will use: $PYTHON"
  fi
fi

if [[ -d "$DEST/.git" ]]; then
  echo "==> Repo exists — fetching / updating"
  git -C "$DEST" fetch --prune origin
  git -C "$DEST" checkout "$BRANCH"
  git -C "$DEST" pull --ff-only origin "$BRANCH"
else
  if [[ -e "$DEST" ]]; then
    echo "error: $DEST exists but is not a git repo. Set DEST=... to another folder." >&2
    exit 1
  fi
  echo "==> Cloning"
  git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$DEST"
fi

cd "$DEST"

# Drop broken 3.14 venv from previous attempt
if [[ -d .venv ]]; then
  if ! .venv/bin/python -c 'import sys; raise SystemExit(0 if (3,9) <= sys.version_info[:2] <= (3,13) else 1)' 2>/dev/null; then
    echo "==> Removing old incompatible .venv"
    rm -rf .venv
  fi
fi

chmod +x tools/build_mac.sh
./tools/build_mac.sh

echo
echo "✓ Done. App path:"
echo "  $DEST/dist/StickOSC.app"
echo
echo "Open:"
echo "  open \"$DEST/dist/StickOSC.app\""
