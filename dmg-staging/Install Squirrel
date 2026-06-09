#!/usr/bin/env bash
# installer/install.sh — Squirrel end-user installer (runs from inside the DMG).
#
# Usage:
#   ./install.sh           # interactive
#   ./install.sh --auto    # non-interactive: auto-detect agent, use ~/squirrel-vault
#
# No prerequisites — all binaries are bundled in the DMG.

set -euo pipefail

DMG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$DMG_DIR/bin"
AGENT_PACK="$DMG_DIR/agent-pack"
RESOURCES="$DMG_DIR/resources"
VERSION_IN_DMG="$(cat "$DMG_DIR/VERSION" 2>/dev/null || echo "unknown")"

INSTALL_BIN="$HOME/.local/bin"
SQUIRREL_HOME="$HOME/.squirrel"
PLIST_LABEL="org.squirrel.web-ui"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"
CONFIG_FILE="$SQUIRREL_HOME/config.toml"
VERSION_FILE="$SQUIRREL_HOME/version"
LOG_DIR="$SQUIRREL_HOME"

CLI_BIN="$INSTALL_BIN/squirrel"
BACKEND_BIN="$INSTALL_BIN/squirrel-backend"

AUTO_MODE=0
for arg in "$@"; do
  case "$arg" in --auto) AUTO_MODE=1 ;; esac
done

# ─── Colors ──────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  C_GREEN=$'\033[32m'; C_BLUE=$'\033[34m'; C_BOLD=$'\033[1m'
  C_YELLOW=$'\033[33m'; C_RED=$'\033[31m'; C_DIM=$'\033[2m'; C_RESET=$'\033[0m'
else
  C_GREEN=''; C_BLUE=''; C_BOLD=''; C_YELLOW=''; C_RED=''; C_DIM=''; C_RESET=''
fi
say()  { printf '%s\n' "$*"; }
ok()   { printf '%s✓  %s%s\n' "$C_GREEN"  "$*" "$C_RESET"; }
info() { printf '%s   %s%s\n' "$C_BLUE"   "$*" "$C_RESET"; }
warn() { printf '%s⚠  %s%s\n' "$C_YELLOW" "$*" "$C_RESET"; }
die()  { printf '%s✗  %s%s\n' "$C_RED"    "$*" "$C_RESET" >&2; exit 1; }
hdr()  { printf '\n%s── %s ──%s\n' "$C_BOLD" "$*" "$C_RESET"; }
ask()  { printf '%s%s%s ' "$C_BOLD" "$*" "$C_RESET"; read -r REPLY; }

# ─── Banner ──────────────────────────────────────────────────────────────────
printf '%s' "$C_BOLD"
cat <<'BANNER'

  ╔══════════════════════════════════════════════════════╗
  ║                                                      ║
  ║   🐿  Squirrel  —  Focus & Productivity Companion   ║
  ║                                                      ║
  ╚══════════════════════════════════════════════════════╝

BANNER
printf '%s' "$C_RESET"

# ─── Detect existing install ──────────────────────────────────────────────────
EXISTING_VERSION=""
IS_UPGRADE=0
if [[ -f "$VERSION_FILE" ]]; then
  EXISTING_VERSION="$(cat "$VERSION_FILE")"
  IS_UPGRADE=1
fi

if (( IS_UPGRADE )); then
  say "Existing install found: ${C_BOLD}v${EXISTING_VERSION}${C_RESET}"
  say "Upgrading to:           ${C_BOLD}v${VERSION_IN_DMG}${C_RESET}"
  say ""
  if (( ! AUTO_MODE )); then
    ask "Continue? [Y/n]"
    [[ "$REPLY" =~ ^[Nn] ]] && { say "Aborted."; exit 0; }
  fi
else
  say "Installing Squirrel ${C_BOLD}v${VERSION_IN_DMG}${C_RESET}"
  say ""
fi

# ─── Agent selection (fresh install only) ────────────────────────────────────
AGENT_INDICES=()
VAULT_PATH=""

AGENT_NAMES=("Claude Code" "Codex" "Cursor" "Windsurf")
AGENT_CHECK_DIRS=("$HOME/.claude" "$HOME/.codex" "$HOME/.cursor" "$HOME/.windsurf")
AGENT_PACK_DESTS=(
  "$HOME/.claude/plugins/squirrel"
  "$HOME/.codex/squirrel"
  "$HOME/.cursor/rules/squirrel"
  "$HOME/.windsurf/rules/squirrel"
)

if (( ! IS_UPGRADE )); then
  hdr "Which AI agent(s) do you use?"

  if (( AUTO_MODE )); then
    for i in "${!AGENT_CHECK_DIRS[@]}"; do
      [[ -d "${AGENT_CHECK_DIRS[$i]}" ]] && AGENT_INDICES+=("$i")
    done
    (( ${#AGENT_INDICES[@]} > 0 )) || die "No supported agent detected. Install Claude Code, Codex, Cursor, or Windsurf first."
  else
    for i in "${!AGENT_NAMES[@]}"; do
      label=""
      [[ -d "${AGENT_CHECK_DIRS[$i]}" ]] && label=" ${C_DIM}(detected)${C_RESET}"
      printf '  %d)  %s%s\n' "$((i+1))" "${AGENT_NAMES[$i]}" "$label"
    done
    say ""
    ask "Enter numbers separated by spaces or commas (e.g. 1 2):"
    # Normalise commas → spaces, then parse
    IFS=', ' read -ra _picks <<< "${REPLY//,/ }"
    for _p in "${_picks[@]}"; do
      [[ -z "$_p" ]] && continue
      _idx="$(( _p - 1 ))"
      (( _idx >= 0 && _idx < ${#AGENT_NAMES[@]} )) || die "Invalid choice: $_p"
      AGENT_INDICES+=("$_idx")
    done
    (( ${#AGENT_INDICES[@]} > 0 )) || die "No agents selected."
  fi

  _selected_labels=()
  for _i in "${AGENT_INDICES[@]}"; do
    _selected_labels+=("${AGENT_NAMES[$_i]}")
  done
  say "Agent(s): ${C_BOLD}$(IFS=', '; echo "${_selected_labels[*]}")${C_RESET}"

  # ─── Vault path ────────────────────────────────────────────────────────────
  hdr "Where is your vault?"
  if (( AUTO_MODE )); then
    VAULT_PATH="$HOME/squirrel-vault"
  else
    say "  Enter an existing folder path, or press Enter to create ~/squirrel-vault"
    ask "Vault path:"
    VAULT_PATH="${REPLY:-$HOME/squirrel-vault}"
    VAULT_PATH="${VAULT_PATH/#\~/$HOME}"
  fi
  say "Vault: ${C_BOLD}$VAULT_PATH${C_RESET}"
fi

say ""

# ─── Rollback helpers ─────────────────────────────────────────────────────────
OLD_CLI_BAK=""
OLD_BACKEND_BAK=""

_rollback() {
  warn "Something went wrong — rolling back"
  [[ -n "$OLD_CLI_BAK"     && -f "$OLD_CLI_BAK"     ]] && mv "$OLD_CLI_BAK"     "$CLI_BIN"     && warn "Restored previous squirrel binary"
  [[ -n "$OLD_BACKEND_BAK" && -f "$OLD_BACKEND_BAK" ]] && mv "$OLD_BACKEND_BAK" "$BACKEND_BIN" && warn "Restored previous squirrel-backend binary"
  [[ -f "$PLIST_PATH" ]] && launchctl load "$PLIST_PATH" 2>/dev/null || true
}
trap _rollback ERR

# ─── 1. Create directories ────────────────────────────────────────────────────
hdr "Installing"
mkdir -p "$INSTALL_BIN" "$SQUIRREL_HOME" "$HOME/Library/LaunchAgents"

# ─── 2. Stop service if upgrading ────────────────────────────────────────────
if (( IS_UPGRADE )) && [[ -f "$PLIST_PATH" ]]; then
  info "Stopping existing service..."
  launchctl unload "$PLIST_PATH" 2>/dev/null || true
fi

# ─── 3. Install CLI binary ────────────────────────────────────────────────────
# R-4.1: verify signature before copying; R-4.4: log success; R-4.3/4.6: abort on failure
info "Installing squirrel CLI..."
if ! codesign --verify --strict --deep "$BIN_DIR/squirrel" 2>/dev/null; then
  printf 'error: codesign verification failed for squirrel — refusing to install. Re-download the DMG from https://github.com/metuur/squirrel/releases.\n' >&2
  exit 1
fi
ok "codesign verified: squirrel"
[[ -f "$CLI_BIN" ]] && { OLD_CLI_BAK="${CLI_BIN}.bak"; cp "$CLI_BIN" "$OLD_CLI_BAK"; }
cp "$BIN_DIR/squirrel" "${CLI_BIN}.new"
mv "${CLI_BIN}.new" "$CLI_BIN"
chmod +x "$CLI_BIN"
ok "squirrel → $CLI_BIN"

# ─── 4. Install backend binary ───────────────────────────────────────────────
# R-4.2: verify signature before copying; R-4.4: log success; R-4.3/4.6: abort on failure
info "Installing squirrel-backend..."
if ! codesign --verify --strict --deep "$BIN_DIR/squirrel-backend" 2>/dev/null; then
  printf 'error: codesign verification failed for squirrel-backend — refusing to install. Re-download the DMG from https://github.com/metuur/squirrel/releases.\n' >&2
  exit 1
fi
ok "codesign verified: squirrel-backend"
[[ -f "$BACKEND_BIN" ]] && { OLD_BACKEND_BAK="${BACKEND_BIN}.bak"; cp "$BACKEND_BIN" "$OLD_BACKEND_BAK"; }
cp "$BIN_DIR/squirrel-backend" "${BACKEND_BIN}.new"
mv "${BACKEND_BIN}.new" "$BACKEND_BIN"
chmod +x "$BACKEND_BIN"
ok "squirrel-backend → $BACKEND_BIN"

# ─── 5. Write launchd plist ───────────────────────────────────────────────────
# The bundled template is the dev shape (__PYTHON__ __SERVER_PY__ … __TOKEN_FILE__).
# Installed runs use the compiled squirrel-backend binary, which needs no separate
# server.py, so we point __PYTHON__ at the binary and drop the __SERVER_PY__ arg.
info "Configuring background service..."
TOKEN_FILE="$SQUIRREL_HOME/launchd-token"
if [[ ! -f "$TOKEN_FILE" ]]; then
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32 > "$TOKEN_FILE"
  else
    head -c 32 /dev/urandom | xxd -p -c 256 > "$TOKEN_FILE"
  fi
  chmod 600 "$TOKEN_FILE"
fi
plist="$(cat "$RESOURCES/plist.template")"
plist="$(printf '%s\n' "$plist" | grep -v '__SERVER_PY__')"   # binary needs no server.py
plist="${plist//__PYTHON__/$BACKEND_BIN}"
plist="${plist//__BINARY__/$BACKEND_BIN}"                     # tolerate either template
plist="${plist//__SERVER_PY__/}"
plist="${plist//__PORT__/3939}"
plist="${plist//__TOKEN_FILE__/$TOKEN_FILE}"
plist="${plist//__HOME__/$HOME}"
printf '%s\n' "$plist" > "$PLIST_PATH"
ok "launchd plist → $PLIST_PATH"

# ─── 6. Seed config (never overwrite) ────────────────────────────────────────
if [[ ! -f "$CONFIG_FILE" ]]; then
  info "Creating config..."
  cp "$RESOURCES/squirrel.toml.example" "$CONFIG_FILE"
  if [[ -n "$VAULT_PATH" ]]; then
    sed -i '' "s|path = \".*\"|path = \"$VAULT_PATH\"|" "$CONFIG_FILE" 2>/dev/null || true
  fi
  ok "config → $CONFIG_FILE"
fi

# Create vault folder if it doesn't exist
if [[ -n "$VAULT_PATH" && ! -d "$VAULT_PATH" ]]; then
  mkdir -p "$VAULT_PATH"
  ok "vault created → $VAULT_PATH"
fi

# ─── 7. Start service ─────────────────────────────────────────────────────────
info "Starting background service..."
launchctl load "$PLIST_PATH"
ok "squirrel-backend running on http://127.0.0.1:3939"

# ─── 8. Request notification permission ──────────────────────────────────────
info "Requesting notification permission..."
osascript -e 'display notification "Squirrel is ready" with title "Squirrel" subtitle "Focus & Productivity Companion"' 2>/dev/null || true

# ─── 9. Write version stamp ───────────────────────────────────────────────────
printf '%s\n' "$VERSION_IN_DMG" > "$VERSION_FILE"

# ─── 10. Install agent-pack (LAST — commit step) ─────────────────────────────
hdr "Installing agent-pack"

AGENT_PACK_DESTS_SELECTED=()
if (( IS_UPGRADE )); then
  # Re-detect all agents present on disk
  for i in "${!AGENT_CHECK_DIRS[@]}"; do
    [[ -d "${AGENT_CHECK_DIRS[$i]}" ]] && AGENT_PACK_DESTS_SELECTED+=("${AGENT_PACK_DESTS[$i]}")
  done
else
  for _i in "${AGENT_INDICES[@]}"; do
    AGENT_PACK_DESTS_SELECTED+=("${AGENT_PACK_DESTS[$_i]}")
  done
fi

if (( ${#AGENT_PACK_DESTS_SELECTED[@]} > 0 )); then
  for dest in "${AGENT_PACK_DESTS_SELECTED[@]}"; do
    mkdir -p "$dest"
    rsync -a --delete "$AGENT_PACK/" "$dest/"
    ok "agent-pack → $dest"
  done
else
  warn "No agent directory found — skipping agent-pack install"
  warn "Run the installer again after installing Claude Code, Codex, Cursor, or Windsurf"
fi

# ─── Done ─────────────────────────────────────────────────────────────────────
rm -f "$OLD_CLI_BAK" "$OLD_BACKEND_BAK"
trap - ERR

say ""
printf '%s' "$C_BOLD"
if (( IS_UPGRADE )); then
  printf '  Upgraded  v%s → v%s  ✓\n' "$EXISTING_VERSION" "$VERSION_IN_DMG"
else
  printf '  Squirrel v%s installed  ✓\n' "$VERSION_IN_DMG"
fi
printf '%s' "$C_RESET"
say ""
say "  Open your agent and type:  /sq-status"
say ""
