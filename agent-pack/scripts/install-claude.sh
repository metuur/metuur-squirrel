#!/usr/bin/env bash
#
# install-claude.sh — full-stack install of Squirrel for Claude Code.
#
# Installs EVERY component:
#   • Plugin (skills, commands, hooks, lib, templates) → ~/.claude/plugins/squirrel/
#   • Standalone `squirrel` CLI symlinked into ~/.local/bin
#   • Config seed at ~/.squirrel/config.toml (from template if missing)
#   • macOS reminder daemon via launchd (on macOS; opt-in prompt)
#
# Usage:
#   ./scripts/install-claude.sh             # full install (interactive prompts)
#   ./scripts/install-claude.sh --link      # symlink files instead of copying
#   ./scripts/install-claude.sh --dry-run   # preview without writing
#   ./scripts/install-claude.sh --yes       # non-interactive (accept all prompts)
#
# Opt-out flags (skip individual steps):
#   --no-config      do not create ~/.squirrel/config.toml
#   --no-cli         do not symlink `squirrel` into ~/.local/bin
#   --no-reminders   do not install the macOS launchd daemon
#   --prefix=PATH    install CLI symlink here (default: ~/.local/bin)
#
# Restricted / no-plugin environments:
#   --no-plugin      install skills, commands, and hooks into Claude Code's
#   --manual         native locations instead of registering a plugin (for orgs
#                    that block plugin installs). Delegates to
#                    install-claude-manual.sh.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "$SCRIPT_DIR/_lib.sh"

print_help_and_exit() {
  awk 'NR>1 && /^#/ {sub(/^# ?/,""); print; next} NR>1 {exit}' "${BASH_SOURCE[0]}"
  exit 0
}

# Route to the manual (no-plugin) installer if requested, passing the other args
# through untouched.
NO_PLUGIN=0
PASS_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --no-plugin|--manual) NO_PLUGIN=1 ;;
    *)                    PASS_ARGS+=("$arg") ;;
  esac
done
if (( NO_PLUGIN )); then
  exec "$SCRIPT_DIR/install-claude-manual.sh" "${PASS_ARGS[@]+"${PASS_ARGS[@]}"}"
fi

ROOT="$(project_root "${BASH_SOURCE[0]}")"
parse_common_args "$@"
[[ ${#LEFTOVER_ARGS[@]} -eq 0 ]] || die "Unknown argument(s): ${LEFTOVER_ARGS[*]} (try --help)"

hdr "Installing Squirrel — Claude Code (full stack)"
require_python
require_squirrel_cli "$ROOT"

# Step 1: canonical install (puts everything at ~/.claude/plugins/squirrel/)
install_canonical "$ROOT"

# Step 2: agent-specific integration (no-op for claude — canonical IS the claude install)
install_agent_integration "$ROOT" "claude"

# Steps 3, 4, 5: CLI on PATH, config seed, macOS daemon
install_post_steps "$ROOT"

hdr "All done"
say ""
say "What was installed:"
say "  ✓ Plugin (skills, commands, hooks, lib, templates) → ~/.claude/plugins/squirrel/"
(( SKIP_CLI ))       || say "  ✓ CLI binary on PATH → $CLI_PREFIX/squirrel"
(( SKIP_CONFIG ))    || say "  ✓ Config seed       → ~/.squirrel/config.toml"
if [[ "$(uname)" == "Darwin" ]] && (( ! SKIP_REMINDERS )); then
  say "  ✓ macOS reminder daemon (if you accepted the prompt)"
fi
say ""
say "Next steps:"
say "  1. Close ALL Claude Code windows, then reopen."
say "  2. Verify:"
say "       /plugin list           # 'squirrel v0.7.0' should appear"
say "  3. Configure your vault:"
say "       /sq-init               # interactive setup wizard"
say "  4. Try it out:"
say "       /sq-where-am-i         # see your vault status"
