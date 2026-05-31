#!/usr/bin/env bash
# sq-where-am-i.sh — Runtime wrapper for the where-am-i skill.
# Locates the squirrel lib/ directory and runs where_am_i_formatter.py.
# Optional first arg: vault name (omit for default vault).
set -u

VAULT_NAME="${1:-}"

# Candidate lib/ locations, in order of preference.
CANDIDATES=(
  "$HOME/.claude/plugins/squirrel/lib"
  "$HOME/others/ai-agents/adhd-context-bridge/lib"
)
# Also probe common dev layouts the user might have.
while IFS= read -r d; do
  CANDIDATES+=("$d")
done < <(find "$HOME/others" -maxdepth 4 -type d -name squirrel -print 2>/dev/null \
           | sed 's|$|/lib|' | head -5)

LIB=""
for c in "${CANDIDATES[@]}"; do
  if [ -f "$c/where_am_i_formatter.py" ]; then
    LIB="$c"
    break
  fi
done

if [ -z "$LIB" ]; then
  echo "❌ Could not find squirrel lib/ with where_am_i_formatter.py" >&2
  exit 1
fi

if [ -n "$VAULT_NAME" ]; then
  exec python3 "$LIB/where_am_i_formatter.py" --name "$VAULT_NAME"
else
  exec python3 "$LIB/where_am_i_formatter.py"
fi
