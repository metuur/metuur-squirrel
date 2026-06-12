#!/usr/bin/env bash
# installer/uninstall.sh — remove Squirrel from this Mac, preserving every vault.
#
# Usage:
#   ./uninstall.sh            # interactive: prints the plan, asks to confirm
#   ./uninstall.sh --dry-run  # print the plan and exit; change nothing
#   ./uninstall.sh --yes      # skip the confirmation prompt
#
# Covers all three install footprints (.pkg system paths, drag-DMG and manual
# per-user paths, launchd service, agent packs, macOS Library dirs) in one run.
# It NEVER touches a vault: every `[[vaults]] path` in ~/.squirrel/config.toml is
# read first and preserved, including the vault's own .squirrel/ subfolder.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQUIRREL_HOME="$HOME/.squirrel"
CONFIG_FILE="$SQUIRREL_HOME/config.toml"

DRY_RUN=0
ASSUME_YES=0

# ─── Colors / helpers (house style) ──────────────────────────────────────────
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

# ─── Flags ───────────────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --yes|-y)  ASSUME_YES=1 ;;
    --help|-h) sed -n '2,13p' "$0"; exit 0 ;;
    *) die "Unknown argument: $arg (use --dry-run, --yes, or --help)" ;;
  esac
done

# ─── Guards ──────────────────────────────────────────────────────────────────
[[ "$(uname -s)" == "Darwin" ]] || die "Squirrel uninstall is macOS-only."
[[ "$(id -u)" -ne 0 ]] || die "Do not run as root. Run as your user; sudo is requested only for system paths."

# ─── Footprint inventory ─────────────────────────────────────────────────────
# The block between the two SQUIRREL-FOOTPRINT-SYNC markers is the shared
# removable footprint, duplicated verbatim from installer/install-snapshot.sh.
# An automated check (tests/installer/test_footprint_sync.sh) asserts the two
# copies stay identical. Edit BOTH copies together, keeping markers and order.
footprint_paths() {
  # >>> SQUIRREL-FOOTPRINT-SYNC >>>
  cat <<EOF
/Applications/Squirrel.app
/usr/local/bin/squirrel
/usr/local/bin/squirrel-backend
/usr/local/share/squirrel
$HOME/.local/bin/squirrel
$HOME/.local/bin/squirrel-backend
$HOME/Library/LaunchAgents/org.squirrel.web-ui.plist
$HOME/.squirrel
$HOME/.claude/plugins/squirrel
$HOME/.codex/squirrel
$HOME/.cursor/rules/squirrel
$HOME/.windsurf/rules/squirrel
$HOME/Library/Application Support/com.metuur.squirrel
$HOME/Library/Application Support/com.metuur.squirrel.dev
$HOME/Library/Caches/com.metuur.squirrel
$HOME/Library/Caches/com.metuur.squirrel.dev
$HOME/Library/WebKit/com.metuur.squirrel
$HOME/Library/WebKit/com.metuur.squirrel.dev
$HOME/Library/HTTPStorages/com.metuur.squirrel
$HOME/Library/HTTPStorages/com.metuur.squirrel.dev
$HOME/Library/Preferences/com.metuur.squirrel.plist
$HOME/Library/Preferences/com.metuur.squirrel.dev.plist
$HOME/Library/Saved Application State/com.metuur.squirrel.savedState
$HOME/Library/Saved Application State/com.metuur.squirrel.dev.savedState
EOF
  # <<< SQUIRREL-FOOTPRINT-SYNC <<<
}

# ─── Vault enumeration (preserve list) ───────────────────────────────────────
# Emit every `path` value that appears in a [[vaults]] table — and only there.
# Commented lines and `path` keys in other tables (e.g. [ai]) are ignored. The
# value's surrounding quotes are stripped; a leading ~ is expanded to $HOME.
parse_vault_paths() {
  [[ -f "$CONFIG_FILE" ]] || return 0
  /usr/bin/awk '
    /^[[:space:]]*#/                 { next }                 # comment line
    /^[[:space:]]*\[\[[[:space:]]*vaults[[:space:]]*\]\]/ { invault=1; next }
    /^[[:space:]]*\[\[/              { invault=0; next }      # other array-table
    /^[[:space:]]*\[[^[]/            { invault=0; next }      # other table header
    invault && /^[[:space:]]*path[[:space:]]*=/ {
      if (match($0, /"[^"]*"/) || match($0, /\x27[^\x27]*\x27/)) {
        print substr($0, RSTART+1, RLENGTH-2)
      }
    }
  ' "$CONFIG_FILE" 2>/dev/null || true
}

PRESERVE=()
load_preserve() {
  local p
  if [[ ! -f "$CONFIG_FILE" ]]; then
    warn "No config.toml found — cannot read vault paths; none will be specially preserved."
    warn "(Vaults never live inside ~/.squirrel, so removing app data is still safe.)"
    return 0
  fi
  while IFS= read -r p; do
    [[ -z "$p" ]] && continue
    p="${p/#\~/$HOME}"            # expand leading ~
    PRESERVE+=("$p")
  done < <(parse_vault_paths)
  if [[ ${#PRESERVE[@]} -eq 0 ]]; then
    warn "config.toml present but no [[vaults]] path entries found."
  fi
}

# ─── Removal plan (existing footprint paths only) ────────────────────────────
PLAN=()
build_plan() {
  local p
  while IFS= read -r p; do
    [[ -z "$p" ]] && continue
    if [[ -e "$p" || -L "$p" ]]; then
      PLAN+=("$p")
    fi
  done < <(footprint_paths)
}

print_plan() {
  hdr "Squirrel uninstall plan"
  if [[ ${#PLAN[@]} -eq 0 ]]; then
    info "No Squirrel files found — nothing to remove."
  else
    say "Will remove:"
    for p in "${PLAN[@]}"; do printf '  %s- %s%s\n' "$C_RED" "$p" "$C_RESET"; done
  fi
  say ""
  if [[ ${#PRESERVE[@]} -eq 0 ]]; then
    say "Vaults to preserve: ${C_DIM}(none recorded)${C_RESET}"
  else
    say "Vaults to preserve ${C_BOLD}(never touched)${C_RESET}:"
    for p in "${PRESERVE[@]}"; do printf '  %s✓ %s%s\n' "$C_GREEN" "$p" "$C_RESET"; done
  fi
  say ""
}

confirm() {
  [[ $ASSUME_YES -eq 1 ]] && return 0
  printf '%sType %sy%s to remove the above, anything else to cancel: %s' \
    "$C_BOLD" "$C_RED" "$C_BOLD" "$C_RESET"
  local reply; read -r reply
  [[ "$reply" =~ ^[Yy]$ ]] || { say "Cancelled — nothing was changed."; exit 0; }
}

# ─── Removal (vault safety gate: task 3.2; removals: Unit 4) ──────────────────
perform_removal() {
  warn "Removal is not yet wired in this build (vault gate + deletions land in"
  warn "subsequent tasks). No files were changed."
}

# ─── Main ────────────────────────────────────────────────────────────────────
main() {
  load_preserve
  build_plan
  print_plan

  if [[ $DRY_RUN -eq 1 ]]; then
    info "Dry run — nothing was changed."
    exit 0
  fi
  [[ ${#PLAN[@]} -eq 0 ]] && exit 0

  confirm
  perform_removal
}

main
