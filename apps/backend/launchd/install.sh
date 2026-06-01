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
TOKEN_FILE="$HOME/.squirrel/launchd-token"

# Verify an existing token file against the R-2.3 checks shared with the
# backend: mode 0600, owned by the running user, exactly 64 hex chars. Echoes
# the failed check to stderr (never the token value). Returns non-zero on fail.
_verify_token_file() {
  local f="$1"
  [ -f "$f" ] || { echo "token-file missing: $f" >&2; return 1; }
  # Use /usr/bin/stat explicitly: this script is macOS-only (guarded above), so
  # BSD stat is always present, and a Homebrew GNU coreutils `stat` on PATH
  # would otherwise misread `-f` as --file-system.
  local mode owner content
  mode="$(/usr/bin/stat -f '%Lp' "$f")"
  owner="$(/usr/bin/stat -f '%Su' "$f")"
  if [ "$mode" != "600" ]; then
    echo "token-file must be mode 0600, found $mode: $f" >&2
    return 1
  fi
  if [ "$owner" != "$USER" ]; then
    echo "token-file must be owned by $USER, found $owner: $f" >&2
    return 1
  fi
  content="$(cat "$f")"
  if ! printf '%s' "$content" | grep -Eq '^[0-9a-fA-F]{64}$'; then
    echo "token-file must contain exactly 64 hex chars: $f" >&2
    return 1
  fi
  return 0
}

# R-5.1/R-5.2: ensure ~/.squirrel/launchd-token exists, is valid, and is 0600.
# Preserve an existing valid file (idempotent reinstall); mint a fresh CSPRNG
# token otherwise. If the file exists but fails validation, exit non-zero
# rather than silently overwriting. The token value is never printed.
ensure_launchd_token() {
  local f="$TOKEN_FILE"
  mkdir -p "$(dirname "$f")"
  if [ -f "$f" ]; then
    if _verify_token_file "$f"; then
      return 0
    fi
    echo "❌  Existing $f failed validation (see above). Refusing to overwrite." >&2
    echo "    Fix the file's mode/owner/contents, or run: bash $0 --reinstall" >&2
    exit 1
  fi
  # umask 077 closes any window where the file is briefly world-readable.
  local prev_umask; prev_umask="$(umask)"
  umask 077
  openssl rand -hex 32 > "$f"
  umask "$prev_umask"
  chmod 600 "$f"
}

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

command -v openssl >/dev/null 2>&1 || { echo "❌  openssl not on PATH" >&2; exit 1; }

# R-5.1: provision the launchd token BEFORE rendering the plist so the
# --token-file path (R-5.3) points at a file that already exists and is valid.
ensure_launchd_token

mkdir -p "$PLIST_DIR"
sed -e "s|__PYTHON__|$PYTHON_BIN|g" \
    -e "s|__SERVER_PY__|$SERVER_PY|g" \
    -e "s|__PORT__|$PORT|g" \
    -e "s|__TOKEN_FILE__|$TOKEN_FILE|g" \
    -e "s|__HOME__|$HOME|g" \
    "$HERE/plist.template" > "$PLIST"

mkdir -p "$HOME/.squirrel"

# (Re)load
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "✅  Installed $PLIST"
echo "    Web UI will auto-start at login on http://127.0.0.1:$PORT"
echo "    Uninstall:  bash $0 --uninstall"
