---
description: Shows all vault deadlines grouped by urgency. Usage: /sq-deadlines [--level critical,urgent,soon,upcoming,eventual,distant] [--vault NAME]
allowed-tools: [Bash]
---

# /sq-deadlines

Arguments: `$ARGUMENTS`

Optional arguments:
- `--level <levels>` — filter by urgency (e.g. `--level critical,urgent`)
- `--vault NAME` — operate on a specific vault (default if omitted)

Shows vault deadlines grouped by urgency level by running `deadline_scanner.py`.

## Step 1: Parse arguments

From `$ARGUMENTS` extract `--level <levels>` and `--vault NAME` if present.
If `--level` is not specified, show all levels.
If `--vault` is not specified, use the default vault.

## Step 2: Resolve VAULT_PATH (multi-vault)

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

## Step 3: Locate the script

```bash
SCRIPT=""
for candidate in \
    "${HOME}/.claude/plugins/squirrel/lib/deadline_scanner.py" \
    "$(find "${HOME}/.claude" -name 'deadline_scanner.py' 2>/dev/null | head -1)" \
    "$(find "${HOME}/others" -name 'deadline_scanner.py' -path '*/squirrel/*' 2>/dev/null | head -1)"; do
  [ -f "$candidate" ] && SCRIPT="$candidate" && break
done
[ -z "$SCRIPT" ] && echo "❌ deadline_scanner.py not found. Check the plugin installation." && exit 1
```

## Step 4: Run the script

Without level filter:
```bash
RESULT=$(python3 "$SCRIPT" --vault "$VAULT_PATH" --pretty 2>&1)
```

With filter (if `--level` was specified):
```bash
RESULT=$(python3 "$SCRIPT" --vault "$VAULT_PATH" --level "<levels>" --pretty 2>&1)
```

If `EXIT_CODE != 0`, show the error and stop.

## Step 5: Render the result

With the returned JSON, render each level that has items:

```
📅 Deadlines — <scanned_at, date only>

🔴 CRITICAL (<N>) — overdue or < 4 hours
  • [OVERDUE] <project>/<intent> — overdue by <days_overdue> day(s)   ← if is_overdue=true
  • <project>/<intent> — <hours_left>h left                          ← if imminent

🟠 URGENT (<N>) — today (≥4 h) or tomorrow
  • <project>/<intent> — <hours_left>h left / tomorrow

🟡 SOON (<N>) — 2-3 days
  • <project>/<intent> — <days_left> day(s)

🔵 UPCOMING (<N>) — 4-7 days
  • <project>/<intent> — <days_left> day(s)

🟢 EVENTUAL (<N>) — 8-30 days
  • <project>/<intent> — <days_left> day(s)

⚪ DISTANT (<N>) — more than 30 days
  • <project>/<intent> — <days_left> day(s)
```

Omit sections with zero items entirely.
If no level has items: show "✅ No deadlines found in the vault."
