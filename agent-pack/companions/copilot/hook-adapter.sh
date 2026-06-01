#!/usr/bin/env bash
# hook-adapter.sh — Copilot→Squirrel hook bridge (env-vars + CLI args delivery).
#
# Usage:
#   hook-adapter.sh <SquirrelEventName> <bash-body>
#
# Exports EVENT, PROJECT, TIMESTAMP (and USER_PROMPT for UserPromptSubmit)
# then runs <bash-body> via bash -c, matching the INT-007 contract that the
# inline bodies from agent-pack/hooks/hooks.json expect.
#
# R-7.8: If EVENT cannot be derived, exits 0 silently (logs to stderr).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_adapter-common.sh
source "$SCRIPT_DIR/_adapter-common.sh"

EVENT="${1:-}"
BODY="${2:-}"

if [[ -z "$EVENT" ]]; then
  printf 'squirrel hook-adapter: EVENT is empty — skipping body\n' >&2
  exit 0
fi

export EVENT
export PROJECT
PROJECT="$(resolve_project)"
export TIMESTAMP
TIMESTAMP="$(iso_timestamp)"

# USER_PROMPT is already exported by Copilot for userPromptSubmitted events
# when delivered via env-vars. Keep whatever Copilot already set; export empty
# string if missing so the body does not see an unbound variable.
export USER_PROMPT="${USER_PROMPT:-}"

if [[ -z "$BODY" ]]; then
  exit 0
fi

bash -c "$BODY"
