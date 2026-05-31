---
name: squirrel-recover
description: Recover lost session context when the user forgot to run /sq-end. Reads session-manifest.jsonl (primary) or Claude's own JSONL history (fallback), generates a 5-line summary via claude -p, and asks the user what to do with it. Use when the user says "perdí la sesión", "me olvidé de /sq-end", "qué hice ayer", "recover", or runs /sq-recover. Accepts an optional `vault_name` argument; when omitted, operates on the default vault (R-7.1, R-7.3).
---

# squirrel:recover

## Purpose

Recover cognitive context from a forgotten session. The user closed Claude without running `/sq-end` — this skill reconstructs what happened using the edit manifest or Claude's own session history, then offers to persist it.

## When to invoke

- Explicit: `/sq-recover`, "perdí la sesión", "me olvidé el sq-end", "qué hice ayer"
- When `SessionStart` finds no recent shutdown note for the active project AND the manifest has entries within 72 h

## Workflow

### Step 1: Resolve vault path via config_loader and locate scripts

When the skill is invoked with `vault_name`, that named vault is used. When
omitted, `config_loader.get_vault(name=None)` returns the default vault (R-7.3).

```bash
VAULT_PATH=$(python3 -c "
import sys, pathlib
for c in [pathlib.Path('~/.claude/plugins/squirrel/lib').expanduser()] + list(pathlib.Path.home().glob('others/*/squirrel/lib')) + list(pathlib.Path.home().glob('others/*/*/squirrel/lib')):
    if c.exists(): sys.path.insert(0, str(c)); break
from config_loader import get_vault, ConfigError
try:
    name = '$vault_name' if '$vault_name' else None
    print(get_vault(name=name).path)
except ConfigError as e:
    print(f'ERROR: {e}', file=sys.stderr); sys.exit(1)
" 2>&1)
[ $? -ne 0 ] && echo "❌ $VAULT_PATH" >&2 && exit 1

SCANNER=$(find "${HOME}/.claude" "${HOME}/others" -name session_scanner.py -path "*/squirrel/*" 2>/dev/null | head -1)
[ -z "$SCANNER" ] && echo "❌ session_scanner.py no encontrado. Verificá la instalación." && exit 1
```

<!-- @spec SESSION-007, SESSION-008 -->
### Step 2: Scan for recoverable sessions

```bash
SESSIONS=$(python3 "$SCANNER" --vault "$VAULT_PATH" --max-age-hours 72 --pretty 2>&1)
EXIT_CODE=$?
```

If `EXIT_CODE != 0` or `SESSIONS` is `[]`, tell the user: "No encontré sesiones recuperables en las últimas 72 h." and stop.

### Step 3: Present session list to the user

Show a numbered list:
```
🔍 Sesiones recuperables (últimas 72 h):

  1. <cwd>  —  <last_seen date>  —  <entry_count> edits  —  fuente: <source>
  2. ...
```

Ask: "¿Cuál querés recuperar? (número o Enter para cancelar)"

If the user cancels, stop.

<!-- @spec SESSION-009, SESSION-010 -->
### Step 4: Generate summary (with cache)

For the selected session:

```bash
HASH=$(echo "$SELECTED_SESSION_JSON" | python3 -c "import sys,hashlib,json; d=sys.stdin.read(); print(hashlib.sha256(d.encode()).hexdigest()[:16])")
CACHE_DIR="${VAULT_PATH}/.squirrel/llm-cache"
CACHE_FILE="${CACHE_DIR}/${HASH}.md"
```

If `$CACHE_FILE` exists → read and display it, skip `claude -p` call.

Otherwise:

**Compliance check before calling `claude -p`:**
Read `~/.squirrel/config.toml` for `compliance.strict` and `compliance.corporate_domains`.
If `strict = true` AND any file in `files_edited` matches a corporate domain path → redact those paths (replace with `[redacted]`) before building the prompt.

Build prompt:
```
Sesión de trabajo recuperada. Lista de archivos editados:
<files_edited — one per line, redacted if needed>

Directorio de trabajo: <cwd>
Desde: <first_seen>  Hasta: <last_seen>

Generá un resumen de 5 líneas de lo que probablemente pasó en esta sesión de trabajo.
Sé concreto sobre qué archivos fueron modificados y qué tipo de trabajo representan.
```

```bash
mkdir -p "$CACHE_DIR"
SUMMARY=$(echo "$PROMPT" | claude -p 2>/dev/null)
echo "$SUMMARY" > "$CACHE_FILE"
```

Display the summary:
```
📋 Resumen de sesión (<last_seen>):

<SUMMARY>
```

<!-- @spec SESSION-012 -->
### Step 5: Disposition

Ask the user:
```
¿Qué hacemos con este resumen?

  a) append-to-shutdown  → agregarlo como shutdown note al intent activo
  b) inbox              → guardarlo en vault/99-Resources/Captures/
  c) project            → guardarlo en el proyecto (<infered_project>)
  d) raw                → mostrarlo en pantalla (ya está hecho)
  e) discard            → descartarlo (sin guardar)
```

Handle each option:

**append-to-shutdown**: Append to the active intent's shutdown notes section (same format as `squirrel:session-end` shutdown notes, but labeled "RECOVERED").

**inbox**: Write to `<vault>/99-Resources/Captures/RECOVERED-<date>-<hash>.md` with frontmatter `tipo: recovered-session` and `estado: inbox`.

**project**: Ask which project, then write to `<vault>/01-Proyectos-Activos/<PROJECT>/RECOVERED-<date>-<hash>.md`.

**raw**: Already displayed — confirm "Listo, solo se mostró."

**discard**: Confirm "Descartado. El resumen en caché se mantiene para referencia futura."

## Anti-patterns

- ❌ Never call `claude -p` if the cache file already exists — check hash first
- ❌ Never pass corporate-env file paths to `claude -p` when `compliance.strict = true`
- ❌ Never write vault files without user choosing a disposition option
- ❌ Never invent file contents — only summarize what the file paths and timestamps suggest
