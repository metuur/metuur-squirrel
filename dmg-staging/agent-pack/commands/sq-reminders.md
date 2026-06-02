---
description: Lista y gestiona reminders del vault. Uso: /sq-reminders | /sq-reminders snooze ID YYYY-MM-DD [--vault NAME]
allowed-tools: [Bash]
---

# /sq-reminders

Argumentos: `$ARGUMENTS`

## Paso 1: Parsear argumentos

De `$ARGUMENTS` extraer el subcomando (`snooze`), ID de nota, fecha, y `--vault NAME` si están presentes.

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

- Si `SUBCMD` está vacío → modo lista.
- Si `SUBCMD` es `snooze` → modo snooze; requiere `ID` y `DATE`.

## Paso 2: Resolver VAULT_PATH

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

## Paso 3: Localizar los scripts

```bash
SCANNER_SCRIPT=""
for candidate in \
    "${HOME}/.claude/plugins/squirrel/lib/reminder_scanner.py" \
    "$(find "${HOME}/.claude" -name 'reminder_scanner.py' 2>/dev/null | head -1)" \
    "$(find "${HOME}/others" -name 'reminder_scanner.py' -path '*/squirrel/*' 2>/dev/null | head -1)"; do
  [ -f "$candidate" ] && SCANNER_SCRIPT="$candidate" && break
done
[ -z "$SCANNER_SCRIPT" ] && echo "❌ No se encontró reminder_scanner.py. Verificá la instalación del plugin." && exit 1

WRITER_SCRIPT=""
for candidate in \
    "${HOME}/.claude/plugins/squirrel/lib/reminder_writer.py" \
    "$(find "${HOME}/.claude" -name 'reminder_writer.py' 2>/dev/null | head -1)" \
    "$(find "${HOME}/others" -name 'reminder_writer.py' -path '*/squirrel/*' 2>/dev/null | head -1)"; do
  [ -f "$candidate" ] && WRITER_SCRIPT="$candidate" && break
done
[ -z "$WRITER_SCRIPT" ] && echo "❌ No se encontró reminder_writer.py. Verificá la instalación del plugin." && exit 1
```

## Paso 4: Ejecutar

### Modo lista (SUBCMD vacío)

```bash
RESULT=$(python3 "$SCANNER_SCRIPT" --vault "$VAULT_PATH" 2>&1)
[ $? -ne 0 ] && echo "❌ Error ejecutando reminder_scanner: $RESULT" >&2 && exit 1
```

Parsear el JSON con Python stdlib y renderizar:

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

Salida esperada (ejemplo con ítems):

```
🔴 Active (2)
  1. [rem-2024-001] Revisar medicación — 2024-03-10
  2. [rem-2024-005] Llamar al médico — 2024-03-12

🔔 Approaching (1)
  1. [rem-2024-009] Renovar seguro — 2024-03-17
```

Estado vacío:

```
No reminders right now.
```

---

### Modo snooze (SUBCMD = "snooze")

Validar que `ID` y `DATE` estén presentes:

```bash
[ -z "$ID" ]   && echo "❌ Uso: /sq-reminders snooze ID YYYY-MM-DD" >&2 && exit 1
[ -z "$DATE" ] && echo "❌ Uso: /sq-reminders snooze ID YYYY-MM-DD" >&2 && exit 1
```

Ejecutar:

```bash
RESULT=$(python3 "$WRITER_SCRIPT" snooze --note-id "$ID" --until "$DATE" --vault "$VAULT_PATH" 2>&1)
EXIT_CODE=$?
```

Parsear respuesta JSON:

```bash
python3 -c "
import json, sys
try:
    data = json.loads('$RESULT')
except Exception:
    print('❌ Respuesta inesperada del writer:', '$RESULT')
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
    print('❌ Error desconocido:', data)
    sys.exit(1)
"
```
