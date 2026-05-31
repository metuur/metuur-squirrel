#!/bin/bash
# squirrel macOS Reminder Daemon — Installer
#
# Usage:
#   install.sh          → install and start daemon
#   install.sh --uninstall → stop and remove daemon

set -euo pipefail

LABEL="org.squirrel.reminders"
PLIST_DEST="${HOME}/Library/LaunchAgents/${LABEL}.plist"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON_SCRIPT="${SCRIPT_DIR}/reminder-daemon.sh"
LOG_PATH="${HOME}/.squirrel/reminders-daemon.log"

# ─── OS check ────────────────────────────────────────────────────────────────

if [[ "$(uname)" != "Darwin" ]]; then
    echo "ℹ️  squirrel macOS reminder daemon: non-macOS host detected — skipping installation."
    exit 0
fi

# ─── Uninstall ────────────────────────────────────────────────────────────────

if [[ "${1:-}" == "--uninstall" ]]; then
    echo "🗑️  Uninstalling squirrel reminder daemon..."
    if launchctl list "$LABEL" >/dev/null 2>&1; then
        launchctl bootout "gui/$(id -u)" "$PLIST_DEST" 2>/dev/null \
            || launchctl unload "$PLIST_DEST" 2>/dev/null || true
        echo "   ✓ Service unloaded."
    else
        echo "   ℹ️  Service was not loaded."
    fi
    if [ -f "$PLIST_DEST" ]; then
        rm -f "$PLIST_DEST"
        echo "   ✓ Plist removed: $PLIST_DEST"
    fi
    echo "✅ Daemon uninstalled."
    exit 0
fi

# ─── Install ─────────────────────────────────────────────────────────────────

echo "🔧 Installing squirrel reminder daemon..."

if [ ! -f "$DAEMON_SCRIPT" ]; then
    echo "❌ Daemon script not found: $DAEMON_SCRIPT"
    exit 1
fi

chmod +x "$DAEMON_SCRIPT"

# Render plist from template
TEMPLATE="${SCRIPT_DIR}/plist.template"
if [ ! -f "$TEMPLATE" ]; then
    echo "❌ plist.template not found: $TEMPLATE"
    exit 1
fi

mkdir -p "${HOME}/Library/LaunchAgents"
mkdir -p "$(dirname "$LOG_PATH")"

sed \
    -e "s|__DAEMON_PATH__|${DAEMON_SCRIPT}|g" \
    -e "s|__LOG_PATH__|${LOG_PATH}|g" \
    -e "s|__HOME__|${HOME}|g" \
    "$TEMPLATE" > "$PLIST_DEST"

echo "   ✓ Plist written: $PLIST_DEST"

# Unload any existing instance first
launchctl bootout "gui/$(id -u)" "$PLIST_DEST" 2>/dev/null \
    || launchctl unload "$PLIST_DEST" 2>/dev/null || true

# Load
launchctl bootstrap "gui/$(id -u)" "$PLIST_DEST" 2>/dev/null \
    || launchctl load "$PLIST_DEST"

echo "   ✓ Service loaded: $LABEL"
echo ""
echo "✅ Daemon installed. It will poll every 2 hours during your workday window."
echo "   Log: $LOG_PATH"
echo "   To test immediately: bash \"$DAEMON_SCRIPT\" --force"
echo "   To uninstall:        bash \"$SCRIPT_DIR/install.sh\" --uninstall"
