---
description: Global vault status. Runs status_aggregator.py and renders the resulting JSON. Accepts an optional `--vault NAME`.
allowed-tools: [Bash, Read]
---

# /sq-status

Global vault status. Generates nothing new — it only reports.

Optional arguments:
- `--vault NAME` — operate on a specific vault (default if omitted)

## Step 0: Parse `--vault NAME` and resolve VAULT_PATH (multi-vault)

```bash
# Parse --vault NAME from $ARGUMENTS (R-6.1, R-6.2)
VAULT_NAME=""
_skip_next=0
for arg in $ARGUMENTS; do
  if [ "$_skip_next" = "1" ]; then VAULT_NAME="$arg"; _skip_next=0; continue; fi
  if [ "$arg" = "--vault" ]; then _skip_next=1; fi
done

# Resolve VAULT_PATH via config_loader (multi-vault aware)
VAULT_PATH=$(python3 -c "
import sys, pathlib
for c in [pathlib.Path('~/.claude/plugins/squirrel/lib').expanduser()] + list(pathlib.Path.home().glob('others/*/squirrel/lib')) + list(pathlib.Path.home().glob('others/*/*/squirrel/lib')):
    if c.exists(): sys.path.insert(0, str(c)); break
from config_loader import get_vault, ConfigError
try:
    name = '$VAULT_NAME' if '$VAULT_NAME' else None
    print(get_vault(name=name).path)
except ConfigError as e:
    print(f'ERROR: {e}', file=sys.stderr); sys.exit(1)
" 2>&1)
[ $? -ne 0 ] && echo "❌ $VAULT_PATH" >&2 && exit 1
```

## Step 1: Locate the script

```bash

# script path: plugin standard locations
SCRIPT=""
for candidate in \
    "${HOME}/.claude/plugins/squirrel/lib/status_aggregator.py" \
    "$(dirname "$(find "${HOME}/.claude" -name 'status_aggregator.py' 2>/dev/null | head -1)")/status_aggregator.py" \
    "$(find "${HOME}/others" -name 'status_aggregator.py' -path '*/squirrel/*' 2>/dev/null | head -1)"; do
  [ -f "$candidate" ] && SCRIPT="$candidate" && break
done
[ -z "$SCRIPT" ] && echo "❌ status_aggregator.py not found. Check the plugin installation." && exit 1
```

## Step 2: Run the script

```bash
STATUS_JSON=$(python3 "$SCRIPT" --vault "$VAULT_PATH" --pretty 2>&1)
EXIT_CODE=$?
```

**If `EXIT_CODE != 0`**: show the contents of `STATUS_JSON` as an error message and stop. Don't make up data.

## Step 2.5: Scan critical and urgent deadlines (ATTN-007)

```bash
SCANNER=""
for candidate in \
    "${HOME}/.claude/plugins/squirrel/lib/deadline_scanner.py" \
    "$(dirname "$(find "${HOME}/.claude" -name 'deadline_scanner.py' 2>/dev/null | head -1)")/deadline_scanner.py" \
    "$(find "${HOME}/others" -name 'deadline_scanner.py' -path '*/squirrel/*' 2>/dev/null | head -1)"; do
  [ -f "$candidate" ] && SCANNER="$candidate" && break
done

if [ -n "$SCANNER" ]; then
  DEADLINES_JSON=$(python3 "$SCANNER" --vault "$VAULT_PATH" --level critical,urgent --pretty 2>&1)
fi
```

If `SCANNER` wasn't found, omit the deadlines section in the render (it's not a fatal error).

## Step 3: Render the JSON

With the returned JSON, render in this format:

```
📊 Vault Status — <scanned_at, date only>

🟢 WIP (<wip.count>/<wip.max> — max allowed: <wip.max>)
  1. <project.id> — <intents.percent_done>% — Deadline: <project.deadline> — Last: <active_intent>
  2. ...

🚧 PARKING LOT (<parking_lot.count> projects)
  • <id>

🏛️ AREAS
  • <id>

⚠️ ALERTS
  • <alert.project>: <alert.message>  [level: <alert.level>]

⏰ DEADLINES
  {FOR each item in by_urgency.critical where is_overdue=true (show as overdue):}
    🔴 [OVERDUE] <item.id> — <item.title> — <item.days_overdue>d ago
  {FOR each item in by_urgency.critical where is_overdue is falsy:}
    🔴 <item.id> — <item.title> — TODAY (<item.hours_left>h left)
  {FOR each item in by_urgency.urgent:}
    🟠 <item.id> — <item.title> — <item.days_left>d / <item.hours_left>h

  To see all levels: `/sq-deadlines`

🎯 RECOMMENDED FOCUS
  <recommended_focus.project> — <recommended_focus.reason>
  Next: <recommended_focus.next_action>
```

Omit empty sections (no items). Don't add data that isn't in the JSON.

The `⏰ DEADLINES` section is omitted entirely if:
- `SCANNER` was not found, OR
- `DEADLINES_JSON` contains an error, OR
- `by_urgency.critical` and `by_urgency.urgent` are both empty (count = 0)
