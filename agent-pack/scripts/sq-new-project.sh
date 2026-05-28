#!/usr/bin/env bash
# sq-new-project.sh — Runtime wrapper for the new-project skill.
# Locates the squirrel lib/ directory and runs new_project_writer.py,
# forwarding all arguments verbatim.
set -u

CANDIDATES=(
  "$HOME/.claude/plugins/squirrel/lib"
  "$HOME/others/ai-agents/adhd-context-bridge/lib"
)
while IFS= read -r d; do
  CANDIDATES+=("$d")
done < <(find "$HOME/others" -maxdepth 4 -type d -name squirrel -print 2>/dev/null \
           | sed 's|$|/lib|' | head -5)

LIB=""
for c in "${CANDIDATES[@]}"; do
  if [ -f "$c/new_project_writer.py" ]; then
    LIB="$c"
    break
  fi
done

if [ -z "$LIB" ]; then
  echo "❌ Could not find squirrel lib/ with new_project_writer.py" >&2
  exit 1
fi

exec python3 "$LIB/new_project_writer.py" "$@"
