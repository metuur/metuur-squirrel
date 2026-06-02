#!/usr/bin/env bash
#
# install-manual.sh — Squirrel manual installer (no signing required).
#
# Run this when "Install Squirrel" is blocked by macOS Gatekeeper.
# Ships inside squirrel-manual-install.zip alongside the binaries.
#
# Usage:
#   bash install-manual.sh          # interactive
#   bash install-manual.sh --yes    # non-interactive (uses defaults)
#
# What it installs:
#   1. CLI binary           → ~/.local/bin/squirrel
#   2. Backend daemon       → ~/.local/bin/squirrel-backend
#   3. Agent-pack           → ~/.claude/plugins/squirrel/
#   4. Config seed          → ~/.squirrel/config.toml  (if missing)
#   5. Auth token           → ~/.squirrel/launchd-token
#   6. launchd plist        → ~/Library/LaunchAgents/org.squirrel.web-ui.plist
#   7. Daemon               → started via launchctl

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ─── Flags ────────────────────────────────────────────────────────────────────
AUTO=0
for arg in "$@"; do
  case "$arg" in
    --yes|-y) AUTO=1 ;;
    --help|-h)
      sed -n '1,14p' "$0"; exit 0 ;;
    *)
      printf 'Unknown argument: %s\n' "$arg" >&2; exit 1 ;;
  esac
done

# ─── Colors ───────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  C_GREEN=$'\033[32m'; C_BLUE=$'\033[34m'; C_BOLD=$'\033[1m'
  C_YELLOW=$'\033[33m'; C_RED=$'\033[31m'; C_RESET=$'\033[0m'
else
  C_GREEN=''; C_BLUE=''; C_BOLD=''; C_YELLOW=''; C_RED=''; C_RESET=''
fi
say()  { printf '%s\n' "$*"; }
ok()   { printf '%s✓  %s%s\n' "$C_GREEN"  "$*" "$C_RESET"; }
info() { printf '%s   %s%s\n' "$C_BLUE"   "$*" "$C_RESET"; }
warn() { printf '%s⚠  %s%s\n' "$C_YELLOW" "$*" "$C_RESET"; }
die()  { printf '%s✗  %s%s\n' "$C_RED"    "$*" "$C_RESET" >&2; exit 1; }
hdr()  { printf '\n%s── %s ──%s\n' "$C_BOLD" "$*" "$C_RESET"; }
ask()  { printf '%s%s%s ' "$C_BOLD" "$*" "$C_RESET"; read -r REPLY; }

# ─── Validate bundle ──────────────────────────────────────────────────────────
[[ -f "$SCRIPT_DIR/bin/squirrel"         ]] || die "bin/squirrel not found next to this script"
[[ -f "$SCRIPT_DIR/bin/squirrel-backend" ]] || die "bin/squirrel-backend not found next to this script"
[[ -d "$SCRIPT_DIR/agent-pack"           ]] || die "agent-pack/ not found next to this script"

HAS_APP=0
[[ -d "$SCRIPT_DIR/Squirrel.app" ]] && HAS_APP=1

VERSION="$(cat "$SCRIPT_DIR/VERSION" 2>/dev/null || echo "unknown")"

# ─── Banner ───────────────────────────────────────────────────────────────────
printf '%s' "$C_BOLD"
cat <<'BANNER'

  ╔══════════════════════════════════════════════════════╗
  ║                                                      ║
  ║   🐿  Squirrel — Manual Installer (no signing)      ║
  ║                                                      ║
  ╚══════════════════════════════════════════════════════╝

BANNER
printf '%s' "$C_RESET"
say "Version: ${C_BOLD}${VERSION}${C_RESET}"
say "This installer skips codesign checks — for dev builds and Gatekeeper-blocked installs."
say ""
say "  Components bundled:"
say "    CLI binary       bin/squirrel"
say "    Backend daemon   bin/squirrel-backend"
(( HAS_APP )) && say "    Desktop app      Squirrel.app"
say "    Agent-pack       skills + slash commands"
say ""

if (( ! AUTO )); then
  ask "Continue? [Y/n]"
  [[ "$REPLY" =~ ^[Nn] ]] && { say "Aborted."; exit 0; }
fi

# ─── Paths ────────────────────────────────────────────────────────────────────
INSTALL_BIN="$HOME/.local/bin"
PLUGIN_DIR="$HOME/.claude/plugins/squirrel"
SQUIRREL_HOME="$HOME/.squirrel"
TOKEN_FILE="$SQUIRREL_HOME/launchd-token"
CONFIG_FILE="$SQUIRREL_HOME/config.toml"
PLIST_PATH="$HOME/Library/LaunchAgents/org.squirrel.web-ui.plist"
CLI_BIN="$INSTALL_BIN/squirrel"
BACKEND_BIN="$INSTALL_BIN/squirrel-backend"
PORT=3939

mkdir -p "$INSTALL_BIN" "$SQUIRREL_HOME" "$HOME/Library/LaunchAgents"

# ─── Step 1: Strip quarantine from bundle ─────────────────────────────────────
hdr "Step 1 — Remove macOS quarantine"
info "xattr -cr (this directory)"
xattr -cr "$SCRIPT_DIR" 2>/dev/null || true
ok "quarantine flag removed"

# ─── Step 2: Copy CLI binary ──────────────────────────────────────────────────
hdr "Step 2 — Install CLI binary"
info "squirrel → $CLI_BIN"
cp "$SCRIPT_DIR/bin/squirrel" "$CLI_BIN"
chmod +x "$CLI_BIN"
xattr -d com.apple.quarantine "$CLI_BIN" 2>/dev/null || true
ok "squirrel installed"

# ─── Step 3: Copy backend binary ──────────────────────────────────────────────
hdr "Step 3 — Install backend daemon binary"
info "squirrel-backend → $BACKEND_BIN"
cp "$SCRIPT_DIR/bin/squirrel-backend" "$BACKEND_BIN"
chmod +x "$BACKEND_BIN"
xattr -d com.apple.quarantine "$BACKEND_BIN" 2>/dev/null || true
ok "squirrel-backend installed"

# ─── Step 3b: Install Squirrel.app → /Applications ───────────────────────────
if (( HAS_APP )); then
  hdr "Step 3b — Install Squirrel.app"
  APP_DEST="/Applications/Squirrel.app"
  if [[ -d "$APP_DEST" ]]; then
    warn "Existing $APP_DEST found"
    if (( ! AUTO )); then
      ask "Replace it? [Y/n]"
      [[ "$REPLY" =~ ^[Nn] ]] && { info "Skipping Squirrel.app install"; HAS_APP=0; }
    fi
  fi
  if (( HAS_APP )); then
    info "Copying Squirrel.app → /Applications/"
    rm -rf "$APP_DEST"
    cp -r "$SCRIPT_DIR/Squirrel.app" "$APP_DEST"
    # Strip quarantine from the entire .app bundle
    xattr -cr "$APP_DEST" 2>/dev/null || true
    xattr -d com.apple.quarantine "$APP_DEST" 2>/dev/null || true
    chmod +x "$APP_DEST/Contents/MacOS/"* 2>/dev/null || true
    ok "Squirrel.app → /Applications/Squirrel.app"
  fi
fi

# ─── Step 4: PATH check ───────────────────────────────────────────────────────
hdr "Step 4 — PATH"
SHELL_RC=""
case "${SHELL:-}" in
  */zsh)  SHELL_RC="$HOME/.zshrc" ;;
  */bash) SHELL_RC="$HOME/.bash_profile" ;;
esac

if echo "$PATH" | tr ':' '\n' | grep -qx "$INSTALL_BIN"; then
  ok "$INSTALL_BIN already on PATH"
else
  warn "$INSTALL_BIN is not on PATH"
  if [[ -n "$SHELL_RC" ]]; then
    printf 'export PATH="%s:$PATH"\n' "$INSTALL_BIN" >> "$SHELL_RC"
    ok "Added to $SHELL_RC — open a new terminal tab after install"
  else
    warn "Add this line to your shell config manually:"
    say "  export PATH=\"$INSTALL_BIN:\$PATH\""
  fi
fi

# ─── Step 5: Install as Claude Code plugin ────────────────────────────────────
hdr "Step 5 — Register Claude Code plugin"

CLAUDE_PLUGINS_DIR="$HOME/.claude/plugins"
INSTALLED_PLUGINS_JSON="$CLAUDE_PLUGINS_DIR/installed_plugins.json"
PLUGIN_KEY="squirrel@squirrel"

# Remove any legacy squirrel symlink so we can place a real directory
if [[ -L "$PLUGIN_DIR" ]]; then
  warn "Removing legacy squirrel symlink: $PLUGIN_DIR → $(readlink "$PLUGIN_DIR")"
  rm "$PLUGIN_DIR"
fi

# Copy agent-pack files into the plugin directory
info "Copying agent-pack → $PLUGIN_DIR"
mkdir -p "$PLUGIN_DIR"
rsync -a --delete "$SCRIPT_DIR/agent-pack/" "$PLUGIN_DIR/"
ok "Plugin files installed"

# Register in installed_plugins.json so Claude Code loads it
INSTALL_TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")"
PLUGIN_VERSION="$(cat "$SCRIPT_DIR/VERSION" 2>/dev/null || echo "0.0.0")"

info "Registering in $INSTALLED_PLUGINS_JSON"
python3 - <<PYEOF
import json, os, sys

path = os.path.expanduser("$INSTALLED_PLUGINS_JSON")
os.makedirs(os.path.dirname(path), exist_ok=True)

# Load or init the registry
try:
    with open(path) as f:
        registry = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    registry = {"version": 2, "plugins": {}}

if "version" not in registry:
    registry["version"] = 2
if "plugins" not in registry:
    registry["plugins"] = {}

canonical_key = "$PLUGIN_KEY"
now = "$INSTALL_TIMESTAMP"
new_version = "$PLUGIN_VERSION"
install_path = "$PLUGIN_DIR"

# Find any existing squirrel entry (may be under squirrel@local or another variant)
stale_keys = [k for k in registry["plugins"] if k != canonical_key and k.startswith("squirrel@")]
existing = registry["plugins"].get(canonical_key, [{}])[0]

# Preserve the original installedAt if this is an update
installed_at = existing.get("installedAt", now)
old_version  = existing.get("version", "")

entry = {
    "scope": "user",
    "installPath": install_path,
    "version": new_version,
    "installedAt": installed_at,
    "lastUpdated": now,
}

# Remove stale keys (e.g. squirrel@local from older installer runs)
for k in stale_keys:
    del registry["plugins"][k]
    print("  removed stale key: %s" % k)

registry["plugins"][canonical_key] = [entry]

with open(path, "w") as f:
    json.dump(registry, f, indent=4)

action = "updated" if old_version else "registered"
print("  %s: %s v%s" % (action, canonical_key, new_version))
if old_version and old_version != new_version:
    print("  version: %s → %s" % (old_version, new_version))
PYEOF

ok "Plugin registered in installed_plugins.json"
say ""
info "Verify inside Claude Code with:  /plugin list"

# ─── Step 6: Seed config ──────────────────────────────────────────────────────
hdr "Step 6 — Config"
if [[ -f "$CONFIG_FILE" ]]; then
  ok "Config already exists — skipping: $CONFIG_FILE"
else
  info "Creating config from template"
  if [[ -f "$SCRIPT_DIR/resources/squirrel.toml.example" ]]; then
    cp "$SCRIPT_DIR/resources/squirrel.toml.example" "$CONFIG_FILE"
  else
    # Minimal fallback if resources/ is absent
    cat > "$CONFIG_FILE" << 'TOML'
default_email = "you@example.com"
machine_environment = "personal"

[[vaults]]
name = "personal"
path = "~/squirrel-vault"
default = true

[projects]
active = []

[compliance]
strict = false
allowed_inbound_tags = ["*"]
allowed_inbound_environments = ["personal", "work"]

[encryption]
enabled = false
gpg_recipient = ""
TOML
  fi

  if (( ! AUTO )); then
    say ""
    say "  Set your vault path in: ${C_BOLD}$CONFIG_FILE${C_RESET}"
    ask "  Enter vault path (or press Enter to use ~/squirrel-vault):"
    VAULT_PATH="${REPLY:-$HOME/squirrel-vault}"
    VAULT_PATH="${VAULT_PATH/#\~/$HOME}"
    # Replace the placeholder path
    sed -i '' "s|path = \"~/squirrel-vault\"|path = \"$VAULT_PATH\"|" "$CONFIG_FILE" 2>/dev/null || true
    [[ -d "$VAULT_PATH" ]] || mkdir -p "$VAULT_PATH"
    ok "Vault: $VAULT_PATH"
  fi

  ok "Config created → $CONFIG_FILE"
fi

# ─── Step 7: Generate auth token ──────────────────────────────────────────────
hdr "Step 7 — Auth token"
if [[ -f "$TOKEN_FILE" ]]; then
  # Validate existing token
  CHARS="$(wc -c < "$TOKEN_FILE" | tr -d ' ')"
  PERMS="$(/usr/bin/stat -f '%Lp' "$TOKEN_FILE" 2>/dev/null || echo "unknown")"
  if [[ "$CHARS" == "65" && "$PERMS" == "600" ]]; then
    ok "Existing token is valid — skipping"
  else
    warn "Existing token invalid (chars=$CHARS, mode=$PERMS) — regenerating"
    rm -f "$TOKEN_FILE"
  fi
fi

if [[ ! -f "$TOKEN_FILE" ]]; then
  info "Generating 64-char hex token via openssl"
  prev_umask="$(umask)"
  umask 077
  openssl rand -hex 32 > "$TOKEN_FILE"
  umask "$prev_umask"
  chmod 600 "$TOKEN_FILE"
  ok "Token written → $TOKEN_FILE (mode 0600)"
fi

# ─── Step 8: Install launchd plist ────────────────────────────────────────────
hdr "Step 8 — launchd daemon"

# Unload any previous version
if [[ -f "$PLIST_PATH" ]]; then
  info "Unloading previous plist"
  launchctl unload "$PLIST_PATH" 2>/dev/null || true
fi

info "Writing plist → $PLIST_PATH"
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>org.squirrel.web-ui</string>
  <key>ProgramArguments</key>
  <array>
    <string>$BACKEND_BIN</string>
    <string>--port</string>
    <string>$PORT</string>
    <string>--token-file</string>
    <string>$TOKEN_FILE</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <dict>
    <key>SuccessfulExit</key>
    <false/>
  </dict>
  <key>StandardOutPath</key>
  <string>$SQUIRREL_HOME/web-ui.stdout.log</string>
  <key>StandardErrorPath</key>
  <string>$SQUIRREL_HOME/web-ui.stderr.log</string>
  <key>WorkingDirectory</key>
  <string>$HOME</string>
</dict>
</plist>
EOF

# Safety check — no unexpanded placeholders
if grep -q '__' "$PLIST_PATH" 2>/dev/null; then
  die "Plist has unexpanded placeholder — this is a bug, please report it"
fi
ok "Plist written"

info "Loading daemon (launchctl load)"
launchctl load "$PLIST_PATH"
ok "Daemon started on http://127.0.0.1:$PORT"

# ─── Step 9: Verify ───────────────────────────────────────────────────────────
hdr "Step 9 — Verify"

# Give the server a moment to start
sleep 1

DAEMON_PID="$(launchctl list 2>/dev/null | awk '/org.squirrel.web-ui/ {print $1}')"
if [[ -n "$DAEMON_PID" && "$DAEMON_PID" != "-" ]]; then
  ok "Daemon running (PID $DAEMON_PID)"
else
  warn "Daemon PID not detected — check logs:"
  warn "  tail -30 $SQUIRREL_HOME/web-ui.stderr.log"
fi

# ─── Summary ──────────────────────────────────────────────────────────────────
say ""
printf '%s' "$C_BOLD"
printf '  Squirrel v%s installed (manual)  ✓\n' "$VERSION"
printf '%s' "$C_RESET"
say ""
say "  What was installed:"
say "    CLI binary      → $CLI_BIN"
say "    Backend daemon  → $BACKEND_BIN"
(( HAS_APP )) && say "    Desktop app     → /Applications/Squirrel.app"
say "    Agent-pack      → $PLUGIN_DIR"
say "    Config          → $CONFIG_FILE"
say "    Auth token      → $TOKEN_FILE"
say "    launchd plist   → $PLIST_PATH"
say ""
say "  Next steps:"
say "    1. Open a new terminal tab (or: source ~/.zshrc)"
say "    2. Set your vault path:"
say "         \$EDITOR $CONFIG_FILE"
say "    3. Restart Claude Code, then type:"
say "         /sq-status"
(( HAS_APP )) && say "    4. Launch the desktop app: open /Applications/Squirrel.app"
say ""
say "  Daemon logs:"
say "    tail -f $SQUIRREL_HOME/web-ui.stdout.log"
say "    tail -f $SQUIRREL_HOME/web-ui.stderr.log"
say ""
say "  Daemon management:"
say "    launchctl list | grep squirrel          # check if running"
say "    launchctl unload $PLIST_PATH   # stop"
say "    launchctl load   $PLIST_PATH   # start"
say ""
say "  Uninstall:"
say "    launchctl unload $PLIST_PATH"
say "    rm -rf $INSTALL_BIN/squirrel $INSTALL_BIN/squirrel-backend"
say "    rm -rf $PLUGIN_DIR $PLIST_PATH"
(( HAS_APP )) && say "    rm -rf /Applications/Squirrel.app"
say ""
