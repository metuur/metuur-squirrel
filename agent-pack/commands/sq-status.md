---
description: Estado global del vault. Ejecuta status_aggregator.py y renderiza el JSON resultante. Acepta `--vault NAME` opcional.
allowed-tools: [Bash, Read]
---

# /sq-status

Estado global del vault. No genera nada nuevo — solo reporta.

Argumentos opcionales:
- `--vault NAME` — operar sobre un vault específico (default si se omite)

## Paso 0: Parsear `--vault NAME` y resolver VAULT_PATH (multi-vault)

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

## Paso 1: Ubicar el script

```bash

# script path: plugin standard locations
SCRIPT=""
for candidate in \
    "${HOME}/.claude/plugins/squirrel/lib/status_aggregator.py" \
    "$(dirname "$(find "${HOME}/.claude" -name 'status_aggregator.py' 2>/dev/null | head -1)")/status_aggregator.py" \
    "$(find "${HOME}/others" -name 'status_aggregator.py' -path '*/squirrel/*' 2>/dev/null | head -1)"; do
  [ -f "$candidate" ] && SCRIPT="$candidate" && break
done
[ -z "$SCRIPT" ] && echo "❌ No se encontró status_aggregator.py. Verificá la instalación del plugin." && exit 1
```

## Paso 2: Ejecutar el script

```bash
STATUS_JSON=$(python3 "$SCRIPT" --vault "$VAULT_PATH" --pretty 2>&1)
EXIT_CODE=$?
```

**Si `EXIT_CODE != 0`**: mostrar el contenido de `STATUS_JSON` como mensaje de error y detener. No inventar datos.

## Paso 2.5: Escanear deadlines críticos y urgentes (ATTN-007)

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

Si `SCANNER` no se encontró, omitir la sección de deadlines en el render (no es un error fatal).

## Paso 3: Renderizar el JSON

Con el JSON devuelto, renderizar en este formato:

```
📊 Vault Status — <scanned_at, solo fecha>

🟢 WIP (<wip.count>/<wip.max> — máximo permitido: <wip.max>)
  1. <project.id> — <intents.percent_done>% — Deadline: <project.deadline> — Last: <active_intent>
  2. ...

🚧 PARKING LOT (<parking_lot.count> proyectos)
  • <id>

🏛️ ÁREAS
  • <id>

⚠️ ALERTAS
  • <alert.project>: <alert.message>  [nivel: <alert.level>]

⏰ DEADLINES
  {FOR each item in by_urgency.critical where is_overdue=true (mostrar como overdue):}
    🔴 [OVERDUE] <item.id> — <item.title> — hace <item.days_overdue>d
  {FOR each item in by_urgency.critical where is_overdue is falsy:}
    🔴 <item.id> — <item.title> — HOY (<item.hours_left>h restantes)
  {FOR each item in by_urgency.urgent:}
    🟠 <item.id> — <item.title> — <item.days_left>d / <item.hours_left>h

  Para ver todos los niveles: `/sq-deadlines`

🎯 FOCO RECOMENDADO
  <recommended_focus.project> — <recommended_focus.reason>
  Next: <recommended_focus.next_action>
```

Omitir secciones vacías (sin items). No agregar datos que no estén en el JSON.

La sección `⏰ DEADLINES` se omite completamente si:
- `SCANNER` no fue encontrado, O
- `DEADLINES_JSON` contiene un error, O
- `by_urgency.critical` y `by_urgency.urgent` están ambos vacíos (count = 0)
