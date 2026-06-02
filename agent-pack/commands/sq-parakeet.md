---
description: Deadline reminder with tone calibrated to urgency. Shows critical/urgent items always (critical includes overdue via is_overdue flag); upcoming/eventual/distant only on direct invocation.
allowed-tools: [Bash, Read]
---

# /sq-parakeet

Scans the vault's deadlines and generates messages with a tone that matches the urgency level.

Optional arguments:
- `--vault NAME` — operate on a specific vault (default if omitted)

## Step 1: Resolve VAULT_PATH and script (multi-vault)

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

SCRIPT=$(find "${HOME}/.claude/plugins/squirrel/lib" "${HOME}/others" \
    -name 'deadline_scanner.py' -path '*/squirrel/*' 2>/dev/null | head -1)
[ -z "$SCRIPT" ] && echo "❌ deadline_scanner.py not found" && exit 1
```

## Step 2: Scan deadlines

```bash
DEADLINES_JSON=$(python3 "$SCRIPT" --vault "$VAULT_PATH" --pretty 2>&1)
```

## Step 3: Invoke the parakeet skill

Pass the JSON to the `squirrel-parakeet` skill (see `skills/parakeet/SKILL.md`).

The skill:
1. Evaluates the urgency levels
2. Generates messages with an appropriate tone (critical with is_overdue → non-judgmental, imminent critical → serious, upcoming → casual)
3. Suggests a concrete action if there are urgent/critical items

Direct invocation mode (`/sq-parakeet`): show all levels including `upcoming`, `eventual`, `distant`.
Embedded mode (within session-start, status): show only `critical`, `urgent`.
