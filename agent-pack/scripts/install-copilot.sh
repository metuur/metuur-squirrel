#!/usr/bin/env bash
#
# install-copilot.sh — full-stack install of Squirrel for GitHub Copilot.
#
# Installs EVERY component:
#   • Canonical files (skills, commands, hooks, lib, templates)
#       → ~/.claude/plugins/squirrel/  (where slash commands' find fallback looks
#         for lib/*.py — required even on Copilot)
#   • Copilot integration (user-level, default):
#       - Skill agents   → ~/.copilot/agents/squirrel-<name>.agent.md
#       - Prompt files   → ~/.copilot/prompts/sq-<cmd>.prompt.md
#       - Manifest       → ~/.copilot/copilot-instructions.md  (patched)
#       - Hooks          → ~/.copilot/hooks/squirrel.json
#   • With --workspace:
#       - Skill agents   → <repo-root>/.github/agents/
#       - Prompt files   → <repo-root>/.github/prompts/
#       - Manifest       → <repo-root>/.github/copilot-instructions.md
#       - Hooks          → <repo-root>/.github/hooks/squirrel.json
#   • Standalone `squirrel` CLI symlinked into ~/.local/bin
#   • Config seed at ~/.squirrel/config.toml (from template if missing)
#   • macOS reminder daemon via launchd (on macOS; opt-in prompt)
#
# Usage:
#   ./scripts/install-copilot.sh              # full install, user-level
#   ./scripts/install-copilot.sh --workspace  # install into .github/ of git repo
#   ./scripts/install-copilot.sh --link       # symlink instead of copy
#   ./scripts/install-copilot.sh --dry-run    # preview without writing
#   ./scripts/install-copilot.sh --yes        # non-interactive
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

hdr "Installing Squirrel — GitHub Copilot (full stack)"
require_python
require_squirrel_cli "$ROOT"

install_canonical          "$ROOT"
install_agent_integration  "$ROOT" "copilot"
install_post_steps         "$ROOT"

hdr "All done"
say ""
say "What was installed:"
say "  ✓ Canonical files (skills, commands, hooks, lib, templates)"
say "      → ~/.claude/plugins/squirrel/   (required for lib/*.py discovery)"
if (( ${WORKSPACE_INSTALL:-0} )); then
  say "  ✓ Copilot skill agents  → .github/agents/"
  say "  ✓ Copilot prompts       → .github/prompts/"
  say "  ✓ Copilot manifest      → .github/copilot-instructions.md  (patched)"
  say "  ✓ Copilot hooks         → .github/hooks/squirrel.json"
else
  say "  ✓ Copilot skill agents  → ~/.copilot/agents/"
  say "  ✓ Copilot prompts       → ~/.copilot/prompts/"
  say "  ✓ Copilot manifest      → ~/.copilot/copilot-instructions.md  (patched)"
  say "  ✓ Copilot hooks         → ~/.copilot/hooks/squirrel.json"
fi
(( SKIP_CLI ))       || say "  ✓ CLI binary on PATH → $CLI_PREFIX/squirrel"
(( SKIP_CONFIG ))    || say "  ✓ Config seed        → ~/.squirrel/config.toml"
if [[ "$(uname)" == "Darwin" ]] && (( ! SKIP_REMINDERS )); then
  say "  ✓ macOS reminder daemon (if you accepted the prompt)"
fi
say ""
say "Next steps:"
say "  1. Restart VS Code or reload the Copilot extension."
say "  2. Edit your vault path:"
say "       \$EDITOR ~/.squirrel/config.toml"
say "  3. Try it out in Copilot Chat:"
say "       /sq-where-am-i"
say "       /sq-status"
