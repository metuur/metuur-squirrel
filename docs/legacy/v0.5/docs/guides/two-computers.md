# Two Computers (Advanced) — Sync Between Environments Without Cloud Sync

> 🎯 *What you'll learn:* How to move notes between a personal computer and a work computer **without** automatic cloud sync. This is the "air-gap" feature — you manually control every byte that crosses.

**Version:** Squirrel v0.5.0  
**Last updated:** 2026-05-24  
**Reading time:** ~15 minutes

---

## Table of Contents

1. [Why manual sync?](#why-manual-sync)
2. [Real-world scenario: Diego](#real-world-scenario-diego)
3. [Step 1: Generate a package (home)](#step-1-generate-a-package-home)
4. [Step 2: Transfer the package](#step-2-transfer-the-package)
5. [Step 3: Apply the package (work)](#step-3-apply-the-package-work)
6. [Scope reference](#scope-reference)
7. [Compliance checks](#compliance-checks)
8. [Audit trail](#audit-trail)
9. [GPG encryption (optional)](#gpg-encryption-optional)
10. [Troubleshooting](#troubleshooting)

---

## Why manual sync?

Squirrel **never syncs automatically**. Instead, you generate a package on one side, carry it across (email, paste, USB stick), and apply it on the other side. Why?

**1. Compliance** — Many workplaces forbid personal-cloud sync of company data. Manual = legal.

**2. Visibility** — You see the diff before applying. No surprise overwrites.

**3. Audit** — Every applied package leaves a record. If you ever need to prove what came in, you have it.

You're the network. You control every byte.

---

## Real-world scenario: Diego

Diego is a consultant. He does research on his **personal laptop at home** on the weekend (design research, competitive analysis, technical explorations). On **Monday at work**, he uses a corporate laptop on a network that can't access his personal cloud.

**The problem:** Diego's work laptop needs the research from his personal laptop, but:
- No automatic sync allowed (corporate policy)
- Personal laptop can't talk to work network (firewall)
- No shared USB drives available (security policy)

**The solution:** Squirrel's air-gap sync. Diego generates a package on personal, emails it to himself, applies it on work. 100% manual, 100% auditable, 100% legal.

---

## Step 1: Generate a package (home)

Diego worked all Saturday on design research. Sunday evening, he prepares to move that research to work Monday. On his **personal laptop**:

### What Diego runs

```
/sq-sync-out --scope=WORK-PROJECT:research
```

Squirrel asks: "What do you want to include?" Diego specifies:
- Scope: all research notes for `WORK-PROJECT`
- From: `personal` (his personal laptop)
- To: `work` (his work laptop)

### What Squirrel does

1. **Collects files** — Gathers all research notes tagged with `WORK-PROJECT` from the last 3 days
2. **Compliance check** — Scans for:
   - API keys or passwords (blocks them)
   - Email addresses from corporate domains (warns Diego)
   - Credit card numbers (blocks them)
   - Company confidential markings (warns Diego)
3. **Builds the package** — Creates a Markdown block with:
   - Header (meta info: from/to, date, files count, hash)
   - Summary (what's in it)
   - File contents (each research note)
4. **Generates hash** — SHA-256 fingerprint to detect tampering or truncation

### What Diego sees

```
✅ Paquete generado (3 archivos, 12 KB)

De: personal  →  Para: work
Scope: WORK-PROJECT:research
Generated: 2026-05-24 20:15 UTC
Hash: a3f5b8c9d2e1f4g7h0i3j6k9...

📦 Resumen:
- 01-Proyectos-Activos/WORK-PROJECT/WORK-PROJECT-RESEARCH-001.md — create
- 01-Proyectos-Activos/WORK-PROJECT/WORK-PROJECT-RESEARCH-002.md — create
- 01-Proyectos-Activos/WORK-PROJECT/WORK-PROJECT-RESEARCH-003.md — create

---

¿Cómo lo querés transferir?
  1) Copiar al clipboard
  2) Abrir como draft de email (mailto:)
  3) Guardar a archivo (.md)
  4) Solo mostrar
```

Diego picks **option 2** ("open as email draft"). Squirrel opens his email client with a pre-filled `To: diego@gmail.com`, `Subject: Context Bridge: WORK-PROJECT`, and the full package in the body.

Diego hits send. Done.

---

## Step 2: Transfer the package

The package is now in Diego's personal email inbox. **Multiple transfer methods:**

| Method | Pros | Cons |
|---|---|---|
| **Email body** | Instant, simple | Some mail clients truncate long bodies |
| **Email attachment** | Safe from truncation | Extra step to download/paste |
| **Paste in Slack DM** | Private, quick | Slack has retention limits |
| **USB stick** | Offline, airgapped | Physical transfer needed |
| **Copy-paste** | Ultra-simple | Easy to paste incomplete |

**Diego's choice:** He opened the email on his personal laptop, copied the full text from the email body (from `<!-- SQUIRREL-PACKAGE` all the way to `<!-- END-SQUIRREL-PACKAGE -->`), and pasted it into a .txt file that he emailed to his work email.

✅ **The package is now in Diego's work inbox.**

---

## Step 3: Apply the package (work)

Monday morning, Diego sits down at his **work laptop**. He opens Claude Code and opens the email with the package.

### What Diego does

He copies the entire package block (the full HTML comment + Markdown) and pastes it into Claude Code chat:

```
<!-- SQUIRREL-PACKAGE v1 -->
<!--
  from: personal
  to: work
  generated_at: 2026-05-24T20:15:00Z
  scope: WORK-PROJECT:research
  files_count: 3
  hash_sha256: a3f5b8c9d2e1f4g7h0i3j6k9...
-->

# 📦 Context Bridge Package

De: personal  →  Para: work
Generado: 2026-05-24 20:15 UTC
...
[full package content]
...
<!-- END-SQUIRREL-PACKAGE -->
```

### What Squirrel does (auto-detect)

The moment Diego pastes the package, Squirrel **automatically detects it** (looks for the `<!-- SQUIRREL-PACKAGE` marker) and invokes the sync-in skill:

```
📦 Paquete recibido

De: personal  →  Para: work
Generado: 2026-05-24 20:15 UTC
Hash: ✓ válido (coincide)

📋 Plan de aplicación (3 operaciones):

| # | Operación | Archivo | Estado local |
|---|-----------|---------|--------------|
| 1 | CREATE    | 01-Proyectos-Activos/WORK-PROJECT/WORK-PROJECT-RESEARCH-001.md | no existe ✓ |
| 2 | CREATE    | 01-Proyectos-Activos/WORK-PROJECT/WORK-PROJECT-RESEARCH-002.md | no existe ✓ |
| 3 | CREATE    | 01-Proyectos-Activos/WORK-PROJECT/WORK-PROJECT-RESEARCH-003.md | no existe ✓ |

¿Aplicar el paquete?
  (sí: aplicar todo)
  (selectivo: preguntarme archivo por archivo)
  (cancelar: no se aplica nada)
```

### What Diego sees (if conflicts)

If Diego had *already* created those files at work, Squirrel would show him diffs:

```diff
--- local: WORK-PROJECT-RESEARCH-001.md
+++ incoming
@@ -5,3 +5,7 @@
  ## Competitive Analysis
  
  Checked three competitors:
+ - Competitor A uses React + Node (noted detail differences)
+ - Competitor B uses Vue + Django (different data flow)
+ - Competitor C is custom (close to our approach)
```

Squirrel asks: "Override? Preserve local? Merge?" Diego picks one.

### What Diego confirms

Diego reviews the plan, says "sí", and the files are applied to his work vault. Done.

### What Squirrel records

Squirrel writes to `<vault>/.squirrel/applied/2026-05-24-a3f5b8c9.json`:

```json
{
  "applied_at": "2026-05-24T09:05:00Z",
  "from": "personal",
  "to": "work",
  "package_hash": "a3f5b8c9d2e1f4g7h0i3j6k9...",
  "operations": [
    {"op": "create", "path": "01-Proyectos-Activos/WORK-PROJECT/WORK-PROJECT-RESEARCH-001.md", "result": "ok"},
    {"op": "create", "path": "01-Proyectos-Activos/WORK-PROJECT/WORK-PROJECT-RESEARCH-002.md", "result": "ok"},
    {"op": "create", "path": "01-Proyectos-Activos/WORK-PROJECT/WORK-PROJECT-RESEARCH-003.md", "result": "ok"}
  ],
  "applied_by": "claude-code@diego-work-laptop"
}
```

**Forensic trail.** If Diego's company security ever asks "what did you bring in from personal?", he points to this log.

---

## Scope reference

What goes in a package? It's flexible:

| Scope | What it captures |
|---|---|
| `/sq-sync-out --scope=WORK-PROJECT:research` | All research notes for that project |
| `/sq-sync-out --scope=WORK-PROJECT:decisions` | All decisions only (no intents) |
| `/sq-sync-out --scope=WORK-PROJECT:*` | The whole project (intents, decisions, research) |
| `/sq-sync-out --scope=WORK-PROJECT-INTENT-005` | A single intent file |
| `/sq-sync-out --scope=WORK-PROJECT-INTENT-005 --include-shutdown` | That intent + all shutdown notes |
| `/sq-sync-out --since=2026-05-20` | Everything modified since that date |
| `/sq-sync-out --manual` | Let me pick files one by one |

**Diego's choice:** He used `--scope=WORK-PROJECT:research` to grab only research notes, not conclusions or decisions yet.

---

## Compliance checks

When Squirrel builds the package, it scans for sensitive content:

### What triggers a warning

```
⚠️ Detectado contenido sensible en WORK-PROJECT-RESEARCH-002.md:
   Línea 12: API_KEY=sk-proj-... [REDACTED]

¿Cómo proceder?
  a) Excluir este archivo del paquete
  b) Redactar la línea y continuar
  c) Cancelar paquete entero
```

**Diego's options:**
- **a) Exclude** — Don't include this file at all
- **b) Redact** — Keep the file but remove the sensitive line
- **c) Cancel** — Don't send the package (start over)

### What Squirrel checks for

- **API keys/tokens** — regex patterns for `sk-`, `ghp_`, `AKIA`, etc.
- **Passwords** — variables containing "password", "secret", "key" with values
- **Email** — addresses from corporate domains (if configured)
- **Credit cards** — 16-digit patterns
- **SSN** — 9-digit social security patterns

### Escape hatch (not recommended)

If Squirrel is too conservative and blocks something you know is safe:

```
/sq-sync-out --scope=WORK-PROJECT:research --force-include
```

This tells Squirrel to skip the compliance check. **Only use if you're 100% sure.** It's there for the 1% case where Squirrel is wrong.

---

## Audit trail

Every time Diego applies a package, Squirrel records it. Later, if Diego needs to audit:

```bash
ls -la ~/vault-notas/.squirrel/applied/
# 2026-05-24-a3f5b8c9.json
# 2026-05-25-b4g6c9d0.json
# ...
```

Each file shows:
- What was applied
- When
- From which environment
- The package hash (so he can verify it matches the original)
- Whether operations succeeded or failed

**Compliance audit:** Diego's IT security asks "what did you bring from personal to work?" Diego shows them `applied/2026-05-24-a3f5b8c9.json`. They see exactly what came in, when, and where.

---

## GPG encryption (optional)

For truly sensitive research (legal, medical, financial), Diego can encrypt the package end-to-end.

### Setup (one-time, on personal laptop)

```bash
# Generate a GPG key (if you don't have one)
gpg --gen-key

# Tell Squirrel to use it
# Edit ~/.squirrel/config.toml:
[encryption]
enabled = true
gpg_recipient = "diego@gmail.com"
```

### Generate encrypted package

```
/sq-sync-out --scope=WORK-PROJECT:sensitive --encrypt
```

Squirrel outputs:

```
-----BEGIN PGP MESSAGE-----

jA0EBAABCgA3FiEE...
[long encrypted block]
...
-----END PGP MESSAGE-----
```

**Only Diego's private key can decrypt this.** Even if someone intercepts the email, they see gibberish.

### Apply on work laptop

Diego pastes the encrypted block. Squirrel detects the `-----BEGIN PGP MESSAGE-----` marker, runs `gpg --decrypt`, and applies the decrypted files. Transparent.

---

## Troubleshooting

### ❌ "Hash mismatch — package might be corrupted"

**What happened:** The package was truncated or modified between generation and paste (usually a mail client adding line breaks).

**Fix:**
1. Open the original email on your personal laptop
2. Copy from `<!-- SQUIRREL-PACKAGE` (the very start) to `<!-- END-SQUIRREL-PACKAGE -->` (the very end)
3. Make sure your clipboard has EXACTLY those boundaries — no extra spaces, no truncation
4. Paste again

**If it keeps failing:** Save the package as a `.txt` file attachment instead of pasting from the email body. Email bodies are fragile.

---

### ❌ "The package's `to` field doesn't match my environment"

**What happened:** The package says "to: personal" but you're applying it on "work" (environment_name mismatch).

**Fix:** Squirrel asks you to confirm anyway. You can say "sí" if you intentionally want to apply it to a different environment. This is usually safe (maybe you misconfigured the environment name).

---

### ❌ "File conflict: this file already exists"

**What happened:** You ran the same package twice by mistake, or the file was created differently on work after you generated the package on personal.

**Fix:** Squirrel shows you the diff and asks:
- **a) Overwrite** — incoming package wins
- **b) Preserve local** — ignore incoming, keep what you have at work
- **c) Create with -CONFLICT suffix** — save incoming as FILENAME-CONFLICT.md (review manually later)

Pick the one that makes sense for your situation.

---

### ❌ "Paquete incompleto" (partial paste)

**What happened:** You only pasted part of the package (maybe your clipboard truncated it).

**Fix:** Go back to the original source, copy the entire block again, and paste the whole thing.

---

### ❌ "Want to undo a sync-in"

**What happened:** You applied a package, and now you realize something should have been different.

**Fix:** Open the audit log:

```bash
cat ~/.squirrel/applied/2026-05-24-a3f5b8c9.json
```

You'll see exactly which files were created/modified. Delete or revert them manually (they're just `.md` files in your vault). No built-in "undo" — it's just plain files.

---

## Where to go next

- **Using sync regularly?** → [Power User](./power-user.md) for advanced encryption and compliance mode.
- **Generating packages often?** → Consider automating with the CLI (see Power User).
- **Want to understand the security model?** → The philosophy: you're the network, you control every byte. Every package is audited. Encryption is optional.

The air-gap is Squirrel's most distinctive feature. You own your data end-to-end. 🐿️
