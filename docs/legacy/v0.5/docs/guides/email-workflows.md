# Email Workflows — Save incoming emails, generate outgoing summaries

Two recipes you'll use a lot:

1. **"Include this email in the notes"** — drop an incoming email (Sarah's bug report, your professor's reply, a vendor quote) into the right project's notes.
2. **"Generate an email summary from X"** — produce a stakeholder-ready summary of a project that you can paste into Gmail/Outlook/Slack in one shot.

Both flows are available in **two places**:

- **Claude Code (the terminal)** — slash commands `/sq-capture` and `/sq-brief`. Best when you're already in a coding session and have the email body in your clipboard.
- **The React web UI** — a "Paste email" tab in the Add-a-note modal (writes the email straight into the vault), and a "Get brief command" button on the project page (composes the exact slash command for you to paste into your AI agent). Best when you're triaging your inbox in a browser tab.

The CC path runs end-to-end inside Claude Code. The web UI path keeps Claude usage explicit — capture writes locally (no AI), and the brief flow hands you the command to run wherever you prefer.

---

## Table of Contents

1. [Recipe A — Include an email in the notes](#recipe-a--include-an-email-in-the-notes)
2. [Recipe B — Generate an email summary from a project](#recipe-b--generate-an-email-summary-from-a-project)
3. [Bonus — Receiving a SQUIRREL-PACKAGE via email (auto-sync)](#bonus--receiving-a-squirrel-package-via-email-auto-sync)
4. [Troubleshooting](#troubleshooting)

---

## Recipe A — Include an email in the notes

### Option 1 — From the web UI

1. Open the web UI and click **Add a note** (top-right of the header).
2. Switch the tab at the top of the modal from **Quick note** to **📧 Paste email**.
3. Fill in **From** (e.g. `sarah@acme.com`), **Subject**, and paste the email body.
4. Pick the target project from the dropdown (defaults to the project you're currently viewing).
5. Click **Save**. The note is written with a formatted email header:
   ```markdown
   📧 Email

   **From:** sarah@acme.com
   **Subject:** API timeout on /orders
   **Received:** 2026-05-25

   ---

   <body>
   ```
6. The page reloads; the new note appears in the project's notes list.

### Option 2 — From Claude Code

### When to use it

- A stakeholder sent you a bug report, a requirements clarification, or a quote — and you want it saved next to the relevant project so you can find it later from `/sq-start`.
- You want the email to count as *captured context* (it'll show up in the project page, in `/sq-brief`, and in the web UI).

### Command

```
/sq-capture include this email in <PROJECT-TAG> notes:

<paste the full email here — From, Subject, body, signature>
```

### Concrete example

```
/sq-capture include this email in TRABAJO-PROYECTO-A notes:

From: sarah@acme.com
Subject: API timeout on /orders during peak hours

Hi — we're seeing intermittent 30s timeouts on /orders between 3–5pm.
Could you investigate this week? Stakeholder: Sarah.
— Sarah
```

### What happens

The `squirrel:capture` skill will:

1. Pick a semantic tag like `TRABAJO-PROYECTO-A-RESEARCH-007` (it detects "email" → typically `research` or `reference`; if it looks like a feature request it might use `intent`).
2. Write a Markdown file with proper frontmatter into the project folder of the vault:
   ```
   ~/vault-tdah/01-Proyectos-Activos/TRABAJO-PROYECTO-A/
       TRABAJO-PROYECTO-A-RESEARCH-007.md
   ```
3. Add a link to it from the Project Page (`PROJECT.md` in that folder).

### Verify

Terminal:

```
ls -lt ~/vault-tdah/01-Proyectos-Activos/TRABAJO-PROYECTO-A/ | head -5
```

Web UI: open `http://localhost:<port>/projects/trabajo-proyecto-a` — the new note appears at the top of the project's notes list.

### Variants

| Command | Effect |
|---|---|
| `/sq-capture include this email in <PROJECT> notes: <body>` | Default — semantic tag inferred |
| `/sq-capture <body> --project=TRABAJO-PROYECTO-A --tag email` | Forces the tag if auto-detection picks the wrong type |
| `/sq-capture <body> --silent` | Saves without printing the file path |

### Anti-patterns

- ❌ Don't paste the email with `>` quote-prefixes ("> Hi —"). The `>` characters get captured verbatim. Paste the raw email body.
- ❌ Don't omit `From:` and `Subject:` — they help the skill name the note and help *you* find it three weeks later.
- ❌ Don't put PII you wouldn't want in your vault. The vault is local Markdown, but if your vault is in Obsidian-Sync or iCloud, the email will sync too.

---

## Recipe B — Generate an email summary from a project

### Option 1 — From the web UI

The web UI **does not run AI itself** — it generates the right slash command for you to run in your agent of choice. This keeps the UI instant (no waiting on a model) and lets you use Claude Code, Codex, Cursor, or any other tool that understands the squirrel plugin's commands.

1. Open the web UI, navigate to **My projects**, click the project.
2. In the action bar click **🖥️ Get brief command**.
3. A panel opens with:
   - **Recipient** input (optional). Type a stakeholder email — it appends `--email <to>` to the command and formats the brief for email.
   - **Slash command** box, e.g. `/squirrel:sq-brief TRABAJO-PROYECTO-A --email sarah@acme.com` with a **Copy** button.
   - **Headless variant** box, e.g. `claude -p "/squirrel:sq-brief TRABAJO-PROYECTO-A --email sarah@acme.com"` with a **Copy** button — for running from any terminal without opening an interactive session.
4. Paste the command into Claude Code (or run the headless variant in your shell). Claude executes the real `squirrel:brief` skill and produces the 6-section brief.
5. Paste the resulting brief into Gmail / Outlook / Slack yourself, or pipe the headless output to your clipboard:
   ```
   claude -p "/squirrel:sq-brief TRABAJO-PROYECTO-A --email sarah" | pbcopy
   ```

> No subprocess timeouts, no API key, no model usage tracked through the web UI — the UI is a prompt factory; you decide what runs the prompt.

### Option 2 — From Claude Code

### When to use it

- Friday afternoon — your lead asked "where are we on Project A?". You don't want to write the recap by hand.
- Before a 1:1 — you want to walk in with a structured update.
- Before pinging a client — you want to send a polite, factual status without staring at a blank cursor.

### Command

```
/sq-brief <PROJECT-TAG> --email <STAKEHOLDER>
```

### Concrete example

```
/sq-brief TRABAJO-PROYECTO-A --email sarah
```

### What happens

The `squirrel:brief` skill will:

1. Load the project's state via `lib/status_aggregator.py` (intents, decisions, last activity, open questions).
2. Produce a 6-section brief — NOW / DONE / NEXT / DECISIONS / STEPS / CONTEXT — adapted for an email to Sarah (less terse than Slack, less verbose than a full weekly review).
3. Offer three actions:

   ```
   ¿Querés que:
     a) Lo abra como draft de email para sarah
     b) Lo copie al clipboard
     c) Genere paquete sync-out (si vas a llevarlo a otro entorno)
   ```

   - Pick `a` to launch your system mail client (`mailto:` URL pre-filled with subject + body).
   - Pick `b` to paste into Gmail/Outlook/whatever yourself.
   - Pick `c` if you're cross-machine and want a SQUIRREL-PACKAGE block (see the Bonus section below).

### Variants

| Command | Effect |
|---|---|
| `/sq-brief <PROJECT> --email <name>` | Email-formatted, mailto draft offered |
| `/sq-brief <PROJECT> --short` | 3-line standup version (Slack-ready) |
| `/sq-brief <PROJECT>` | Full 6 sections, no formatting opinion |
| `/sq-brief --all` | Brief of every WIP project (Friday weekly review) |
| `/sq-brief <PROJECT> --vault NAME` | Run against a non-default vault |

### What the email looks like (abbreviated)

```
Subject: Status: TRABAJO-PROYECTO-A — week of 2026-05-25

Hi Sarah,

Quick update on Project A.

🎯 NOW
Investigating the /orders timeouts you flagged Monday. Reproduced locally
with a 2k-rps soak test.

✅ DONE (this week)
- Added DB connection-pool metrics (deployed Tuesday).
- Confirmed the timeout window matches a checkpoint pause in Postgres.

🎬 NEXT
Profile the checkpoint pause with pg_stat_progress_vacuum and propose a
mitigation by Thursday.

🌐 CONTEXT
- Stakeholder: you, Sarah.
- Deadline: investigation summary by Fri.

— Javier
```

### Anti-patterns

- ❌ Don't run `/sq-brief` on a project that has zero captured intents — you'll get a thin, useless brief. Capture a few things first via `/sq-capture` (Recipe A) or `/sq-end` to seed it.
- ❌ Don't edit the brief inside the terminal output. Pick `b` (clipboard) or `a` (mailto), then edit in your real email client.

---

## Bonus — Receiving a SQUIRREL-PACKAGE via email (auto-sync)

If you (or a teammate) ran `/sq-sync-out` on a different machine and emailed you the result, the email body will contain a block like:

```
<!-- SQUIRREL-PACKAGE v1 -->
... header + files + hash ...
<!-- END-SQUIRREL-PACKAGE -->
```

You don't need any command. Just **paste the email body into the Claude Code chat**:

1. The `UserPromptSubmit` hook (configured in `hooks/hooks.json`) detects the `<!-- SQUIRREL-PACKAGE` marker.
2. The `squirrel:sync-in` skill auto-fires.
3. It validates the SHA-256 hash, checks the `to:` field matches your machine, shows you a diff against the local vault, and asks for confirmation.
4. On approval, it writes the files atomically and logs the apply to `<vault>/.squirrel/applied/<timestamp>-<hash>.json`.

This is the "air-gap bridge" between personal and corporate environments: no shared drive, no MCP, no API — the email IS the transport.

### Manual fallback

If the auto-detect doesn't fire (e.g., the marker is inside a `>` quote block), run:

```
/sq-sync-in
```

…and the skill will look for the most recently saved package in `<vault>/.squirrel/incoming/`, or you can pass `--from-file <path>`.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `/sq-capture` writes to the wrong project | Auto-detection picked the wrong tag | Re-run with `--project=<TAG>` explicit |
| `/sq-brief` says "No intents found" | Project has no captured state yet | Run `/sq-capture` a few times, or `/sq-end` once, then retry |
| `/sq-brief --email` doesn't open a mailto draft | Your OS has no default `mailto:` handler | Pick option `b` (clipboard) instead |
| Pasted email triggers `sync-in` by accident | Email body contained the literal string `<!-- SQUIRREL-PACKAGE` | Edit it out, or run `/sq-capture` directly with the body inline |
| Web UI doesn't show the new note | Web server was started before the file existed | The home page auto-refreshes; on project pages, click the refresh icon top-right |

---

## See also

- [Everyday Use](everyday-use.md) — the five commands you'll use daily (`/sq-capture` is one of them).
- [Two Computers](two-computers.md) — the full sync-out / sync-in protocol with marker formats and hash validation.
- [Power User](power-user.md) — advanced flags, multi-vault routing, custom tag schemes.
