---
name: squirrel-sync-in
description: Parse, validate, and apply a SQUIRREL-PACKAGE that the user has pasted into the chat. Use whenever the user pastes a block starting with `<!-- SQUIRREL-PACKAGE` (auto-detect), or runs /sq-sync-in. Validates hash, shows diff against local vault, asks for confirmation, then applies operations atomically. Logs to audit trail. Accepts an optional `vault_name` argument to choose which vault to apply into; when omitted, applies to the default vault (R-7.1, R-7.3).
---

# squirrel:sync-in

## Purpose
Receive a context package from the OTHER environment (personal ↔ work) and apply it to the LOCAL vault safely. The user pasted the package — your job is to validate, show diff, ask, apply.

## When to invoke
- **Auto-detect**: if user message contains `<!-- SQUIRREL-PACKAGE`, AUTOMATICALLY load this skill
- Explicit: `/sq-sync-in`
- Hook `UserPromptSubmit` can detect the pattern and trigger automatically

## Workflow

### Step 1: Parse the package
Locate the boundary markers:
- Start: `<!-- SQUIRREL-PACKAGE v1 -->`
- End: `<!-- END-SQUIRREL-PACKAGE -->`

If markers are missing or unbalanced → REJECT with clear error:
```
❌ El paquete está incompleto o mal formateado.
   Faltó: <start-marker | end-marker>
   ¿Lo copiaste entero del email/clipboard?
```

### Step 2: Parse header
Extract from the HTML comment block at top:
- `from`, `to`, `generated_at`, `scope`, `files_count`, `hash_sha256`, `intent`, `receiver_instructions`

If `to` mismatches the current environment (configured in `~/.squirrel/config.toml` as `environment_name`):
```
⚠️ Este paquete fue generado para "<to>" pero estás en "<current>".
   ¿Aplicarlo igual? (sí / no)
```

<!-- @spec SYNC-003 -->
### Step 3: Validate hash
Reconstruct the canonical payload:
1. Extract content of each "Archivo N" code block
2. Concatenate in order, separated by `\n---\n`
3. SHA-256 hash, hex-encode
4. Compare to `hash_sha256` from header

If mismatch:
```
❌ Hash inválido — el paquete podría estar corrupto o truncado.
   Esperado: <expected>
   Calculado: <calculated>

¿Continuar de todos modos? (NO recomendado)
```

DO NOT apply if hash fails unless user explicitly overrides.

### Step 4: Parse each file entry
For each `### Archivo N:` section, extract:
- `target_path` (from the section header)
- `operacion` (create | update | append | merge)
- `tag`
- `conflicto_si_existe` (ask | overwrite | skip)
- `content` (the markdown code block content)

Resolve `target_path` against the local vault root.

### Step 5: Check for conflicts
For each file:
- If `operacion = create` and the file exists → CONFLICT
- If `operacion = update` and the file does NOT exist → MISMATCH
- If `operacion = append` and the file does NOT exist → CREATE NEW
- If `operacion = merge` → need 3-way merge (advanced; for MVP, treat as `update` with diff)

### Step 6: Build the plan
Generate a summary:

```markdown
📦 Paquete recibido:
   De: <from> → Para: <to>
   Generado: <human-readable>
   Scope: <scope>
   Hash: ✓ válido

📋 Plan de aplicación (<N> operaciones):

| # | Operación | Archivo | Estado local |
|---|-----------|---------|--------------|
| 1 | CREATE    | 01-Proyectos-Activos/X/Y.md | (no existe) |
| 2 | UPDATE    | 01-Proyectos-Activos/X/Z.md | existe — DIFF abajo |
| 3 | APPEND    | 99-Resources/inbox.md | existe — append |
| 4 | CREATE    | 01-Proyectos-Activos/X/W.md | ⚠️ YA EXISTE — conflicto |

```

<!-- @spec SYNC-004 -->
### Step 7: Show diffs for conflicts
For each file marked CONFLICT or UPDATE, show a unified diff:

```diff
--- local: 01-Proyectos-Activos/X/Z.md
+++ incoming
@@ -10,7 +10,9 @@
 ## Open questions
-- ¿Refresh token en localStorage o httpOnly cookie?
+- ¿Refresh token en localStorage o httpOnly cookie? [DECIDIDO: httpOnly]
+- ¿Email no verificado en Google → cómo manejarlo?
```

For CREATE operations on existing files, ask resolution:
```
Conflicto en <file>:
  a) sobrescribir local con el paquete
  b) preservar local, descartar paquete
  c) crear con sufijo -CONFLICT (revisar manualmente)
  d) ver diff
```

### Step 8: Ask for confirmation
After showing the plan and any diffs:

```
¿Aplicar el paquete?
  (sí: aplicar todo según el plan)
  (selectivo: te pregunto archivo por archivo)
  (cancelar: no se aplica nada)
```

### Step 9: Apply operations atomically
For each operation:
- Use Write tool to create/overwrite
- Use Edit tool for surgical updates
- For APPEND: read existing, concatenate, write

If ANY operation fails, do NOT roll back automatically — but report clearly:
```
✅ Aplicados: 3 archivos
⚠️ Fallidos: 1
   - <file>: <error>
```

### Step 10: Audit log
Write to `<vault>/.squirrel/applied/<timestamp>-<hash[:8]>.json`:
```json
{
  "applied_at": "<ISO>",
  "from": "<env>",
  "to": "<env>",
  "package_hash": "<full hash>",
  "operations": [
    {"op": "create", "path": "...", "result": "ok"},
    {"op": "update", "path": "...", "result": "ok"},
    {"op": "create", "path": "...", "result": "skipped-conflict"}
  ],
  "applied_by": "<agent>@<hostname>"
}
```

This gives a forensic trail: if your security/compliance ever asks "what did you bring in", point to this file.

### Step 11: Update Project Pages
For any new intent/decision/research note created, check if it should be linked from a Project Page. Suggest:
```
🔗 Sugerencia: agregar los siguientes links a Project Pages:
   - <PROJECT-A>.md: agregar [[<NEW-TAG-1>]] bajo "Componentes e Intents"
   - <PROJECT-A>.md: agregar [[<NEW-TAG-2>]] bajo "Decisiones"

¿Aplico estos links?
```

### Step 12: Final confirmation
```
✅ Paquete aplicado exitosamente.

Resumen:
  • Creados: <N>
  • Actualizados: <N>
  • Saltados (conflicto): <N>

Log: <vault>/.squirrel/applied/<timestamp>-<short-hash>.json

Sugerencia: corré /sq-brief <PROJECT> para ver el estado actualizado.
```

## Security considerations

### Path traversal protection
- Every target path must resolve INSIDE the vault root
- Reject `../`, absolute paths outside vault, symlinks pointing outside
- If a path is suspicious → REJECT and report

### Code execution prevention
- The package is PURE MARKDOWN — no shell scripts, no eval
- If a file contains shell scripts in fenced blocks, that's fine (it's content), but DO NOT execute anything from the package automatically

### Foreign environment marker
If the package's `from` field is "personal" and the current environment is "work":
- Add a TAG in the frontmatter of imported notes: `imported_from: personal`
- Add a comment: `<!-- Imported from personal environment on <date> -->`

This makes it visible later that this content originated outside.

### Compliance mode
If `config.toml` has `compliance.strict = true`:
- BLOCK any package that includes files with tags NOT in `allowed_inbound_tags`
- BLOCK any package whose `from` field is not in `allowed_inbound_environments`
- Report rejected files to the user

## Special cases

### Encrypted package
If the payload looks like GPG armored output:
- Pipe through `gpg --decrypt` (requires user's key to be configured)
- Then re-parse as normal package
- If decryption fails → clear error

### Package version mismatch
If header is `v2` but we only know `v1` → REJECT with message:
```
❌ Versión del paquete no soportada: v2.
   Actualizá squirrel a una versión compatible.
```

### Partial paste
If only the header is present but no files → REJECT:
```
❌ Solo encontré el header del paquete, sin archivos.
   ¿Copiaste el bloque completo?
```

### Re-applying the same package
The audit log has hashes — detect re-application:
```
ℹ️ Este paquete ya fue aplicado el <date> (mismo hash).
   ¿Re-aplicar de todos modos? (puede sobrescribir cambios locales hechos desde entonces)
```

## Anti-patterns
- ❌ Don't apply WITHOUT showing the diff first
- ❌ Don't skip hash verification silently
- ❌ Don't write outside the vault root, EVER
- ❌ Don't execute any code from the package
- ❌ Don't auto-resolve conflicts — ask the user
- ❌ Don't lose the original package — log it before applying

## Output style
- Structured tables for the plan
- Clear diffs (unified format)
- One confirmation gate before applying
- Audit log path mentioned in the confirmation

## References

- Saltzer & Schroeder (1975): fail-safe defaults — unrecognized input should be rejected, not silently accepted
- Anderson, R. (2020): Security Engineering — hash verification as integrity primitive for untrusted channels
- Allen, D. (2001): GTD "inbox zero" — temporary holding area with guaranteed review prevents indefinite limbo
