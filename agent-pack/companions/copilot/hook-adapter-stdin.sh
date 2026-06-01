#!/usr/bin/env bash
# hook-adapter-stdin.sh — Copilot→Squirrel hook bridge (JSON-on-stdin delivery).
#
# Usage:
#   echo '<json-payload>' | hook-adapter-stdin.sh <SquirrelEventName> <bash-body>
#
# If stdin is not a TTY, reads up to 4096 bytes from stdin (with a 1s timeout)
# and attempts to parse the JSON payload for USER_PROMPT and project hint.
# Falls back gracefully when stdin is empty, non-JSON, or a TTY.
#
# Then exports EVENT, PROJECT, TIMESTAMP, USER_PROMPT (INT-007 contract) and
# runs <bash-body> via bash -c.
#
# R-7.8: If EVENT cannot be derived, exits 0 silently (logs to stderr).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_adapter-common.sh
source "$SCRIPT_DIR/_adapter-common.sh"

EVENT="${1:-}"
BODY="${2:-}"

if [[ -z "$EVENT" ]]; then
  printf 'squirrel hook-adapter-stdin: EVENT is empty — skipping body\n' >&2
  exit 0
fi

export EVENT
export TIMESTAMP
TIMESTAMP="$(iso_timestamp)"

# Try to read JSON from stdin when it is not a terminal.
_STDIN_PAYLOAD=""
if [[ ! -t 0 ]]; then
  _STDIN_PAYLOAD="$(dd bs=4096 count=1 2>/dev/null < /dev/stdin || true)"
fi

# Parse the two fields we care about from the payload, if present.
_PARSED_PROMPT=""
_PARSED_PROJECT=""
if [[ -n "$_STDIN_PAYLOAD" ]]; then
  _PARSED_PROMPT="$(python3 - "$_STDIN_PAYLOAD" <<'PY' 2>/dev/null || true
import json, sys
try:
    d = json.loads(sys.argv[1])
    print(d.get("user_prompt") or d.get("userPrompt") or "")
except Exception:
    print("")
PY
)"
  _PARSED_PROJECT="$(python3 - "$_STDIN_PAYLOAD" <<'PY' 2>/dev/null || true
import json, sys
try:
    d = json.loads(sys.argv[1])
    print(d.get("project") or d.get("project_tag") or "")
except Exception:
    print("")
PY
)"
fi

export USER_PROMPT="${_PARSED_PROMPT:-${USER_PROMPT:-}}"

# PROJECT: prefer parsed payload, else read from state.json.
if [[ -n "$_PARSED_PROJECT" ]]; then
  export PROJECT="$_PARSED_PROJECT"
else
  export PROJECT
  PROJECT="$(resolve_project)"
fi

if [[ -z "$BODY" ]]; then
  exit 0
fi

bash -c "$BODY"
