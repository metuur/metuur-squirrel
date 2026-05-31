#!/usr/bin/env bash
#
# install-standalone.sh — full-stack install of Squirrel for terminal-only use.
#
# Installs EVERY component (no AI agent integration):
#   • Canonical files (skills, commands, hooks, lib, templates)
#       → ~/.claude/plugins/squirrel/  (so lib/*.py is on the discovery path)
#   • Standalone `squirrel` CLI symlinked into ~/.local/bin   (PRIMARY for this mode)
#   • Config seed at ~/.squirrel/config.toml (from template if missing)
#   • macOS reminder daemon via launchd (on macOS; opt-in prompt)
#
# Usage:
#   ./scripts/install-standalone.sh                     # full install
#   ./scripts/install-standalone.sh --link              # symlink canonical files
#   ./scripts/install-standalone.sh --dry-run           # preview without writing
#   ./scripts/install-standalone.sh --yes               # non-interactive
#   ./scripts/install-standalone.sh --prefix=/usr/local/bin   # custom CLI location
#
# Opt-out flags (skip individual steps):
#   --no-config      do not create ~/.squirrel/config.toml
#   --no-cli         do not symlink `squirrel` into ~/.local/bin  (defeats the point)
#   --no-reminders   do not install the macOS launchd daemon
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "$SCRIPT_DIR/_lib.sh"

print_help_and_exit() {
  awk 'NR>1 && /^#/ {sub(/^# ?/,""); print; next} NR>1 {exit}' "${BASH_SOURCE[0]}"
  exit 0
}

ROOT="$(project_root "${BASH_SOURCE[0]}")"
parse_common_args "$@"
[[ ${#LEFTOVER_ARGS[@]} -eq 0 ]] || die "Unknown argument(s): ${LEFTOVER_ARGS[*]} (try --help)"

hdr "Installing Squirrel — Standalone CLI (full stack)"
require_python
require_squirrel_cli "$ROOT"

install_canonical          "$ROOT"
install_agent_integration  "$ROOT" "standalone"   # no-op
install_post_steps         "$ROOT"

hdr "All done"
say ""
say "What was installed:"
say "  ✓ Canonical files (skills, commands, hooks, lib, templates)"
say "      → ~/.claude/plugins/squirrel/"
(( SKIP_CLI ))       || say "  ✓ CLI binary on PATH → $CLI_PREFIX/squirrel"
(( SKIP_CONFIG ))    || say "  ✓ Config seed       → ~/.squirrel/config.toml"
if [[ "$(uname)" == "Darwin" ]] && (( ! SKIP_REMINDERS )); then
  say "  ✓ macOS reminder daemon (if you accepted the prompt)"
fi
say ""
say "Next steps:"
say "  1. Verify the CLI is on PATH:"
say "       squirrel --help"
say "  2. Edit your vault path:"
say "       \$EDITOR ~/.squirrel/config.toml"
say "  3. Try it out:"
say "       squirrel status"
say "       squirrel deadlines"
say "       squirrel chunk --hours 8"
