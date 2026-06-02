---
description: Configuración inicial del plugin. Crea ~/.squirrel/config.toml y estructura mínima del vault si no existe. Acepta `--add-vault` para añadir un vault adicional a una config existente.
allowed-tools: [Read, Write, Bash, AskUserQuestion]
---

# /sq-init

Configuración inicial de squirrel.

Argumentos opcionales:
- `--add-vault` — añade un vault adicional a una config existente en lugar de correr el setup inicial completo (R-6.4)

## Paso 0: Detectar `--add-vault` y rutear

```bash
ADD_VAULT=0
for arg in $ARGUMENTS; do
  if [ "$arg" = "--add-vault" ]; then ADD_VAULT=1; fi
done
```

Si `ADD_VAULT == 1`, saltar directamente al **Paso A — Add-vault subflow** al final de este archivo. La rama de setup inicial (Pasos 1–6) NO se ejecuta en ese caso.

Si `ADD_VAULT == 0`, continuar con el flujo de setup inicial estándar (Pasos 1–6).

---

Pasos (flujo de setup inicial, sólo cuando `--add-vault` NO está presente):
1. Localizar el directorio de instalación del plugin:
```bash
SQUIRREL_DIR=$(find "${HOME}/.claude/plugins" "${HOME}/others" \
    -maxdepth 4 -name "plugin.json" -path "*squirrel*" 2>/dev/null \
    | head -1 | xargs dirname 2>/dev/null | xargs dirname 2>/dev/null)
[ -z "$SQUIRREL_DIR" ] && echo "❌ No se encontró el directorio del plugin squirrel." && exit 1
```

1b. Preguntar al usuario:
   - `vault_path`: ruta absoluta al vault (default `~/vault-squirrel`)
   - `environment_name`: `personal` o `work` (u otro custom)
   - `default_email`: dirección de email para mailto: drafts
   - `active_projects`: lista de tags de proyectos WIP actuales

<!-- @spec INT-005 -->
2. Crear `~/.squirrel/config.toml` desde la plantilla si no existe:
```bash
mkdir -p ~/.squirrel
if [ ! -f ~/.squirrel/config.toml ]; then
    cp "$SQUIRREL_DIR/config/squirrel.toml.example" ~/.squirrel/config.toml
    echo "✅ config.toml creado desde plantilla."
else
    echo "ℹ️  config.toml ya existe — no se sobreescribió."
fi
```

2b. Referencia: estructura del config.toml generado:
```toml
vault_path = "~/vault-squirrel"
environment_name = "personal"
default_email = "user@example.com"

[projects]
active = ["TRABAJO-PROYECTO-A", "SIDEPROJECT-FOYER-FAMILY", "VISA-FAMILIA"]

[compliance]
strict = false
corporate_domains = []
allowed_inbound_tags = ["*"]
allowed_inbound_environments = ["personal", "work"]

[encryption]
enabled = false
gpg_recipient = ""

[capture]
default_folder = "99-Resources/Captures"
auto_link_project_page = true
```

3. Crear estructura mínima en el vault si no existe:
   - `<vault>/.squirrel/outgoing/`
   - `<vault>/.squirrel/applied/`
   - `<vault>/.squirrel/incoming/`
   - `<vault>/.squirrel/audit-logs/`   ← audit trail (VAULT-006)
   - `<vault>/.squirrel/switches.jsonl` ← empty file, switches ledger (VAULT-006)

4. Verificar que existan las carpetas PARA del vault (VAULT-001 + VAULT-006):
   - `01-Proyectos-Activos/`   ← PARA: Projects
   - `02-Areas/`               ← PARA: Areas
   - `03-Recursos/`            ← PARA: Resources
   - `04-Archivo/`             ← PARA: Archive

   También crear carpetas auxiliares si no existen:
   - `00-Dashboard/`
   - `02-Parking-Lot/`
   - `04-Daily/`
   - `99-Resources/`

   Si faltan, crear con stub README.

4b. Escribir una intent de muestra desde `templates/intent.md` (VAULT-006):
   - Destino: `<vault>/01-Proyectos-Activos/DEMO-INICIO/DEMO-INICIO-SETUP-001.md`
   - Rellenar `<TAG>` → `DEMO-INICIO-SETUP-001`, `<PROJECT>` → `DEMO-INICIO`, `<YYYY-MM-DD>` → fecha de hoy.
   - Crear también la página de proyecto `<vault>/01-Proyectos-Activos/DEMO-INICIO/DEMO-INICIO.md` con frontmatter mínimo:
     ```yaml
     ---
     id: DEMO-INICIO
     tipo: C
     estado: wip
     creado: <YYYY-MM-DD>
     tags: [proyecto, demo]
     ---
     # DEMO-INICIO
     Proyecto de demostración generado por /sq-init.
     ```
   - No sobreescribir si ya existen — avisar y saltar.

5. Ofrecer instalar los dashboards de Obsidian:
   - Preguntar: "¿Querés copiar los dashboards de Dataview a `vault/00-Dashboard/`? (s/n)"
   - Si sí: copiar `templates/dashboard/Dashboard.md` y `templates/dashboard/Dashboard-Kanban.md`
     a `<vault>/00-Dashboard/`. No sobreescribir si ya existen — avisar y saltar.
   - Si no: mencionar que pueden instalarse manualmente desde `templates/dashboard/`.
   - Tip: "En Obsidian podés fijar el panel del Dashboard para tenerlo siempre visible."

6. Confirmar setup y sugerir próximo paso: `/sq-where-am-i` para empezar.

---

## Paso A — `--add-vault` subflow (R-6.4)

Solo se ejecuta cuando el usuario invoca `/sq-init --add-vault`. No toca el vault ni la
estructura PARA; sólo añade una nueva entrada `[[vaults]]` a `~/.squirrel/config.toml`.

### A.1 — Pre-requisitos

Verificar que `~/.squirrel/config.toml` ya existe. Si no existe, decirle al usuario que
corra `/sq-init` (sin flag) primero y detener.

```bash
[ ! -f ~/.squirrel/config.toml ] && \
  echo "❌ No existe ~/.squirrel/config.toml. Corré /sq-init (sin --add-vault) primero." && \
  exit 1
```

Mostrar los vaults ya configurados para que el usuario tenga contexto:

```bash
SQUIRREL_DIR=$(find "${HOME}/.claude/plugins" "${HOME}/others" \
    -maxdepth 4 -name "plugin.json" -path "*squirrel*" 2>/dev/null \
    | head -1 | xargs dirname 2>/dev/null | xargs dirname 2>/dev/null)
[ -z "$SQUIRREL_DIR" ] && echo "❌ No se encontró el directorio del plugin squirrel." && exit 1

python3 -c "
import sys, pathlib
sys.path.insert(0, '$SQUIRREL_DIR/lib')
from config_loader import list_vaults, NoVaultsConfiguredError
try:
    for v in list_vaults():
        marker = '  (default)' if v.default else ''
        print(f'  {v.name:<20} {v.path}{marker}')
except NoVaultsConfiguredError:
    print('  (ningún vault configurado todavía)')
"
```

### A.2 — Preguntar nombre, path, y set-as-default

Preguntar al usuario, una por vez (usando `AskUserQuestion` si está disponible, o un
prompt simple en chat). Los tres campos son obligatorios:

1. **`name`** — short name del vault (e.g. `work`, `personal`, `client-a`). Sin espacios,
   minúsculas + guiones recomendado. Debe ser único entre los vaults existentes.
2. **`path`** — ruta absoluta al directorio del vault. Tilde (`~`) se expande. El
   directorio debe existir.
3. **`set-as-default? (y/n)`** — si el usuario responde `y`, este vault pasa a ser el
   default y los demás se marcan `default = false`. Si responde `n`, el default actual
   no cambia.

Guardar las respuestas como `$VAULT_NAME`, `$VAULT_PATH`, `$SET_DEFAULT` (`y` o `n`).

### A.3 — Validar y escribir al config

Toda la validación (nombre duplicado, path inexistente, path que no es directorio) vive
en `config_loader.add_vault` (R-6.4 / D3). El handler aquí es un wrapper delgado:

```bash
RESULT=$(python3 -c "
import sys, pathlib
sys.path.insert(0, '$SQUIRREL_DIR/lib')
from config_loader import add_vault, set_default, ValidationError, ConfigError
try:
    v = add_vault('$VAULT_NAME', '$VAULT_PATH')
    if '$SET_DEFAULT' == 'y':
        set_default('$VAULT_NAME')
        print(f'OK {v.name} {v.path} default=true')
    else:
        print(f'OK {v.name} {v.path} default=false')
except ValidationError as e:
    print(f'ERROR {e}', file=sys.stderr); sys.exit(1)
except ConfigError as e:
    print(f'ERROR {e}', file=sys.stderr); sys.exit(2)
" 2>&1)
EXIT_CODE=$?
```

- `EXIT_CODE == 0` → confirmar al usuario:
  ```
  ✅ Vault '<name>' añadido (<path>)
     ¿Default actualizado? <sí/no>
  Próximo paso: probá `squirrel vaults list` o corré algún comando con `--vault <name>`.
  ```
- `EXIT_CODE != 0` → mostrar el mensaje de error (de `RESULT` o stderr) y sugerir
  arreglar el nombre / path antes de reintentar. NO continuar con más pasos.

### A.4 — Anti-patterns

- ❌ No editar `config.toml` a mano desde este flujo — siempre pasar por
  `config_loader.add_vault` y `config_loader.set_default` para que la validación
  (path existe, nombre único, exactamente un default) se aplique uniformemente.
- ❌ No tocar la estructura del vault recién agregado — el usuario es responsable de
  que ya esté inicializada con las carpetas PARA. Si quiere setup completo, debe
  correr `/sq-init` apuntando al nuevo vault como default temporal.
- ❌ No correr los pasos 1–6 del setup inicial cuando `--add-vault` está presente —
  ese flujo asume primera instalación.

