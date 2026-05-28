---
description: Generate an HTML dashboard from vault data and open it in the browser.
allowed-tools: [Bash, Read]
---

# /sq-dashboard

Generates a single-file HTML dashboard from vault status + deadlines and opens it in the browser.

Optional arguments:
- `--vault NAME` — operate on the named vault (default if omitted)

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

SCRIPT=""
for candidate in \
    "${HOME}/.claude/plugins/squirrel/lib/dashboard_generator.py" \
    "$(find "${HOME}/others" -name 'dashboard_generator.py' -path '*/squirrel/*' 2>/dev/null | head -1)"; do
  [ -f "$candidate" ] && SCRIPT="$candidate" && break
done
[ -z "$SCRIPT" ] && echo "❌ No se encontró dashboard_generator.py. Verificá la instalación del plugin." && exit 1
```

## Paso 2: Generar el dashboard

```bash
python3 "$SCRIPT" --vault "$VAULT_PATH" --open
```

Si el flag `--open` no funciona en el entorno actual, el archivo se habrá guardado en `~/.squirrel/dashboard.html`. Informar al usuario la ruta y que puede abrirlo con:

```bash
open ~/.squirrel/dashboard.html
```

## Paso 3: Confirmar

Reportar:
- Ruta del archivo generado
- Número de proyectos WIP encontrados
- Número de deadlines encontrados
- Confirmar si se abrió en el browser

## Notas

- El HTML se auto-refresca cada 5 minutos (meta refresh)
- Para regenerar sin abrir: `sq dashboard` o `python3 dashboard_generator.py --vault <path>`
- Si hay errores del vault (archivos malformados), se reportan pero no detienen la generación
