---
name: squirrel-recover
description: Recover lost session context when the user forgot to run /sq-end. Reads session-manifest.jsonl (primary) or Claude's own JSONL history (fallback), generates a 5-line summary via claude -p, and asks the user what to do with it. Use when the user says "I lost the session", "I forgot to run /sq-end", "what did I do yesterday", "recover", or runs /sq-recover. Accepts an optional `vault_name` argument; when omitted, operates on the default vault (R-7.1, R-7.3).
---

# squirrel:recover

## Purpose

Recover cognitive context from a forgotten session. The user closed Claude without running `/sq-end` — this skill reconstructs what happened using the edit manifest or Claude's own session history, then offers to persist it.

## When to invoke

- Explicit: `/sq-recover`, "I lost the session", "I forgot to run sq-end", "what did I do yesterday"
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
[ -z "$SCANNER" ] && echo "❌ session_scanner.py not found. Check your installation." && exit 1
```

<!-- @spec SESSION-007, SESSION-008 -->
### Step 2: Scan for recoverable sessions

```bash
SESSIONS=$(python3 "$SCANNER" --vault "$VAULT_PATH" --max-age-hours 72 --pretty 2>&1)
EXIT_CODE=$?
```

If `EXIT_CODE != 0` or `SESSIONS` is `[]`, tell the user: "No recoverable sessions found in the last 72 h." and stop.

### Step 3: Present session list to the user

Show a numbered list:
```
🔍 Recoverable sessions (last 72 h):

  1. <cwd>  —  <last_seen date>  —  <entry_count> edits  —  source: <source>
  2. ...
```

Ask: "Which one do you want to recover? (number or Enter to cancel)"

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
Recovered work session. List of edited files:
<files_edited — one per line, redacted if needed>

Working directory: <cwd>
From: <first_seen>  To: <last_seen>

Generate a 5-line summary of what likely happened in this work session.
Be specific about which files were modified and what kind of work they represent.
```

```bash
mkdir -p "$CACHE_DIR"
SUMMARY=$(echo "$PROMPT" | claude -p 2>/dev/null)
echo "$SUMMARY" > "$CACHE_FILE"
```

Display the summary:
```
📋 Session summary (<last_seen>):

<SUMMARY>
```

<!-- @spec SESSION-012 -->
### Step 5: Disposition

Ask the user:
```
What should we do with this summary?

  a) append-to-shutdown  → add it as a shutdown note to the active intent
  b) inbox              → save it in vault/99-Resources/Captures/
  c) project            → save it in the project (<infered_project>)
  d) raw                → display it on screen (already done)
  e) discard            → discard it (without saving)
```

Handle each option:

**append-to-shutdown**: Append to the active intent's shutdown notes section (same format as `squirrel:session-end` shutdown notes, but labeled "RECOVERED").

**inbox**: Write to `<vault>/99-Resources/Captures/RECOVERED-<date>-<hash>.md` with frontmatter `tipo: recovered-session` and `estado: inbox`.

**project**: Ask which project, then write to `<vault>/01-Proyectos-Activos/<PROJECT>/RECOVERED-<date>-<hash>.md`.

**raw**: Already displayed — confirm "Done, only displayed."

**discard**: Confirm "Discarded. The cached summary is kept for future reference."

## Anti-patterns

- ❌ Never call `claude -p` if the cache file already exists — check hash first
- ❌ Never pass corporate-env file paths to `claude -p` when `compliance.strict = true`
- ❌ Never write vault files without user choosing a disposition option
- ❌ Never invent file contents — only summarize what the file paths and timestamps suggest
