---
description: Muestra todos los deadlines del vault agrupados por urgencia. Uso: /sq-deadlines [--level critical,urgent,soon,upcoming,eventual,distant] [--vault NAME]
allowed-tools: [Bash]
---

# /sq-deadlines

Argumentos: `$ARGUMENTS`

Argumentos opcionales:
- `--level <levels>` — filtrar por urgencia (ej: `--level critical,urgent`)
- `--vault NAME` — operar sobre un vault específico (default si se omite)

Muestra deadlines del vault agrupados por nivel de urgencia ejecutando `deadline_scanner.py`.

## Paso 1: Parsear argumentos

De `$ARGUMENTS` extraer `--level <levels>` y `--vault NAME` si están presentes.
Si no se especifica `--level`, mostrar todos los niveles.
Si no se especifica `--vault`, usar el vault default.

## Paso 2: Resolver VAULT_PATH (multi-vault)

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

## Paso 3: Localizar el script

```bash
SCRIPT=""
for candidate in \
    "${HOME}/.claude/plugins/squirrel/lib/deadline_scanner.py" \
    "$(find "${HOME}/.claude" -name 'deadline_scanner.py' 2>/dev/null | head -1)" \
    "$(find "${HOME}/others" -name 'deadline_scanner.py' -path '*/squirrel/*' 2>/dev/null | head -1)"; do
  [ -f "$candidate" ] && SCRIPT="$candidate" && break
done
[ -z "$SCRIPT" ] && echo "❌ No se encontró deadline_scanner.py. Verificá la instalación del plugin." && exit 1
```

## Paso 4: Ejecutar el script

Sin filtro de nivel:
```bash
RESULT=$(python3 "$SCRIPT" --vault "$VAULT_PATH" --pretty 2>&1)
```

Con filtro (si `--level` fue especificado):
```bash
RESULT=$(python3 "$SCRIPT" --vault "$VAULT_PATH" --level "<levels>" --pretty 2>&1)
```

Si `EXIT_CODE != 0`, mostrar el error y detener.

## Paso 5: Renderizar el resultado

Con el JSON devuelto, renderizar cada nivel que tenga ítems:

```
📅 Deadlines — <scanned_at, solo fecha>

🔴 CRITICAL (<N>) — vencidos o < 4 horas
  • [OVERDUE] <project>/<intent> — vencido hace <days_overdue> día(s)   ← si is_overdue=true
  • <project>/<intent> — <hours_left>h restantes                        ← si inminente

🟠 URGENT (<N>) — hoy (≥4 h) o mañana
  • <project>/<intent> — <hours_left>h restantes / mañana

🟡 SOON (<N>) — 2-3 días
  • <project>/<intent> — <days_left> día(s)

🔵 UPCOMING (<N>) — 4-7 días
  • <project>/<intent> — <days_left> día(s)

🟢 EVENTUAL (<N>) — 8-30 días
  • <project>/<intent> — <days_left> día(s)

⚪ DISTANT (<N>) — más de 30 días
  • <project>/<intent> — <days_left> día(s)
```

Omitir completamente las secciones con cero ítems.
Si ningún nivel tiene ítems: mostrar "✅ No deadlines encontrados en el vault."
