#!/usr/bin/env bash
#
# install-cursor.sh — full-stack install of Squirrel for Cursor (or VSCode with Cursor).
#
# Installs EVERY component:
#   • Canonical files (skills, commands, hooks, lib, templates)
#       → ~/.claude/plugins/squirrel/  (where the lib/*.py discovery looks —
#         required even on Cursor)
#   • Cursor integration:
#       - Skills (as rules) → ~/.cursor/rules/squirrel/<skill>/
#       - Rule pointer text printed at the end (paste into Settings → Rules for AI)
#   • Standalone `squirrel` CLI symlinked into ~/.local/bin
#   • Config seed at ~/.squirrel/config.toml (from template if missing)
#   • macOS reminder daemon via launchd (on macOS; opt-in prompt)
#
# Usage:
#   ./scripts/install-cursor.sh             # full install
#   ./scripts/install-cursor.sh --link      # symlink instead of copy
#   ./scripts/install-cursor.sh --dry-run   # preview without writing
#   ./scripts/install-cursor.sh --yes       # non-interactive
#
# Opt-out flags (skip individual steps):
#   --no-config      do not create ~/.squirrel/config.toml
#   --no-cli         do not symlink `squirrel` into ~/.local/bin
#   --no-reminders   do not install the macOS launchd daemon
#   --prefix=PATH    install CLI symlink here (default: ~/.local/bin)
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

hdr "Installing Squirrel — Cursor (full stack)"
require_python
require_squirrel_cli "$ROOT"

install_canonical          "$ROOT"
install_agent_integration  "$ROOT" "cursor"
install_post_steps         "$ROOT"

hdr "All done"
say ""
say "What was installed:"
say "  ✓ Canonical files (skills, commands, hooks, lib, templates)"
say "      → ~/.claude/plugins/squirrel/   (required for lib/*.py discovery)"
say "  ✓ Cursor rules    → ~/.cursor/rules/squirrel/"
(( SKIP_CLI ))       || say "  ✓ CLI binary on PATH → $CLI_PREFIX/squirrel"
(( SKIP_CONFIG ))    || say "  ✓ Config seed       → ~/.squirrel/config.toml"
if [[ "$(uname)" == "Darwin" ]] && (( ! SKIP_REMINDERS )); then
  say "  ✓ macOS reminder daemon (if you accepted the prompt)"
fi
say ""
say "Manual step (Cursor only):"
say "  Open Cursor → Settings → Rules for AI, paste this:"
say ""
say "      Use ~/.cursor/rules/squirrel/ for managing project context, shutdown"
say "      notes, and cross-environment transfers. See SKILL.md files in each"
say "      subdirectory."
say ""
say "  Then restart Cursor."
say ""
say "  Optional richer manifest at:"
say "      $ROOT/companions/cursor/squirrel.mdc"
say ""
say "Next steps:"
say "  1. Edit your vault path:"
say "       \$EDITOR ~/.squirrel/config.toml"
say "  2. Cursor has no slash commands — ask in plain English:"
say "       \"Where am I on WORK-X?\""
say "       \"Capture this idea: …\""
say "       \"End the session and write a shutdown note.\""
