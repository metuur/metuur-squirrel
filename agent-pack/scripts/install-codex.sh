#!/usr/bin/env bash
#
# install-codex.sh — full-stack install of Squirrel for OpenAI Codex CLI.
#
# Installs EVERY component:
#   • Canonical files (skills, commands, hooks, lib, templates)
#       → ~/.claude/plugins/squirrel/  (where slash commands' find fallback looks
#         for lib/*.py — required even on Codex)
#   • Codex integration:
#       - Skills      → ~/.codex/skills/<skill>/
#       - Commands    → ~/.codex/commands/sq-*.md
#       - AGENTS.md   → patched with a "Context Bridge" block
#   • Standalone `squirrel` CLI symlinked into ~/.local/bin
#   • Config seed at ~/.squirrel/config.toml (from template if missing)
#   • macOS reminder daemon via launchd (on macOS; opt-in prompt)
#
# Usage:
#   ./scripts/install-codex.sh              # full install
#   ./scripts/install-codex.sh --link       # symlink instead of copy
#   ./scripts/install-codex.sh --dry-run    # preview without writing
#   ./scripts/install-codex.sh --yes        # non-interactive
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

hdr "Installing Squirrel — Codex CLI (full stack)"
require_python
require_squirrel_cli "$ROOT"

install_canonical          "$ROOT"
install_agent_integration  "$ROOT" "codex"
install_post_steps         "$ROOT"

hdr "All done"
say ""
say "What was installed:"
say "  ✓ Canonical files (skills, commands, hooks, lib, templates)"
say "      → ~/.claude/plugins/squirrel/   (required for lib/*.py discovery)"
say "  ✓ Codex skills    → ~/.codex/skills/"
say "  ✓ Codex commands  → ~/.codex/commands/"
say "  ✓ Codex manifest  → ~/.codex/AGENTS.md  (patched)"
(( SKIP_CLI ))       || say "  ✓ CLI binary on PATH → $CLI_PREFIX/squirrel"
(( SKIP_CONFIG ))    || say "  ✓ Config seed       → ~/.squirrel/config.toml"
if [[ "$(uname)" == "Darwin" ]] && (( ! SKIP_REMINDERS )); then
  say "  ✓ macOS reminder daemon (if you accepted the prompt)"
fi
say ""
say "Next steps:"
say "  1. Start a fresh Codex session:"
say "       codex"
say "  2. Edit your vault path:"
say "       \$EDITOR ~/.squirrel/config.toml"
say "  3. Try it out:"
say "       /sq-where-am-i"
say "       /sq-status"
