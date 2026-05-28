---
description: Deadline reminder with tone calibrated to urgency. Shows critical/urgent items always (critical includes overdue via is_overdue flag); upcoming/eventual/distant only on direct invocation.
allowed-tools: [Bash, Read]
---

# /sq-parakeet

Escanea deadlines del vault y genera mensajes con tono acorde al nivel de urgencia.

Argumentos opcionales:
- `--vault NAME` — operar sobre un vault específico (default si se omite)

## Paso 1: Resolver VAULT_PATH y script (multi-vault)

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
[ -z "$SCRIPT" ] && echo "❌ deadline_scanner.py no encontrado" && exit 1
```

## Paso 2: Escanear deadlines

```bash
DEADLINES_JSON=$(python3 "$SCRIPT" --vault "$VAULT_PATH" --pretty 2>&1)
```

## Paso 3: Invocar el skill parakeet

Pasarle el JSON al skill `squirrel-parakeet` (ver `skills/parakeet/SKILL.md`).

El skill:
1. Evalúa los niveles de urgencia
2. Genera mensajes con tono apropiado (critical con is_overdue → non-judgmental, critical inminente → serio, upcoming → casual)
3. Sugiere una acción concreta si hay items urgent/critical

Modo de invocación directa (`/sq-parakeet`): mostrar todos los niveles incluyendo `upcoming`, `eventual`, `distant`.
Modo embedded (dentro de session-start, status): mostrar solo `critical`, `urgent`.
