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
$HOME/.local/bin/squirrel.bak
$HOME/.local/bin/squirrel-backend.bak
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

# ─── Vault safety gate ───────────────────────────────────────────────────────
# Canonicalize a path for COMPARISON only: strip trailing slashes and resolve
# symlinks (including a symlinked leaf directory, via cd+pwd -P) so a vault that
# points into app data is compared at its real location. Always succeeds — an
# unresolvable path falls back to its lexical form. NOTE: deletion (Unit 4) uses
# the literal PLAN paths, never these resolved forms (R-3.4a).
canonicalize() {
  local p="$1" d b
  while [[ "$p" == */ && "$p" != "/" ]]; do p="${p%/}"; done
  if [[ -d "$p" ]]; then
    ( cd "$p" 2>/dev/null && pwd -P ) || printf '%s\n' "$p"
  else
    d="$(cd "$(dirname "$p")" 2>/dev/null && pwd -P)" || { printf '%s\n' "$p"; return 0; }
    b="$(basename "$p")"
    if [[ "$d" == "/" ]]; then printf '/%s\n' "$b"; else printf '%s/%s\n' "$d" "$b"; fi
  fi
  return 0
}

# True if two canonical paths overlap: equal, or either contained in the other.
overlaps() {
  local t="$1" v="$2"
  [[ "$t" == "$v" ]]   && return 0
  [[ "$t" == "$v"/* ]] && return 0   # removal target sits inside a vault
  [[ "$v" == "$t"/* ]] && return 0   # a vault sits inside a removal target
  return 1
}

# Abort BEFORE any deletion if any removal target overlaps a preserved vault.
vault_safety_gate() {
  local t v ct cv
  for t in "${PLAN[@]:-}"; do
    [[ -z "$t" ]] && continue
    ct="$(canonicalize "$t")"
    for v in "${PRESERVE[@]:-}"; do
      [[ -z "$v" ]] && continue
      cv="$(canonicalize "$v")"
      if overlaps "$ct" "$cv"; then
        die "ABORT: removal target '$t' overlaps preserved vault '$v'
   (resolved: '$ct' vs '$cv'). Nothing was deleted — fix the vault location first."
      fi
    done
  done
}

# ─── Stop running Squirrel ───────────────────────────────────────────────────
# Each external action is its own function so the orchestration order can be
# unit-tested (the gate against KeepAlive respawn) without a live app.
stop_app() {
  /usr/bin/osascript -e 'tell application "Squirrel" to quit' 2>/dev/null || true
  /usr/bin/pkill -f 'Squirrel.app/Contents/MacOS/squirrel' 2>/dev/null || true
  info "Quit Squirrel app"
}
retire_launchd_service() {
  local uid; uid="$(/usr/bin/id -u 2>/dev/null || true)"
  [[ -n "$uid" ]] && /bin/launchctl bootout "gui/$uid/org.squirrel.web-ui" 2>/dev/null || true
  info "Retired launchd service org.squirrel.web-ui"
}
kill_backend() {
  /usr/bin/pkill -f 'squirrel-backend' 2>/dev/null || true
  info "Stopped squirrel-backend"
}
port_3939_listener() {
  /usr/sbin/lsof -nP -iTCP:3939 -sTCP:LISTEN 2>/dev/null | /usr/bin/grep -q LISTEN
}

# Order is load-bearing: bootout the launchd service BEFORE killing the backend,
# or its KeepAlive immediately respawns the process we just killed (the
# "Backend offline" respawn loop). Then confirm :3939 is actually free.
stop_squirrel() {
  hdr "Stopping Squirrel"
  stop_app
  retire_launchd_service
  kill_backend
  /bin/sleep 1
  if port_3939_listener; then
    warn "Port 3939 still has a listener after stop — a process may be respawning it."
  else
    ok "Port 3939 is free"
  fi
}

# ─── Removal ─────────────────────────────────────────────────────────────────
FAILURES=()

# Remove one path literally. rm -rf on a symlink unlinks the link itself, never
# the target (R-3.4a) — and the PLAN paths carry no trailing slash, so a
# symlinked directory is never traversed. Failures are recorded, not fatal.
rm_path() {
  local p="$1"
  [[ -e "$p" || -L "$p" ]] || return 0
  if /bin/rm -rf "$p" 2>/dev/null; then
    ok "removed $p"
  else
    warn "failed to remove $p"
    FAILURES+=("$p")
  fi
}

# Drop the squirrel@* entry from Claude's plugin registry, written atomically
# (temp file + os.replace). Unparsable JSON is left untouched so other plugins'
# registration can never be corrupted (R-4.3).
deregister_plugin() {
  local f="$HOME/.claude/plugins/installed_plugins.json"
  [[ -f "$f" ]] || return 0
  local rc=0
  /usr/bin/python3 - "$f" <<'PY' || rc=$?
import json, os, sys, tempfile
f = sys.argv[1]
try:
    with open(f) as fh:
        data = json.load(fh)
except Exception:
    sys.exit(3)                       # unparsable -> leave untouched
plugins = data.get("plugins")
if not isinstance(plugins, dict):
    sys.exit(2)                       # nothing to do
removed = [k for k in list(plugins) if k.split("@", 1)[0] == "squirrel"]
for k in removed:
    del plugins[k]
if not removed:
    sys.exit(2)
d = os.path.dirname(f) or "."
fd, tmp = tempfile.mkstemp(dir=d, prefix=".ip.", suffix=".json")
try:
    with os.fdopen(fd, "w") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, f)                # atomic
except Exception:
    try: os.unlink(tmp)
    except OSError: pass
    sys.exit(4)
sys.exit(0)
PY
  case "$rc" in
    0) ok "deregistered Claude plugin (squirrel@squirrel)" ;;
    2) : ;;                           # no squirrel entry — nothing to do
    3) warn "installed_plugins.json is not valid JSON — left unchanged" ;;
    *) warn "could not update installed_plugins.json (rc=$rc) — left unchanged"
       FAILURES+=("installed_plugins.json") ;;
  esac
}

# Remove every user-scope ($HOME/...) footprint path in the plan, EXCEPT
# ~/.squirrel which is deleted last (it holds the config that named the vaults).
remove_user_scope() {
  hdr "Removing user files"
  local p
  for p in "${PLAN[@]:-}"; do
    case "$p" in
      "$SQUIRREL_HOME") continue ;;   # handled last
      "$HOME"/*) rm_path "$p" ;;
    esac
  done
}

# True when the current user can remove $1 without sudo — i.e. its parent dir is
# writable (entry removal needs parent write, not file ownership). Lets a
# manual-install /Applications/Squirrel.app (user-owned) be removed prompt-free
# while root-owned /usr/local/* falls through to the sudo batch.
user_can_remove() {
  local parent; parent="$(dirname "$1")"
  [[ -w "$parent" ]]
}

# Single sudo invocation for all root-owned targets (seam: tests override this).
sudo_rm_batch() {
  /usr/bin/sudo /bin/rm -rf "$@"
}

# Remove non-$HOME footprint paths (/Applications, /usr/local/...). Anything the
# user can already delete is removed directly; only genuinely root-owned targets
# are batched into ONE sudo call — and sudo is never invoked when that batch is
# empty (R-4.4).
remove_root_scope() {
  local p sudo_targets=()
  for p in "${PLAN[@]:-}"; do
    case "$p" in "$HOME"/*) continue ;; esac
    [[ -e "$p" || -L "$p" ]] || continue
    if user_can_remove "$p"; then
      rm_path "$p"
    else
      sudo_targets+=("$p")
    fi
  done
  [[ ${#sudo_targets[@]} -eq 0 ]] && return 0

  hdr "Removing system files (admin password required)"
  local t
  for t in "${sudo_targets[@]}"; do printf '  %s- %s%s\n' "$C_RED" "$t" "$C_RESET"; done
  if sudo_rm_batch "${sudo_targets[@]}" 2>/dev/null; then
    for t in "${sudo_targets[@]}"; do ok "removed $t"; done
  else
    for t in "${sudo_targets[@]}"; do
      if [[ -e "$t" || -L "$t" ]]; then warn "failed to remove $t"; FAILURES+=("$t"); else ok "removed $t"; fi
    done
  fi
}

perform_removal() {
  stop_squirrel
  deregister_plugin
  remove_user_scope
  remove_root_scope
  rm_path "$SQUIRREL_HOME"            # R-4.5: ~/.squirrel removed last
}

# ─── Main ────────────────────────────────────────────────────────────────────
main() {
  load_preserve
  build_plan
  print_plan
  vault_safety_gate          # abort before any deletion if a target overlaps a vault

  if [[ $DRY_RUN -eq 1 ]]; then
    info "Dry run — nothing was changed."
    exit 0
  fi
  [[ ${#PLAN[@]} -eq 0 ]] && exit 0

  confirm
  perform_removal

  # R-4.6: report failures and exit non-zero if any removal failed.
  if [[ ${#FAILURES[@]} -gt 0 ]]; then
    warn "${#FAILURES[@]} item(s) could not be removed:"
    for p in "${FAILURES[@]}"; do printf '    %s\n' "$p"; done
    exit 1
  fi
  ok "Squirrel removed."
}

# Run main only when executed directly; sourcing (e.g. from tests) exposes the
# functions without side effects.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main
fi
