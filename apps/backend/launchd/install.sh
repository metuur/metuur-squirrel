#!/usr/bin/env bash
#
# companions/web-ui/launchd/install.sh — optional macOS auto-start.
#
# Installs ~/Library/LaunchAgents/org.squirrel.web-ui.plist so the web UI
# starts at login. Non-macOS hosts exit cleanly with a message (R-11.7).
#
# Usage:
#   bash companions/web-ui/launchd/install.sh           # install + load
#   bash companions/web-ui/launchd/install.sh --uninstall

set -euo pipefail

UNINSTALL=0
PORT=3939
for arg in "$@"; do
  case "$arg" in
    --uninstall) UNINSTALL=1 ;;
    --port=*)    PORT="${arg#--port=}" ;;
    -h|--help)
      sed -n '1,16p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

if [ "$(uname -s)" != "Darwin" ]; then
  echo "ℹ️   launchd auto-start is macOS-only. Nothing to do on this host."
  exit 0
fi

PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_NAME="org.squirrel.web-ui.plist"
PLIST="$PLIST_DIR/$PLIST_NAME"

if [ "$UNINSTALL" -eq 1 ]; then
  if [ -f "$PLIST" ]; then
    launchctl unload "$PLIST" 2>/dev/null || true
    rm -f "$PLIST"
    echo "✅  Removed $PLIST"
  else
    echo "ℹ️   $PLIST not present — nothing to remove."
  fi
  exit 0
fi

# Locate companions/web-ui/server.py (this script lives next to it)
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_PY="$HERE/../server.py"
if [ ! -f "$SERVER_PY" ]; then
  echo "❌  Could not find $SERVER_PY" >&2
  exit 1
fi
SERVER_PY="$(cd "$(dirname "$SERVER_PY")" && pwd)/server.py"

PYTHON_BIN="$(command -v python3 || true)"
[ -z "$PYTHON_BIN" ] && { echo "❌  python3 not on PATH" >&2; exit 1; }

mkdir -p "$PLIST_DIR"
sed -e "s|__PYTHON__|$PYTHON_BIN|g" \
    -e "s|__SERVER_PY__|$SERVER_PY|g" \
    -e "s|__PORT__|$PORT|g" \
    -e "s|__HOME__|$HOME|g" \
    "$HERE/plist.template" > "$PLIST"

mkdir -p "$HOME/.squirrel"

# (Re)load
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "✅  Installed $PLIST"
echo "    Web UI will auto-start at login on http://127.0.0.1:$PORT"
echo "    Uninstall:  bash $0 --uninstall"
