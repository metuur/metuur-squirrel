---
name: squirrel-sync-out
description: Generate a SQUIRREL-PACKAGE — a self-contained Markdown block containing notes, research, decisions, or context that the user wants to transfer between air-gapped environments (e.g., personal computer to work computer, or vice versa). Use when user says "export", "I need to take this with me", "generate package", "/sq-sync-out", "prepare transfer", or before they need to switch environments. The output is a hash-signed Markdown block that can be copied or emailed; the receiving side uses sync-in to apply it. Accepts an optional `vault_name` argument to choose which vault to export from; when omitted, exports from the default vault (R-7.1, R-7.3).
---

# squirrel:sync-out

## Purpose
Bridge two air-gapped environments (personal/corporate) by generating a self-contained, hash-verified Markdown block. The user manually transfers via clipboard or email. The other side applies via `sync-in`.

NEVER attempt to send data automatically. The user is the only network.

## When to invoke
- Explicit: `/sq-sync-out`, "I need to take this to work", "export for personal"
- After research session (suggest): "Do you want to generate a package to take this research with you?"
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
What to include in the package?
  1) Only the active intent: <INTENT-TAG>
  2) All research for <PROJECT> (last N notes)
  3) The decisions for <PROJECT>
  4) Manual selection
  5) Everything modified in the last 24h
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
⚠️ Sensitive content detected in <file>:
   Line N: <redacted preview>

How to proceed?
  a) Exclude this file from the package
  b) Redact the detected lines and continue
  c) Cancel the entire package
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

**From**: <from-env>  →  **To**: <to-env>
**Generated**: <human-readable date>
**Scope**: <scope>
**Files**: <count>

> 📋 To apply: in the other environment, open Claude Code / Codex and paste THIS entire block
> into the chat. The `squirrel:sync-in` skill will process it automatically.

---

## 📑 Package summary

<For each file, one line:>
- `<file-target-path>` — <operation> — <one-line description>

---

## 📂 Files to apply

<For each file:>

### File 1: <target-path-relative-to-vault>

**Operation**: <create | update | append | merge>
**Tag**: `<TAG>`
**Conflict if exists**: <ask | overwrite | skip>

```markdown
<exact content of the file, including frontmatter>
```

---

### File 2: ...

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
✅ Package generated (<N> files, <X> KB)

How do you want to transfer it?
  1) Copy to clipboard
  2) Open as email draft (mailto:)
  3) Save to local file: <vault>/.squirrel/outgoing/<timestamp>.md
  4) Just show it (copy manually)
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
✅ Package ready.

Suggested next steps:
  • In your other environment, open Claude Code/Codex
  • Paste the entire block into the chat
  • The sync-in skill will ask for confirmation before applying

📋 If the package contains pending tasks, you can also:
  → /sq-brief <PROJECT> before applying on the other side, to have context
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
Include shutdown notes in the package? (yes: more context / no: lighter package)
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
