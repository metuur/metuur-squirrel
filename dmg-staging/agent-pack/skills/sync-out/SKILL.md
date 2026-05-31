---
name: squirrel-sync-out
description: Generate a SQUIRREL-PACKAGE — a self-contained Markdown block containing notes, research, decisions, or context that the user wants to transfer between air-gapped environments (e.g., personal computer to work computer, or vice versa). Use when user says "exportar", "necesito llevarme esto", "generar paquete", "/sq-sync-out", "preparar transferencia", or before they need to switch environments. The output is a hash-signed Markdown block that can be copied or emailed; the receiving side uses sync-in to apply it. Accepts an optional `vault_name` argument to choose which vault to export from; when omitted, exports from the default vault (R-7.1, R-7.3).
---

# squirrel:sync-out

## Purpose
Bridge two air-gapped environments (personal/corporate) by generating a self-contained, hash-verified Markdown block. The user manually transfers via clipboard or email. The other side applies via `sync-in`.

NEVER attempt to send data automatically. The user is the only network.

## When to invoke
- Explicit: `/sq-sync-out`, "necesito llevarme esto al trabajo", "exportar para personal"
- After research session (suggest): "¿Querés generar paquete para llevarte esta investigación?"
- After session-end (offer if it looks like cross-environment work)

## Workflow

### Step 1: Determine scope of the package
ASK the user (or accept arguments):
- `--scope=<TAG>` — single intent/decision/note
- `--scope=<PROJECT>:research` — all research notes for a project
- `--scope=<PROJECT>:*` — entire project
- `--scope=<PROJECT>:decisions` — only decisions
- `--scope=manual` — let user select notes one by one
- `--since=<DATE>` — anything created/modified since date

If no scope provided, show a menu:
```
¿Qué incluir en el paquete?
  1) Solo el intent activo: <INTENT-TAG>
  2) Toda la investigación de <PROJECT> (últimas N notas)
  3) Las decisiones de <PROJECT>
  4) Selección manual
  5) Todo lo modificado en las últimas 24h
```

<!-- @spec SYNC-002 -->
### Step 2: Collect files
Based on scope, build a list of file paths to include.

For each file:
- Read content
- Validate it's safe to transfer (see "Compliance check" below)
- Preserve frontmatter exactly

### Step 3: Compliance check (CRITICAL)
Before including ANY file, run these checks:

1. **Path check**: Is the file inside the configured `vault_path`? If not → REJECT
2. **Sensitive content scan**: Look for patterns:
   - API keys, tokens (regex match)
   - Email addresses that look like internal company addresses (if config has `corporate_domains`)
   - Credit card numbers, SSNs
   - Passwords (variable names containing "password", "secret", "key" with values)

If any sensitive content is found:
```
⚠️ Detectado contenido sensible en <file>:
   Línea N: <redacted preview>

¿Cómo proceder?
  a) Excluir este archivo del paquete
  b) Redactar las líneas detectadas y continuar
  c) Cancelar paquete entero
```

3. **Direction check**: Read `~/.squirrel/config.toml` for the `direction` field:
   - If `direction = "personal-to-work"`: warn if any tag starts with `WORK-` or matches `corporate_only_tags`
   - If `direction = "work-to-personal"`: warn if any tag matches `personal_only_tags`

Default: ask for confirmation per-file if uncertain.

<!-- @spec SYNC-001 -->
### Step 4: Generate the package
Use this EXACT format (the receiver parses it strictly):

```markdown
<!-- SQUIRREL-PACKAGE v1 -->
<!--
  from: <personal|work|<env-name>>
  to: <personal|work|<env-name>>
  generated_at: <ISO-8601 UTC>
  generated_by: <agent-name@hostname>
  scope: <scope-description>
  files_count: <N>
  hash_sha256: <hash-of-payload>
  intent: <short description of why this package exists>
  receiver_instructions: apply-with-sync-in
-->

# 📦 Context Bridge Package

**De**: <from-env>  →  **Para**: <to-env>
**Generado**: <human-readable date>
**Scope**: <scope>
**Archivos**: <count>

> 📋 Para aplicar: en el otro entorno, abrí Claude Code / Codex y pegá ESTE bloque completo
> en el chat. El skill `squirrel:sync-in` lo procesará automáticamente.

---

## 📑 Resumen del paquete

<For each file, one line:>
- `<file-target-path>` — <operation> — <one-line description>

---

## 📂 Archivos a aplicar

<For each file:>

### Archivo 1: <target-path-relative-to-vault>

**Operación**: <create | update | append | merge>
**Tag**: `<TAG>`
**Conflicto si existe**: <ask | overwrite | skip>

```markdown
<exact content of the file, including frontmatter>
```

---

### Archivo 2: ...

<repeat>

---

<!-- END-SQUIRREL-PACKAGE -->
```

### Step 5: Compute hash
Hash the canonical payload:
1. Concatenate all file contents (in order, separated by `\n---\n`)
2. SHA-256 the result
3. Hex-encode
4. Insert into the header

The hash protects against:
- Clipboard truncation
- Email body mangling
- Accidental modification

### Step 6: Present the package
Show the full Markdown block to the user.

Then offer delivery options:
```
✅ Paquete generado (<N> archivos, <X> KB)

¿Cómo lo querés transferir?
  1) Copiar al clipboard
  2) Abrir como draft de email (mailto:)
  3) Guardar a archivo local: <vault>/.squirrel/outgoing/<timestamp>.md
  4) Solo mostrar (lo copiás manualmente)
```

For option 2, construct a `mailto:` URI:
```
mailto:<your-email>?subject=Context%20Bridge:%20<scope>&body=<urlencoded-package>
```

NOTE: Most mailto URIs have a body length limit (~2000 chars). If the package exceeds, switch to option 1 or 3 automatically.

### Step 7: Log the export
Write to `<vault>/.squirrel/outgoing/log.jsonl`:
```json
{"ts": "<ISO>", "scope": "<scope>", "files": <N>, "hash": "<hash>", "to": "<env>"}
```

This gives you an audit trail of what left this environment.

### Step 8: Suggest next steps
```
✅ Paquete listo.

Próximos pasos sugeridos:
  • En tu otro entorno, abrí Claude Code/Codex
  • Pegá el bloque completo en el chat
  • El skill sync-in te pedirá confirmación antes de aplicar

📋 Si el paquete contiene tareas pendientes, también podés:
  → /sq-brief <PROJECT> antes de aplicar del otro lado, para tener contexto
```

## Special modes

### Encrypted mode
If `config.toml` has `encryption.enabled = true`:
1. After generating the package, pipe through GPG:
   ```bash
   echo "$PACKAGE" | gpg --armor --encrypt --recipient <recipient-key>
   ```
2. Wrap the encrypted output in the package header
3. Sync-in on the other side will decrypt automatically if it has the key

This is opt-in. Default is plaintext (intentionally — auditability over confidentiality).

### Diff mode
If `--diff` argument: instead of full content, generate a diff against the OTHER environment's last known state (requires the other env to have done a sync-out previously, with the hash recorded).

This is advanced — skip for MVP.

### Selective shutdown notes
If the scope includes intents, the user may want to include OR exclude the shutdown notes (they're verbose):
```
¿Incluir shutdown notes en el paquete? (sí: más contexto / no: paquete más liviano)
```

## Anti-patterns
- ❌ Don't include files outside the configured vault
- ❌ Don't include `.git/` or hidden files
- ❌ Don't include credentials, API keys, env files
- ❌ Don't generate a package without showing the user what's inside FIRST
- ❌ Don't send anything over the network — air-gap is HUMAN
- ❌ Don't skip the hash — it's how the other side trusts the paste

## Output style
- Show the package once, clearly delimited
- After the package, brief next-step guidance
- If sensitive content was detected and excluded/redacted, REPORT IT in the confirmation

## References

- Saltzer & Schroeder (1975): complete mediation — every export must be reviewed before leaving the boundary
- Rivest, Shamir & Adleman (1978): public-key cryptography — GPG-based optional encryption for sensitive vaults
- Allen, D. (2001): GTD "trusted system" — the export must be verifiable (hash) to be trusted on the receiving end
- Barkley, R.A. (2015): ADHD hyperfocus risk — scope guard prevents exporting entire vault when only one project was intended
