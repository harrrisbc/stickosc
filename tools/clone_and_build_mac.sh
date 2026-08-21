#!/usr/bin/env bash
# Clone StickOSC from GitHub and build StickOSC.app on macOS.
#
# One-shot (recommended):
#   curl -fsSL https://raw.githubusercontent.com/harrrisbc/stickosc/cursor/gui-standalone-app-5a6a/tools/clone_and_build_mac.sh | bash
#
# Or download / run from an existing checkout:
#   chmod +x tools/clone_and_build_mac.sh
#   ./tools/clone_and_build_mac.sh
#
# Env overrides:
#   REPO_URL   default: https://github.com/harrrisbc/stickosc.git
#   BRANCH     default: cursor/gui-standalone-app-5a6a  (GUI + Mac app branch)
#   DEST       default: ~/stickosc

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

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 not found. Install Python 3 from https://www.python.org/downloads/ or:" >&2
  echo "  brew install python" >&2
  exit 1
fi

REPO_URL="${REPO_URL:-https://github.com/harrrisbc/stickosc.git}"
BRANCH="${BRANCH:-cursor/gui-standalone-app-5a6a}"
DEST="${DEST:-$HOME/stickosc}"

echo "==> StickOSC clone + Mac build"
echo "    repo:   $REPO_URL"
echo "    branch: $BRANCH"
echo "    dest:   $DEST"

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
chmod +x tools/build_mac.sh
./tools/build_mac.sh

echo
echo "✓ Done. App path:"
echo "  $DEST/dist/StickOSC.app"
echo
echo "Open:"
echo "  open \"$DEST/dist/StickOSC.app\""
