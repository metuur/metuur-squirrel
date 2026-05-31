---
description: "Muestra o cambia el manual focus pick (hoy / hoy PM / esta semana). Uso: /sq-focus | /sq-focus today TAG/SLUG | /sq-focus pm TAG/SLUG | /sq-focus week TAG/SLUG | /sq-focus today --clear | /sq-focus pm --clear | /sq-focus week --clear | /sq-focus history [YYYY-MM-DD]"
allowed-tools: [Bash]
---

# /sq-focus

Argumentos: `$ARGUMENTS`

Gestiona el **manual focus pick** del usuario para hoy, hoy PM y esta semana, usando `focus_cli.py` sobre el vault.

Formas válidas de invocación:

- `/sq-focus` — muestra el foco actual de hoy, hoy PM y esta semana.
- `/sq-focus today TAG/SLUG` — fija el foco de hoy.
- `/sq-focus pm TAG/SLUG` — fija el foco de hoy PM.
- `/sq-focus week TAG/SLUG` — fija el foco de esta semana.
- `/sq-focus today --clear` — limpia el foco de hoy.
- `/sq-focus pm --clear` — limpia el foco de hoy PM.
- `/sq-focus week --clear` — limpia el foco de esta semana.
- `/sq-focus history [YYYY-MM-DD]` — muestra el historial de focus picks.

## Paso 1: Parsear argumentos

```bash
set -- $ARGUMENTS
SUBCMD="${1:-}"
TARGET="${2:-}"
```

Casos:

- Sin `$1` → branch GET (Paso 3).
- `$1` = `today`, `pm`, o `week` y `$2` = `--clear` → branch CLEAR (Paso 5).
- `$1` = `today`, `pm`, o `week` y `$2` con forma `TAG/SLUG` → branch SET (Paso 4).
- `$1` = `history`, `$2` opcional con forma `YYYY-MM-DD` → branch HISTORY (Paso 6).
- Cualquier otra combinación → mostrar uso y exit 1:
  ```
  Usage: /sq-focus | /sq-focus today TAG/SLUG | /sq-focus pm TAG/SLUG | /sq-focus week TAG/SLUG | /sq-focus today --clear | /sq-focus pm --clear | /sq-focus week --clear | /sq-focus history [YYYY-MM-DD]
  ```

## Paso 2: Resolver VAULT_PATH y localizar script

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

# Localizar focus_cli.py
SCRIPT=""
for candidate in \
    "${HOME}/.claude/plugins/squirrel/lib/focus_cli.py" \
    "$(find "${HOME}/.claude" -name 'focus_cli.py' 2>/dev/null | head -1)" \
    "$(find "${HOME}/others" -name 'focus_cli.py' -path '*/squirrel/*' 2>/dev/null | head -1)"; do
  [ -f "$candidate" ] && SCRIPT="$candidate" && break
done
[ -z "$SCRIPT" ] && echo "❌ No se encontró focus_cli.py." && exit 1
```

## Paso 3: Bare invocation — GET

```bash
RAW=$(python3 "$SCRIPT" get --vault "$VAULT_PATH")
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "$RAW" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('error', 'Error desconocido'))" 2>/dev/null || echo "$RAW"
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

Salida esperada (exactamente tres líneas):

```
Today: {project} / {intent}
Today PM: {project} / {intent}
This week: {project} / {intent}
```

Cada línea muestra `(none)` cuando el slot no está fijado.

## Paso 4: SET

Cuando `$SUBCMD` es `today`, `pm`, o `week` y `$TARGET` tiene forma `TAG/SLUG`:

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

## Paso 5: CLEAR

Cuando `$SUBCMD` es `today`, `pm`, o `week` y `$TARGET` es `--clear`:

```bash
case "$SUBCMD" in
  today) SLOT="today" ;;
  pm)    SLOT="today_pm" ;;
  week)  SLOT="week" ;;
esac

RAW=$(python3 "$SCRIPT" clear --vault "$VAULT_PATH" --slot "$SLOT")
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "$RAW" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('error', 'Error desconocido'))" 2>/dev/null || echo "$RAW"
  exit 1
fi

case "$SLOT" in
  today)    echo "Today's focus cleared." ;;
  today_pm) echo "Today PM's focus cleared." ;;
  week)     echo "This week's focus cleared." ;;
esac
exit 0
```

## Paso 6: HISTORY

Cuando `$SUBCMD` es `history`, con `$TARGET` opcional (`YYYY-MM-DD`):

```bash
if [ -n "$TARGET" ]; then
  RAW=$(python3 "$SCRIPT" history --vault "$VAULT_PATH" --date "$TARGET")
else
  RAW=$(python3 "$SCRIPT" history --vault "$VAULT_PATH")
fi
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "$RAW" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('error', 'Error desconocido'))" 2>/dev/null || echo "$RAW"
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

## Notas

- **intent_not_found (R-1.9):** cuando `focus_cli.py set` sale con código 1 y el JSON contiene un error relacionado con intent, se imprime `No such intent: TAG/SLUG` y se sale con 1.
- **Sin HTTP:** toda comunicación va por `focus_cli.py` que opera directamente sobre el vault — no hay llamadas de red.
- **Sin jq:** las respuestas JSON se parsean con `python3 -c` (stdlib).
- **pm slot:** `$1 = pm` mapea a `--slot today_pm` en `focus_cli.py`.
- **history:** muestra picks y sesiones por día en formato tabla simple.
