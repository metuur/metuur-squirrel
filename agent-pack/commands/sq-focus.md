---
description: "Shows or changes the manual focus pick (today / today PM / this week). Usage: /sq-focus | /sq-focus today TAG/SLUG | /sq-focus pm TAG/SLUG | /sq-focus week TAG/SLUG | /sq-focus today --clear | /sq-focus pm --clear | /sq-focus week --clear | /sq-focus history [YYYY-MM-DD]"
allowed-tools: [Bash]
---

# /sq-focus

Arguments: `$ARGUMENTS`

Manages the user's **manual focus pick** for today, today PM, and this week, using `focus_cli.py` over the vault.

Valid invocation forms:

- `/sq-focus` — shows the current focus for today, today PM, and this week.
- `/sq-focus today TAG/SLUG` — sets today's focus.
- `/sq-focus pm TAG/SLUG` — sets today PM's focus.
- `/sq-focus week TAG/SLUG` — sets this week's focus.
- `/sq-focus today --clear` — clears today's focus.
- `/sq-focus pm --clear` — clears today PM's focus.
- `/sq-focus week --clear` — clears this week's focus.
- `/sq-focus history [YYYY-MM-DD]` — shows the focus pick history.

## Step 1: Parse arguments

```bash
set -- $ARGUMENTS
SUBCMD="${1:-}"
TARGET="${2:-}"
```

Cases:

- No `$1` → GET branch (Step 3).
- `$1` = `today`, `pm`, or `week` and `$2` = `--clear` → CLEAR branch (Step 5).
- `$1` = `today`, `pm`, or `week` and `$2` of the form `TAG/SLUG` → SET branch (Step 4).
- `$1` = `history`, optional `$2` of the form `YYYY-MM-DD` → HISTORY branch (Step 6).
- Any other combination → show usage and exit 1:
  ```
  Usage: /sq-focus | /sq-focus today TAG/SLUG | /sq-focus pm TAG/SLUG | /sq-focus week TAG/SLUG | /sq-focus today --clear | /sq-focus pm --clear | /sq-focus week --clear | /sq-focus history [YYYY-MM-DD]
  ```

## Step 2: Resolve VAULT_PATH and locate the script

```bash
# Resolve VAULT_PATH via config_loader (multi-vault aware)
VAULT_PATH=$(python3 -c "
import sys, pathlib
for c in [pathlib.Path('~/.claude/plugins/squirrel/lib').expanduser()] + list(pathlib.Path.home().glob('others/*/squirrel/lib')) + list(pathlib.Path.home().glob('others/*/*/squirrel/lib')):
    if c.exists(): sys.path.insert(0, str(c)); break
from config_loader import get_vault, ConfigError
try:
    print(get_vault(name=None).path)
except ConfigError as e:
    print(f'ERROR: {e}', file=sys.stderr); sys.exit(1)
" 2>&1)
[ $? -ne 0 ] && echo "❌ $VAULT_PATH" >&2 && exit 1

# Locate focus_cli.py
SCRIPT=""
for candidate in \
    "${HOME}/.claude/plugins/squirrel/lib/focus_cli.py" \
    "$(find "${HOME}/.claude" -name 'focus_cli.py' 2>/dev/null | head -1)" \
    "$(find "${HOME}/others" -name 'focus_cli.py' -path '*/squirrel/*' 2>/dev/null | head -1)"; do
  [ -f "$candidate" ] && SCRIPT="$candidate" && break
done
[ -z "$SCRIPT" ] && echo "❌ focus_cli.py not found." && exit 1
```

## Step 3: Bare invocation — GET

```bash
RAW=$(python3 "$SCRIPT" get --vault "$VAULT_PATH")
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "$RAW" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('error', 'Unknown error'))" 2>/dev/null || echo "$RAW"
  exit 1
fi

printf '%s' "$RAW" | python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
def fmt(slot, label):
    pick = data.get(slot)
    if not pick:
        return f'{label}: (none)'
    pt = pick.get('project_title') or pick.get('project_slug') or '?'
    it = pick.get('intent_title') or pick.get('intent_slug') or '?'
    return f'{label}: {pt} / {it}'
print(fmt('today', 'Today'))
print(fmt('today_pm', 'Today PM'))
print(fmt('week', 'This week'))
"
exit 0
```

Expected output (exactly three lines):

```
Today: {project} / {intent}
Today PM: {project} / {intent}
This week: {project} / {intent}
```

Each line shows `(none)` when the slot is not set.

## Step 4: SET

When `$SUBCMD` is `today`, `pm`, or `week` and `$TARGET` has the form `TAG/SLUG`:

```bash
case "$SUBCMD" in
  today) SLOT="today" ;;
  pm)    SLOT="today_pm" ;;
  week)  SLOT="week" ;;
  *)
    echo "Usage: /sq-focus | /sq-focus today TAG/SLUG | /sq-focus pm TAG/SLUG | /sq-focus week TAG/SLUG | /sq-focus today --clear | /sq-focus pm --clear | /sq-focus week --clear | /sq-focus history [YYYY-MM-DD]"
    exit 1 ;;
esac

if ! printf '%s' "$TARGET" | grep -q '/'; then
  echo "Usage: /sq-focus | /sq-focus today TAG/SLUG | /sq-focus pm TAG/SLUG | /sq-focus week TAG/SLUG | /sq-focus today --clear | /sq-focus pm --clear | /sq-focus week --clear | /sq-focus history [YYYY-MM-DD]"
  exit 1
fi
TAG="${TARGET%%/*}"
SLUG="${TARGET#*/}"
if [ -z "$TAG" ] || [ -z "$SLUG" ] || [ "$TAG" = "$TARGET" ]; then
  echo "Usage: /sq-focus | /sq-focus today TAG/SLUG | /sq-focus pm TAG/SLUG | /sq-focus week TAG/SLUG | /sq-focus today --clear | /sq-focus pm --clear | /sq-focus week --clear | /sq-focus history [YYYY-MM-DD]"
  exit 1
fi

RAW=$(python3 "$SCRIPT" set --vault "$VAULT_PATH" --slot "$SLOT" --project "$TAG" --intent "$SLUG")
RC=$?
if [ "$RC" -ne 0 ]; then
  # Parse error JSON — show "No such intent" when intent_not_found
  MSG=$(printf '%s' "$RAW" | python3 -c "
import json, sys
try:
    d = json.loads(sys.stdin.read())
    err = d.get('error', '')
    slug = d.get('slug', '$TAG/$SLUG')
    if 'intent' in err:
        print(f'No such intent: {slug}')
    else:
        print(d.get('message', err) or err)
except Exception:
    print(sys.stdin.read())
" 2>/dev/null || printf '%s' "$RAW")
  echo "$MSG"
  exit 1
fi

case "$SLOT" in
  today)    echo "Today's focus set: $TAG/$SLUG" ;;
  today_pm) echo "Today PM's focus set: $TAG/$SLUG" ;;
  week)     echo "This week's focus set: $TAG/$SLUG" ;;
esac
exit 0
```

## Step 5: CLEAR

When `$SUBCMD` is `today`, `pm`, or `week` and `$TARGET` is `--clear`:

```bash
case "$SUBCMD" in
  today) SLOT="today" ;;
  pm)    SLOT="today_pm" ;;
  week)  SLOT="week" ;;
esac

RAW=$(python3 "$SCRIPT" clear --vault "$VAULT_PATH" --slot "$SLOT")
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "$RAW" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('error', 'Unknown error'))" 2>/dev/null || echo "$RAW"
  exit 1
fi

case "$SLOT" in
  today)    echo "Today's focus cleared." ;;
  today_pm) echo "Today PM's focus cleared." ;;
  week)     echo "This week's focus cleared." ;;
esac
exit 0
```

## Step 6: HISTORY

When `$SUBCMD` is `history`, with optional `$TARGET` (`YYYY-MM-DD`):

```bash
if [ -n "$TARGET" ]; then
  RAW=$(python3 "$SCRIPT" history --vault "$VAULT_PATH" --date "$TARGET")
else
  RAW=$(python3 "$SCRIPT" history --vault "$VAULT_PATH")
fi
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "$RAW" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('error', 'Unknown error'))" 2>/dev/null || echo "$RAW"
  exit 1
fi

printf '%s' "$RAW" | python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
entries = data if isinstance(data, list) else data.get('entries', [])
if not entries:
    print('No history found.')
    sys.exit(0)
for e in entries:
    date = e.get('date', '?')
    picks = e.get('picks', {})
    sessions = e.get('sessions', [])
    print(f'--- {date} ---')
    for slot, pick in picks.items():
        if pick:
            pt = pick.get('project_title') or pick.get('project_slug') or '?'
            it = pick.get('intent_title') or pick.get('intent_slug') or '?'
            print(f'  {slot}: {pt} / {it}')
    for s in sessions:
        start = s.get('start', '?')
        end   = s.get('end', '?')
        proj  = s.get('project', '?')
        print(f'  session: {proj}  {start} → {end}')
"
exit 0
```

## Notes

- **intent_not_found (R-1.9):** when `focus_cli.py set` exits with code 1 and the JSON contains an intent-related error, it prints `No such intent: TAG/SLUG` and exits with 1.
- **No HTTP:** all communication goes through `focus_cli.py`, which operates directly on the vault — there are no network calls.
- **No jq:** JSON responses are parsed with `python3 -c` (stdlib).
- **pm slot:** `$1 = pm` maps to `--slot today_pm` in `focus_cli.py`.
- **history:** shows picks and sessions per day in a simple table format.
