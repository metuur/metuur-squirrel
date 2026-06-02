---
description: Lists and manages vault reminders. Usage: /sq-reminders | /sq-reminders snooze ID YYYY-MM-DD [--vault NAME]
allowed-tools: [Bash]
---

# /sq-reminders

Arguments: `$ARGUMENTS`

## Step 1: Parse arguments

From `$ARGUMENTS` extract the subcommand (`snooze`), note ID, date, and `--vault NAME` if present.

```bash
SUBCMD=""
ID=""
DATE=""
VAULT_NAME=""
_pos=0
_skip_next=0
for arg in $ARGUMENTS; do
  if [ "$_skip_next" = "1" ]; then VAULT_NAME="$arg"; _skip_next=0; continue; fi
  if [ "$arg" = "--vault" ]; then _skip_next=1; continue; fi
  case $_pos in
    0) SUBCMD="$arg"; _pos=1 ;;
    1) ID="$arg";     _pos=2 ;;
    2) DATE="$arg";   _pos=3 ;;
  esac
done
```

- If `SUBCMD` is empty → list mode.
- If `SUBCMD` is `snooze` → snooze mode; requires `ID` and `DATE`.

## Step 2: Resolve VAULT_PATH

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

## Step 3: Locate the scripts

```bash
SCANNER_SCRIPT=""
for candidate in \
    "${HOME}/.claude/plugins/squirrel/lib/reminder_scanner.py" \
    "$(find "${HOME}/.claude" -name 'reminder_scanner.py' 2>/dev/null | head -1)" \
    "$(find "${HOME}/others" -name 'reminder_scanner.py' -path '*/squirrel/*' 2>/dev/null | head -1)"; do
  [ -f "$candidate" ] && SCANNER_SCRIPT="$candidate" && break
done
[ -z "$SCANNER_SCRIPT" ] && echo "❌ reminder_scanner.py not found. Check the plugin installation." && exit 1

WRITER_SCRIPT=""
for candidate in \
    "${HOME}/.claude/plugins/squirrel/lib/reminder_writer.py" \
    "$(find "${HOME}/.claude" -name 'reminder_writer.py' 2>/dev/null | head -1)" \
    "$(find "${HOME}/others" -name 'reminder_writer.py' -path '*/squirrel/*' 2>/dev/null | head -1)"; do
  [ -f "$candidate" ] && WRITER_SCRIPT="$candidate" && break
done
[ -z "$WRITER_SCRIPT" ] && echo "❌ reminder_writer.py not found. Check the plugin installation." && exit 1
```

## Step 4: Run

### List mode (SUBCMD empty)

```bash
RESULT=$(python3 "$SCANNER_SCRIPT" --vault "$VAULT_PATH" 2>&1)
[ $? -ne 0 ] && echo "❌ Error running reminder_scanner: $RESULT" >&2 && exit 1
```

Parse the JSON with Python stdlib and render:

```bash
python3 -c "
import json, sys
data = json.loads('''$RESULT''')
approaching = data.get('approaching', [])
active = data.get('active', [])

if not approaching and not active:
    print('No reminders right now.')
    sys.exit(0)

if active:
    print(f'🔴 Active ({len(active)})')
    for i, item in enumerate(active, 1):
        print(f'  {i}. [{item[\"id\"]}] {item[\"title\"]} — {item[\"reminder_date\"]}')

if approaching:
    if active:
        print()
    print(f'🔔 Approaching ({len(approaching)})')
    for i, item in enumerate(approaching, 1):
        print(f'  {i}. [{item[\"id\"]}] {item[\"title\"]} — {item[\"reminder_date\"]}')
"
```

Expected output (example with items):

```
🔴 Active (2)
  1. [rem-2024-001] Refill medication — 2024-03-10
  2. [rem-2024-005] Call the doctor — 2024-03-12

🔔 Approaching (1)
  1. [rem-2024-009] Renew insurance — 2024-03-17
```

Empty state:

```
No reminders right now.
```

---

### Snooze mode (SUBCMD = "snooze")

Validate that `ID` and `DATE` are present:

```bash
[ -z "$ID" ]   && echo "❌ Usage: /sq-reminders snooze ID YYYY-MM-DD" >&2 && exit 1
[ -z "$DATE" ] && echo "❌ Usage: /sq-reminders snooze ID YYYY-MM-DD" >&2 && exit 1
```

Run:

```bash
RESULT=$(python3 "$WRITER_SCRIPT" snooze --note-id "$ID" --until "$DATE" --vault "$VAULT_PATH" 2>&1)
EXIT_CODE=$?
```

Parse the JSON response:

```bash
python3 -c "
import json, sys
try:
    data = json.loads('$RESULT')
except Exception:
    print('❌ Unexpected response from the writer:', '$RESULT')
    sys.exit(1)
err = data.get('error')
if err == 'not_found':
    print(f'❌ Note not found: $ID')
    sys.exit(1)
elif err == 'invalid_date':
    print(f'❌ Invalid date: $DATE (expected YYYY-MM-DD)')
    sys.exit(1)
elif data.get('snoozed'):
    print(f'✅ Reminder snoozed: $ID until $DATE')
else:
    print('❌ Unknown error:', data)
    sys.exit(1)
"
```
