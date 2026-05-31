#!/usr/bin/env bash
#
# scripts/install-web-ui.sh — install the local web UI for Squirrel.
#
# The UI is a React 19 + Vite SPA backed by a stdlib-only Python JSON API.
# The compiled bundle is shipped at companions/web-ui/app/dist/ so most
# users do NOT need Node.js installed.
#
# This script:
#   1) Verifies Python 3.9+ and the `squirrel web` subcommand.
#   2) If a prebuilt dist/ is present → skip the build (default).
#   3) If no dist/ → checks Node 18+/npm and runs npm install + vite build.
#   4) --rebuild forces step 3 even when dist/ exists (after a code edit).
#
# Usage:
#   scripts/install-web-ui.sh             # interactive (uses prebuilt dist if present)
#   scripts/install-web-ui.sh --rebuild   # force npm install + vite build
#   scripts/install-web-ui.sh --quiet     # non-interactive

set -euo pipefail

QUIET=0
REBUILD=0
for arg in "$@"; do
  case "$arg" in
    --quiet)   QUIET=1 ;;
    --rebuild) REBUILD=1 ;;
    -h|--help)
      sed -n '1,25p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

# ── Step 1: Python 3.9+ check ──────────────────────────────────────────────
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌  Python 3 not found. The web UI needs Python 3.9 or newer." >&2
  exit 1
fi
PY_VER=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
PY_OK=$(python3 -c 'import sys; print(1 if sys.version_info >= (3, 9) else 0)')
if [ "$PY_OK" != "1" ]; then
  echo "❌  Python $PY_VER is too old. The web UI needs 3.9 or newer." >&2
  exit 1
fi

# ── Step 2: squirrel web subcommand ────────────────────────────────────────
if ! command -v squirrel >/dev/null 2>&1; then
  # Try common install locations
  for cand in \
      "$HOME/.local/bin/squirrel" \
      "/usr/local/bin/squirrel" \
      "$PWD/squirrel"; do
    if [ -x "$cand" ]; then
      SQUIRREL_BIN="$cand"
      break
    fi
  done
  if [ -z "${SQUIRREL_BIN:-}" ]; then
    echo "❌  'squirrel' command not found on PATH." >&2
    echo "    Add the install dir to PATH (try ~/.local/bin or /usr/local/bin)." >&2
    exit 1
  fi
else
  SQUIRREL_BIN=$(command -v squirrel)
fi

# Sanity probe: does `squirrel web --help` work?
if ! "$SQUIRREL_BIN" web --help >/dev/null 2>&1; then
  echo "❌  This squirrel CLI does not yet have the 'web' subcommand." >&2
  echo "    Update to v0.7+ and retry." >&2
  exit 1
fi

# ── Step 3: locate the app dir + check whether dist/ is prebuilt ───────────
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$HERE/../companions/web-ui/app"
if [ ! -d "$APP_DIR" ]; then
  echo "❌  companions/web-ui/app not found at $APP_DIR" >&2
  exit 1
fi
APP_DIR="$(cd "$APP_DIR" && pwd)"
DIST_DIR="$APP_DIR/dist"

NEEDS_BUILD=1
if [ -f "$DIST_DIR/index.html" ] && [ "$REBUILD" -ne 1 ]; then
  NEEDS_BUILD=0
  echo "✓  Found prebuilt UI at $DIST_DIR — skipping build."
  echo "   (Use --rebuild to force a fresh npm install + vite build.)"
fi

if [ "$NEEDS_BUILD" -eq 1 ]; then
  # ── Step 4: Node + npm check (only when actually building) ──────────────
  if ! command -v node >/dev/null 2>&1; then
    echo "❌  Node.js not found. To rebuild the UI you need Node 18+." >&2
    echo "    Install with: brew install node  (or use nvm)." >&2
    echo "    Or: use the prebuilt dist/ shipped with the plugin." >&2
    exit 1
  fi
  NODE_MAJOR=$(node -p 'parseInt(process.versions.node.split(".")[0], 10)')
  if [ "$NODE_MAJOR" -lt 18 ]; then
    echo "❌  Node $(node --version) is too old. Need 18 or newer." >&2
    exit 1
  fi
  if ! command -v npm >/dev/null 2>&1; then
    echo "❌  npm not found alongside node." >&2
    exit 1
  fi

  echo
  echo "📦  Installing UI dependencies with npm (one-time, ~30s)…"
  ( cd "$APP_DIR" && npm install --no-fund --no-audit )
  echo
  echo "🔨  Building the UI (vite build)…"
  ( cd "$APP_DIR" && npm run build )
fi

# ── Step 5: print the next steps ──────────────────────────────────────────
if [ "$QUIET" -ne 1 ]; then
  cat <<EOF

✅  Web UI is INSTALLED + BUILT but not yet running.

  Start it now:    squirrel web start
  Open in browser: squirrel web open
  Check status:    squirrel web status
  Stop it:         squirrel web stop

Default URL: http://127.0.0.1:3939  (only after you run \`squirrel web start\`)

To start it automatically at login on macOS, run:
  bash companions/web-ui/launchd/install.sh

To rebuild the UI after code changes:
  cd companions/web-ui/app && npm run build

To remove the web UI entirely later:
  squirrel web uninstall

EOF
  # Offer to start it right now (only if attached to a TTY)
  if [ -t 0 ] && [ -t 1 ]; then
    read -r -p "Start the Web UI now? [Y/n] " _ans || true
    case "$_ans" in
      n|N|no|NO) echo "OK — run 'squirrel web start' when you're ready." ;;
      *)         "$SQUIRREL_BIN" web start ;;
    esac
  fi
fi
