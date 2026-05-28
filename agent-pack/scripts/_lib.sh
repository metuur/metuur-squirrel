#!/usr/bin/env bash
# Shared helpers for install-*.sh scripts.
# Source this from another script; do not execute directly.

# ─── Colors (degrade to plain text if not a TTY) ─────────────────────────────
if [[ -t 1 ]]; then
  C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'
  C_BLUE=$'\033[34m'; C_BOLD=$'\033[1m'; C_RESET=$'\033[0m'
else
  C_RED=''; C_GREEN=''; C_YELLOW=''; C_BLUE=''; C_BOLD=''; C_RESET=''
fi

say()  { printf '%s\n' "$*"; }
info() { printf '%s%s%s\n' "$C_BLUE"   "ℹ  $*" "$C_RESET"; }
ok()   { printf '%s%s%s\n' "$C_GREEN"  "✅ $*" "$C_RESET"; }
warn() { printf '%s%s%s\n' "$C_YELLOW" "⚠  $*" "$C_RESET"; }
die()  { printf '%s%s%s\n' "$C_RED"    "❌ $*" "$C_RESET" >&2; exit 1; }
hdr()  { printf '\n%s%s%s\n' "$C_BOLD" "=== $* ===" "$C_RESET"; }
step() { printf '\n%s── %s ──%s\n' "$C_BOLD" "$*" "$C_RESET"; }

# ─── Global flag state (filled by parse_common_args) ─────────────────────────
DRY_RUN=0
USE_LINK=0
SKIP_CONFIG=0
SKIP_CLI=0
SKIP_REMINDERS=0
ASSUME_YES=0
CLI_PREFIX="$HOME/.local/bin"
EXTRA_ARGS=()           # flags to pass through to `squirrel install`
LEFTOVER_ARGS=()        # anything else the calling script wants to handle

# ─── Path helpers ────────────────────────────────────────────────────────────

# Resolve the project root from a script that sources this file.
project_root() {
  local script_path="$1"
  local script_dir
  script_dir="$(cd "$(dirname "$script_path")" && pwd)"
  cd "$script_dir/.." && pwd
}

# ─── Preflight checks ────────────────────────────────────────────────────────

require_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    die "python3 not found on PATH. Install Python 3.9+ from https://python.org/downloads (or 'brew install python3' on macOS)."
  fi
  local ver
  ver="$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
  local major minor
  IFS='.' read -r major minor <<<"$ver"
  if (( major < 3 || ( major == 3 && minor < 9 ) )); then
    die "Python $ver is too old. Squirrel needs Python 3.9 or higher."
  fi
  ok "Python $ver detected"
}

require_squirrel_cli() {
  local root="$1"
  local cli="$root/squirrel"
  [[ -f "$cli" ]] || die "Cannot find $cli — are you running this from the project repo?"
  [[ -r "$cli" ]] || die "$cli exists but is not readable."
}

# ─── Argument parsing ────────────────────────────────────────────────────────
# Recognized flags:
#   --link              symlink instead of copy (passed through to python installer)
#   --dry-run           preview only, no writes
#   --no-config         skip seeding ~/.squirrel/config.toml from template
#   --no-cli            skip symlinking `squirrel` to $CLI_PREFIX
#   --no-reminders      skip the macOS notification daemon
#   --yes, -y           assume yes for all confirmation prompts
#   --prefix=PATH       where to place the CLI symlink (default: ~/.local/bin)
#   -h, --help          print help and exit (the calling script provides it)
# Unknown args go into LEFTOVER_ARGS for the calling script to handle.
parse_common_args() {
  EXTRA_ARGS=()
  LEFTOVER_ARGS=()
  for arg in "$@"; do
    case "$arg" in
      --link)         USE_LINK=1; EXTRA_ARGS+=(--link)    ;;
      --dry-run)      DRY_RUN=1;  EXTRA_ARGS+=(--dry-run) ;;
      --no-config)    SKIP_CONFIG=1    ;;
      --no-cli)       SKIP_CLI=1       ;;
      --no-reminders) SKIP_REMINDERS=1 ;;
      --yes|-y)       ASSUME_YES=1     ;;
      --prefix=*)     CLI_PREFIX="${arg#--prefix=}" ;;
      --prefix)       die "Use --prefix=PATH (with =, no space)" ;;
      -h|--help)      print_help_and_exit ;;
      *)              LEFTOVER_ARGS+=("$arg") ;;
    esac
  done
}

# ─── Step 1: canonical install (full repo → ~/.claude/plugins/squirrel/) ─────
# Every install does this. It's the location every slash command's `find`
# fallback searches for lib/*.py, so it must exist regardless of which
# agent the user actually runs.
install_canonical() {
  local root="$1"
  step "Installing canonical files → ~/.claude/plugins/squirrel/"
  info "Running: python3 squirrel install --agent claude ${EXTRA_ARGS[*]:-}"
  python3 "$root/squirrel" install --agent claude "${EXTRA_ARGS[@]}"
}

# ─── Step 2: agent-specific integration ──────────────────────────────────────
# claude: already done by install_canonical (no-op)
# codex/cursor: copy skills/commands into their dirs, patch AGENTS.md, etc.
install_agent_integration() {
  local root="$1"
  local agent="$2"
  case "$agent" in
    claude)
      # Already installed by install_canonical
      ;;
    codex|cursor)
      step "Installing $agent integration"
      info "Running: python3 squirrel install --agent $agent ${EXTRA_ARGS[*]:-}"
      python3 "$root/squirrel" install --agent "$agent" "${EXTRA_ARGS[@]}"
      ;;
    standalone)
      # Nothing extra
      ;;
    *)
      die "Unknown agent: $agent"
      ;;
  esac
}

# ─── Step 3: put `squirrel` on PATH ──────────────────────────────────────────
install_cli_to_path() {
  local root="$1"
  if (( SKIP_CLI )); then
    info "Skipping CLI install (--no-cli)"
    return 0
  fi
  step "Installing 'squirrel' CLI → $CLI_PREFIX/squirrel"
  local src="$root/squirrel"
  local dst="$CLI_PREFIX/squirrel"
  if (( DRY_RUN )); then
    info "[dry-run] would mkdir -p $CLI_PREFIX"
    info "[dry-run] would symlink $dst -> $src"
    return 0
  fi
  mkdir -p "$CLI_PREFIX"
  if [[ -e "$dst" || -L "$dst" ]]; then
    warn "$dst already exists — replacing."
    rm -f "$dst"
  fi
  ln -s "$src" "$dst"
  chmod +x "$src"
  ok "CLI symlinked: $dst -> $src"
  if ! echo ":$PATH:" | grep -q ":$CLI_PREFIX:"; then
    warn "$CLI_PREFIX is NOT on your PATH."
    say "  Add to your shell rc (~/.zshrc or ~/.bashrc):"
    say "      export PATH=\"$CLI_PREFIX:\$PATH\""
  fi
}

# ─── Step 4: seed ~/.squirrel/config.toml from the template ──────────────────
install_config() {
  local root="$1"
  if (( SKIP_CONFIG )); then
    info "Skipping config seed (--no-config)"
    return 0
  fi
  step "Seeding config → ~/.squirrel/config.toml"
  local cfg_dir="$HOME/.squirrel"
  local cfg="$cfg_dir/config.toml"
  local tmpl="$root/config/squirrel.toml.example"
  [[ -f "$tmpl" ]] || die "Config template not found: $tmpl"
  if (( DRY_RUN )); then
    info "[dry-run] would mkdir -p $cfg_dir"
    if [[ -f "$cfg" ]]; then
      info "[dry-run] config already exists — would preserve $cfg"
    else
      info "[dry-run] would copy $tmpl → $cfg"
    fi
    return 0
  fi
  mkdir -p "$cfg_dir"
  if [[ -f "$cfg" ]]; then
    ok "Config already exists — preserved: $cfg"
  else
    cp "$tmpl" "$cfg"
    ok "Config created: $cfg"
    warn "Edit $cfg and set vault_path before running any /sq-* command."
  fi
}

# ─── Step 5: macOS reminder daemon (launchd) ─────────────────────────────────
install_macos_daemon() {
  local root="$1"
  if (( SKIP_REMINDERS )); then
    info "Skipping macOS reminder daemon (--no-reminders)"
    return 0
  fi
  if [[ "$(uname)" != "Darwin" ]]; then
    info "Not macOS — skipping reminder daemon (only supported on macOS)."
    return 0
  fi
  step "macOS reminder daemon (launchd)"
  local installer="$root/companions/macos-reminders/install.sh"
  if [[ ! -f "$installer" ]]; then
    warn "Daemon installer not found at $installer — skipping."
    return 0
  fi
  # Confirm unless --yes
  if (( ! ASSUME_YES )); then
    if [[ ! -t 0 ]]; then
      info "Non-interactive shell — pass --yes to install the daemon. Skipping."
      return 0
    fi
    say ""
    say "The macOS reminder daemon polls your vault every 2 hours and sends"
    say "notifications about critical deadlines. It installs a LaunchAgent at"
    say "  ~/Library/LaunchAgents/org.squirrel.reminders.plist"
    say ""
    read -r -p "Install the reminder daemon now? [Y/n] " reply
    case "${reply,,}" in
      n|no) info "Skipped."; return 0 ;;
    esac
  fi
  if (( DRY_RUN )); then
    info "[dry-run] would run: bash $installer"
    return 0
  fi
  bash "$installer"
}

# ─── Convenience: do steps 3, 4, 5 in order (used by every script) ───────────
install_post_steps() {
  local root="$1"
  install_cli_to_path "$root"
  install_config      "$root"
  install_macos_daemon "$root"
}
