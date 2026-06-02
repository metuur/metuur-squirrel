---
description: Generate an HTML dashboard from vault data and open it in the browser.
allowed-tools: [Bash, Read]
---

# /sq-dashboard

Generates a single-file HTML dashboard from vault status + deadlines and opens it in the browser.

Optional arguments:
- `--vault NAME` — operate on the named vault (default if omitted)

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

SCRIPT=""
for candidate in \
    "${HOME}/.claude/plugins/squirrel/lib/dashboard_generator.py" \
    "$(find "${HOME}/others" -name 'dashboard_generator.py' -path '*/squirrel/*' 2>/dev/null | head -1)"; do
  [ -f "$candidate" ] && SCRIPT="$candidate" && break
done
[ -z "$SCRIPT" ] && echo "❌ dashboard_generator.py not found. Check the plugin installation." && exit 1
```

## Step 2: Generate the dashboard

```bash
python3 "$SCRIPT" --vault "$VAULT_PATH" --open
```

If the `--open` flag doesn't work in the current environment, the file will have been saved to `~/.squirrel/dashboard.html`. Tell the user the path and that they can open it with:

```bash
open ~/.squirrel/dashboard.html
```

## Step 3: Confirm

Report:
- Path of the generated file
- Number of WIP projects found
- Number of deadlines found
- Confirm whether it opened in the browser

## Notes

- The HTML auto-refreshes every 5 minutes (meta refresh)
- To regenerate without opening: `sq dashboard` or `python3 dashboard_generator.py --vault <path>`
- If there are vault errors (malformed files), they're reported but don't stop generation
