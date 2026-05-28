# Web UI — Browser Interface for Non-Technical Users

> 🎯 *What you'll learn:* How to start and use Squirrel's local browser interface. No terminal, no Markdown, no slash commands needed. Designed for anyone who prefers a visual web interface — partners, family members, or anyone who wants a modern app feel.

**Version:** Squirrel v0.5.0  
**Last updated:** 2026-05-25  
**Reading time:** ~18 minutes

---

## Table of Contents

1. [What the Web UI is](#what-the-web-ui-is)
2. [Start & stop](#start--stop)
3. [Dashboard — your home screen](#dashboard--your-home-screen)
4. [List view — all projects](#list-view--all-projects)
5. [Kanban board — visual status](#kanban-board--visual-status)
6. [Project detail — 4 tabs](#project-detail--4-tabs)
7. [Create a project](#create-a-project)
8. [Delete a project](#delete-a-project)
9. [Add a note or capture](#add-a-note-or-capture)
10. [Search](#search)
11. [Reminders (macOS)](#reminders-macos)
12. [Keyboard shortcuts](#keyboard-shortcuts)
13. [Auto-start on macOS](#auto-start-on-macos)
14. [Optional AI features](#optional-ai-features)
15. [Security & privacy](#security--privacy)
16. [Troubleshooting](#troubleshooting)

---

## What the Web UI is

A local, browser-based interface for your Squirrel vault. It runs a small Python server on your machine (`localhost:3939`) and serves a React single-page app — no internet, no cloud, no login.

**Who it's for:** Anyone who prefers clicking over typing slash commands. Your spouse, a parent, a non-technical teammate, or just you on the days you want a visual overview.

**What it replaces:** The need to know slash commands or Obsidian. Open a browser → see your projects → manage them.

**What it doesn't replace:** The slash commands and CLI still work exactly as before. The web UI is additive — it reads and writes the same vault files, so changes made in the browser are immediately visible in `/sq-status`, Obsidian, etc.

```
Browser                  Web UI server           Your vault (same files)
──────                   ─────────────           ──────────────────────
Click "New project"  ──► POST /api/projects  ──► Creates folder + README.md
Drag card to "Done"  ──► PATCH /api/status   ──► Updates project frontmatter
Add a note           ──► POST /api/note      ──► Appends to notes.md
```

---

## Start & stop

### Start

```bash
squirrel web start
```

Output:
```
🌐 Web UI running on http://127.0.0.1:3939
```

Open `http://localhost:3939` in your browser. That's it.

**Or, one command to start + open browser:**

```bash
squirrel web open
```

### Other server commands

```bash
squirrel web status        # Show "running on :3939" or "not running"
squirrel web stop          # Stop the server
squirrel web restart       # Restart (useful after config changes)
squirrel web uninstall     # Remove server + launchd plist (vault untouched)
```

**Custom port:**

```bash
squirrel web start --port 4040
# UI is now at http://localhost:4040
```

**LAN access (for iPad on the same Wi-Fi):**

```bash
squirrel web start --lan
# ⚠️ Warning: binding to 0.0.0.0 — only use on a trusted network
# UI is now at http://192.168.1.x:3939
```

---

## Dashboard — your home screen

When you open `http://localhost:3939` you see your **dashboard** — one screen that tells you everything at a glance.

```
┌────────────────────────────────────────────────────────────────┐
│  🌙  Squirrel                        [🔍 Search]  [+ New]     │
│                                      [Personal ▼]              │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  STATUS OVERVIEW                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │  ACTIVE  │  │ BLOCKED  │  │ ON HOLD  │  │   DONE   │      │
│  │    4     │  │    1     │  │    2     │  │    7     │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
│                                                                 │
│  TODAY'S FOCUS                                                 │
│  ├─ WORK-PROJECT-A — open test, line 47                       │
│  └─ VISA-APPLICATION — call embassy by 3 PM                   │
│                                                                 │
│  DUE SOON                                                      │
│  ├─ 🔴 VISA-APPLICATION — Today (embassy call)                │
│  ├─ 🟠 WORK-PROJECT-A — Tomorrow (code review)               │
│  └─ 🟡 SIDE-BLOG — This week (publish draft)                 │
│                                                                 │
│  [+ Add a note]                 [View list]  [View board]      │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

**Status counters** — one box per status, number of projects in each. Click any counter to filter the list to that status.

**Today's Focus** — the `next physical action` from your most recent `/sq-end` shutdown note per active project.

**Due Soon** — deadlines grouped by urgency (Today / Tomorrow / This week), colour-coded.

**Directory selector** — top-right dropdown. If you have "Personal" and "Work" vaults configured, you switch between them here. If you have only one, this dropdown is hidden.

---

## List view — all projects

Click **"View list"** on the dashboard (or `All Projects` in the sidebar) to see every project as a card:

```
┌─────────────────────────────────────────────────────────┐
│  All Projects                         [🔍 Search...]    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  WORK-PROJECT-A                                 │   │
│  │  Payment service refactor                       │   │
│  │                                                 │   │
│  │  [🔵 Active]  [Platform change]  [/Personal]   │   │
│  │                                                 │   │
│  │  ⚠️ 0 blockers   📅 Deadline: 2026-05-30       │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  VISA-APPLICATION                               │   │
│  │  Family visa renewal 2026                      │   │
│  │                                                 │   │
│  │  [🟠 Blocked]  [Regulatory]  [/Personal]       │   │
│  │                                                 │   │
│  │  ⚠️ 1 blocker   📅 Deadline: 2026-06-01        │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

Each card shows:
- **Project ID and human name**
- **Status badge** — colour-coded (blue = active, orange = blocked, grey = on hold, green = done)
- **Type badge** — what kind of work it is
- **Directory badge** — which vault it's in (only if 2+ vaults configured)
- **Blocker count** — red warning if blockers exist
- **Deadline** — the next hard date

Click any card to open that project's detail view.

---

## Kanban board — visual status

Click **"View board"** on the dashboard to see the **Kanban view** — all projects as draggable cards across status columns:

```
┌────────────┬─────────────┬─────────────┬────────────┬────────────┐
│  IDEA (1)  │ PLANNING (2)│ ACTIVE (4)  │BLOCKED (1) │  DONE (7)  │
├────────────┼─────────────┼─────────────┼────────────┼────────────┤
│            │             │             │            │            │
│ ┌────────┐ │ ┌─────────┐ │ ┌─────────┐ │ ┌────────┐ │ ┌────────┐ │
│ │SIDE-   │ │ │TAXES-   │ │ │WORK-    │ │ │VISA-   │ │ │TRIP-   │ │
│ │PODCAST │ │ │2026     │ │ │PROJECT-A│ │ │APPLIC. │ │ │JAPAN   │ │
│ │        │ │ │         │ │ │         │ │ │        │ │ │        │ │
│ │[Idea]  │ │ │⏳No ddl │ │ │📅May 30 │ │ │⚠️1blk  │ │ │✅ Done │ │
│ └────────┘ │ └─────────┘ │ └─────────┘ │ └────────┘ │ └────────┘ │
│            │             │             │            │            │
│            │             │ ┌─────────┐ │            │ ┌────────┐ │
│            │             │ │SIDE-BLOG│ │            │ │TRIP-   │ │
│            │             │ │         │ │            │ │JAPAN-  │ │
│            │             │ │📅Jun 01 │ │            │ │2025    │ │
│            │             │ └─────────┘ │            │ └────────┘ │
│            │             │             │            │            │
│  [Empty]   │             │ ┌─────────┐ │  [Empty]   │            │
│            │             │ │FREELANCE│ │            │            │
│            │             │ │-CLIENT-A│ │            │            │
│            │             │ │📅Jun 14 │ │            │            │
│            │             │ └─────────┘ │            │            │
└────────────┴─────────────┴─────────────┴────────────┴────────────┘
```

### Drag to change status

Drag any project card from one column to another to update its status:

```
Drag VISA-APPLICATION from "BLOCKED" → drop on "ACTIVE"
✅ Status updated: VISA-APPLICATION is now Active
   (This writes to VISA-APPLICATION/README.md immediately)
```

The change is saved to the vault file instantly. Open `VISA-APPLICATION/README.md` in Obsidian and you'll see the updated `status:` field.

### Column meanings

| Column | Status | When to use |
|---|---|---|
| **Idea** | `idea` | Captured but not started yet |
| **Planning** | `in-discovery` | Researching or planning, not coding yet |
| **Active** | `in-progress` | Currently working on it |
| **Blocked** | `blocked` | Waiting on someone or something |
| **Done** | `delivered` | Finished and closed |

---

## Project detail — 4 tabs

Click any project card (from list or board view) to open its detail page. You'll see **4 tabs**:

```
┌──────────────────────────────────────────────────────────────┐
│  ← Back      WORK-PROJECT-A — Payment service refactor       │
│                                                              │
│  [Overview]  [Notes]  [Comms]  [Links]                      │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  (content of selected tab here)                              │
│                                                              │
│  [✏️ Edit]  [+ Add note]  [🗑️ Delete project]               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Tab 1: Overview

Shows the project's main info — status, type, deadline, owner, milestones, blockers, sign-offs. Rendered from `README.md`, displayed in plain readable format (no raw Markdown visible).

```
Project: WORK-PROJECT-A
Status:  Active
Type:    Platform change
Deadline: 2026-05-30

Milestones:
  ☐ Implement payment retry logic
  ✅ Write unit tests
  ☐ Code review
  ☐ Deploy to staging

Blockers:
  None

Sign-offs needed:
  ☐ Tech lead review
  ☐ Security review
```

Click **[✏️ Edit]** to open a plain textarea and edit the content.

### Tab 2: Notes

An append-only decision log — every note has a date stamp. Newest first.

```
── 2026-05-24 17:00 ──
Completed payment retry logic. Tests passing (3/3).
Next: write edge-case tests for timeout and invalid card scenarios.

── 2026-05-23 11:30 ──
Decided to use SQLite for MVP instead of PostgreSQL.
Rationale: faster to ship, can migrate later if product sells.

── 2026-05-20 09:00 ──
Started the auth refactor.
```

Click **[+ Add note]** to append a new entry. Date is added automatically — you just type the text.

### Tab 3: Comms

A log of all communications related to this project — Slack messages, emails, meeting notes.

```
┌────────────┬───────────────────────────┬──────────────────────────┐
│ Date       │ Channel                   │ Context                  │
├────────────┼───────────────────────────┼──────────────────────────┤
│ 2026-05-24 │ Slack                     │ Kickoff with Risk team   │
│            │ [link]                    │                          │
├────────────┼───────────────────────────┼──────────────────────────┤
│ 2026-05-21 │ Email                     │ Client approved scope    │
│            │ [link]                    │                          │
└────────────┴───────────────────────────┴──────────────────────────┘
```

Click **[+ Log communication]** to add a new row — channel, link, and context.

### Tab 4: Links

External references — Jira tickets, Google Docs, GitHub PRs, design files.

```
• Jira epic: [PAYMENT-123] https://jira.company.com/...
• Design doc: https://docs.google.com/...
• GitHub PR: #42 https://github.com/...
```

Click **[✏️ Edit]** to add, remove, or update links.

### Keyboard navigation between tabs

While inside a project detail:

| Shortcut | Action |
|---|---|
| `Ctrl/Cmd + 1` | Switch to Overview tab |
| `Ctrl/Cmd + 2` | Switch to Notes tab |
| `Ctrl/Cmd + 3` | Switch to Comms tab |
| `Ctrl/Cmd + 4` | Switch to Links tab |
| `Esc` | Go back to list/board |

---

## Create a project

Click the **[+ New]** button in the top-right header (or press `Ctrl/Cmd+N` from anywhere) to open the **New Project** form:

```
┌──────────────────────────────────────────────────────┐
│  New Project                                    [✕]  │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Project ID *                                        │
│  ┌────────────────────────────────────────────────┐  │
│  │ WORK-PROJECT-B                                 │  │
│  └────────────────────────────────────────────────┘  │
│  Format: ALL-CAPS with hyphens (e.g. SIDE-BLOG)      │
│                                                      │
│  Project Name *                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │ Checkout payment flow                          │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  Type                                                │
│  ┌────────────────────────────────────────────────┐  │
│  │ Platform change                           ▼    │  │
│  └────────────────────────────────────────────────┘  │
│  (Discovery / PoC / Platform change / Growth / Infra)│
│                                                      │
│  Target Deadline                                     │
│  ┌────────────────────────────────────────────────┐  │
│  │ 2026-06-14                                     │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  Workspace                                           │
│  ┌────────────────────────────────────────────────┐  │
│  │ Personal                                  ▼    │  │
│  └────────────────────────────────────────────────┘  │
│  (only shown if 2+ workspaces configured)            │
│                                                      │
│  [Cancel]                         [Create project]   │
│                                                      │
└──────────────────────────────────────────────────────┘
```

**What happens when you click "Create project":**

1. Squirrel creates a folder: `01-Proyectos-Activos/WORK-PROJECT-B/`
2. Inside it, creates four files: `README.md`, `notes.md`, `comms.md`, `links.md`
3. Fills `README.md` with the metadata you provided (ID, name, type, deadline)
4. Redirects you to the new project's detail page (Overview tab)

The project is now visible in `/sq-status`, `/sq-where-am-i`, and Obsidian.

**💡 Tip:** You don't need to fill in every field. Only ID and Name are required. You can edit the rest later from the Overview tab.

**⚠️ Validation:** If the Project ID already exists, the form shows an error: "This ID is already taken. Choose a different one."

---

## Delete a project

Open any project's detail page. In the bottom bar, click **[🗑️ Delete project]**.

A confirmation dialog appears:

```
┌──────────────────────────────────────────────────────┐
│  ⚠️ Delete project?                            [✕]  │
├──────────────────────────────────────────────────────┤
│                                                      │
│  You are about to permanently delete:                │
│                                                      │
│      WORK-PROJECT-B                                  │
│      "Checkout payment flow"                         │
│                                                      │
│  This will delete:                                   │
│    • README.md                                       │
│    • notes.md (3 entries)                            │
│    • comms.md (1 entry)                              │
│    • links.md (2 links)                              │
│                                                      │
│  ⚠️ This cannot be undone from the web UI.          │
│     If you use Git, the files will be in history.   │
│                                                      │
│  Type the project ID to confirm:                     │
│  ┌────────────────────────────────────────────────┐  │
│  │                                                │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  [Cancel]                         [Delete forever]   │
│  (disabled until you type the ID correctly)          │
│                                                      │
└──────────────────────────────────────────────────────┘
```

**You must type the exact project ID to enable the "Delete forever" button.** This prevents accidental deletion.

After deletion:
- The project folder is removed from the vault
- You're redirected to the project list
- The project disappears from `/sq-status` and `/sq-where-am-i`
- If you use Git, the files remain in your commit history and can be recovered

**💡 Alternative to deletion — Archive:** If you just finished a project, consider moving it to `04-Archivo/` instead of deleting it. Archived projects are hidden from your active views but their history is preserved. You can do this by dragging the card to the "Done" column on the Kanban board, or by editing the status in the Overview tab.

---

## Add a note or capture

The **[+ Add a note]** button appears in:
- The dashboard (always visible)
- Any project detail page
- The header (small `+` icon)

Click it to open the capture modal:

```
┌──────────────────────────────────────────────────────┐
│  Add a note                                    [✕]  │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │ Call embassy at 3 PM — ask about extra docs    │  │
│  │ required for 2026 renewal                      │  │
│  │                                                │  │
│  └────────────────────────────────────────────────┘  │
│  (cursor starts here automatically)                  │
│                                                      │
│  Project                                             │
│  ┌────────────────────────────────────────────────┐  │
│  │ VISA-APPLICATION                          ▼    │  │
│  └────────────────────────────────────────────────┘  │
│  (pre-filled if you're on a project page)            │
│  (defaults to "Unfiled" if on dashboard)             │
│                                                      │
│  [Cancel]                               [Add note]   │
│                                                      │
└──────────────────────────────────────────────────────┘
```

The note is saved with an automatic date stamp and appears in the project's **Notes tab** immediately. It's also visible as a capture file in the vault, readable by `/sq-where-am-i`.

**Unfiled notes** (if you don't pick a project) land in `03-Recursos/Captures/UNFILED-NNN.md`. You can move them to a real project later from Obsidian or by editing the file.

---

## Search

### Quick search (`Ctrl/Cmd+K`)

Press `Ctrl+K` (Mac: `Cmd+K`) from anywhere in the UI to open the search bar. Results update in real-time as you type:

```
┌──────────────────────────────────────────────────────┐
│  🔍 Search projects and notes...            [Esc]   │
├──────────────────────────────────────────────────────┤
│  > payment                                           │
├──────────────────────────────────────────────────────┤
│  WORK-PROJECT-A — "payment retry logic"             │
│    Note: 2026-05-24 — "Completed payment retry..."  │
│                                                      │
│  WORK-PROJECT-B — "Checkout payment flow"           │
│    Overview: "...payment service refactor..."       │
└──────────────────────────────────────────────────────┘
```

The search spans:
- Project names and IDs
- All notes (dated entries)
- All communications
- All linked URLs

Press `Enter` on a result to open that project. Press `Esc` to close.

### Filter the list view

In the list view, use the filter bar to narrow by:
- **Status** — Active / Blocked / On Hold / Done / All
- **Type** — Discovery / Platform change / Growth / etc.
- **Directory** — Personal / Work (if 2+ configured)
- **Has blockers** — checkbox to show only blocked projects

---

## Reminders (macOS)

Squirrel's web UI integrates with the macOS reminder daemon. When active, it fires native dialogs on a schedule (default: every 2 hours during work hours) showing you which projects need attention.

### Install the reminder daemon

```bash
./scripts/manage.sh install-reminders
```

Or from the web UI: **Settings → Reminders → Enable**.

### What a reminder looks like

A native macOS dialog appears:

```
┌──────────────────────────────────────────────────────────┐
│  🐿️ Squirrel Reminder                                    │
│                                                          │
│  VISA-APPLICATION — Family visa renewal 2026            │
│                                                          │
│  Checklist:                                              │
│  • Review initiative status and update if needed        │
│  • Check for new blockers or risks                      │
│  • Follow up on pending communications                  │
│  • Update milestone progress                            │
│                                                          │
│  [✅ Done]    [⏰ Snooze 30 min]    [✕ Dismiss]         │
└──────────────────────────────────────────────────────────┘
```

| Action | Effect |
|---|---|
| **Done** | Marks reminder complete, appends `[REMINDER]` entry to `notes.md` |
| **Snooze** | Suppresses for 30 min (configurable) |
| **Dismiss** | Silences for 24 hours |

### Workday settings

The daemon respects work hours — no dialogs on weekends or outside your configured hours:

```json
"reminders": {
  "workdayStart": "09:00",
  "workdayEnd": "18:00",
  "workdays": [1, 2, 3, 4, 5],
  "cadenceMinutes": 120,
  "maxDialogsPerDay": 8
}
```

Edit these in `config.json` (or through **Settings → Reminders** in the web UI).

### Uninstall

```bash
./scripts/manage.sh uninstall-reminders
```

Or from the web UI: **Settings → Reminders → Disable**.

---

## Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl/Cmd+K` | Open search |
| `Ctrl/Cmd+N` | New project form |
| `Ctrl/Cmd+1` | Switch to Overview tab (in project detail) |
| `Ctrl/Cmd+2` | Switch to Notes tab |
| `Ctrl/Cmd+3` | Switch to Comms tab |
| `Ctrl/Cmd+4` | Switch to Links tab |
| `Esc` | Close modal / clear search / go back |

---

## Auto-start on macOS

Install a LaunchAgent so the web server starts automatically when you log in:

```bash
bash companions/web-ui/launchd/install.sh
```

Remove it:

```bash
bash companions/web-ui/launchd/install.sh --uninstall
```

After installing, open your browser bookmark `http://localhost:3939` any time — the server is always running in the background.

---

## Optional AI features

If you add an Anthropic API key to `~/.squirrel/config.toml`:

```toml
[ai]
provider = "anthropic"
api_key = "sk-ant-..."
model = "claude-sonnet-4-6"
```

Three AI buttons appear:

### "Generate brief" (project detail)

On any project page, a **"✨ Generate brief"** button appears. Click it → AI reads your project's overview, notes, and communications → produces a 6-section brief → you can save it as a note or copy to clipboard.

```
📊 Brief: WORK-PROJECT-A

🎯 What I'm doing: Implementing payment retry logic with exponential backoff.
✅ Done: Unit tests for error cases (3/3 passing)
🎬 Next: Edge case tests for timeout scenarios
🧠 Decisions: SQLite for MVP, migrate to PostgreSQL post-launch
🚦 Steps: 1) Write 3 more tests 2) Code review 3) Deploy to staging
🚧 Open questions: Should retry delay be configurable by client?
```

### "Help me decide" (add note modal)

When adding a note, a **"Help me decide"** button appears. Click → multi-step AI wizard:
1. You describe the decision
2. AI asks 1–2 clarifying questions
3. Final result is a structured decision note saved to the project

### "Help me start" (dashboard, when nothing is in focus)

When your "Today's Focus" is empty, a **"Help me start"** button appears. Click → AI looks at all active projects and their last activity → suggests one concrete action: "Open WORK-PROJECT-A, write the timeout test at line 47."

**Without an API key:** None of these buttons appear. The product works 100% without AI.

---

## Security & privacy

- **Localhost only by default** — binds `127.0.0.1`. Only apps on your machine can reach it.
- **LAN access** — `--lan` flag binds `0.0.0.0`. Use only on a network you trust.
- **No login required** — mitigated by localhost binding. You're the only user.
- **No internet calls** — the server makes zero outbound requests unless you configure AI.
- **Atomic file writes** — every save goes through a temp file + atomic replace. Safe against crashes mid-write.
- **No telemetry** — nothing is ever sent anywhere.

---

## Troubleshooting

### "Server not found" / blank page

```bash
squirrel web status
# Should say "running on http://127.0.0.1:3939"

# If not running, start it:
squirrel web start
```

If it still fails, check the log:
```bash
cat ~/.squirrel/web-ui.log
```

### Port already in use

```bash
squirrel web start --port 4040
# Then open http://localhost:4040
```

### iPad shows blank page

Make sure you started with `--lan` and both devices are on the same Wi-Fi:

```bash
squirrel web start --lan
# Then navigate to http://192.168.1.x:3939 on your iPad
# (Find the local IP with: ipconfig getifaddr en0)
```

### Project I just created doesn't appear in `/sq-status`

The vault files are written immediately, but `/sq-status` reads the active project list from `config.toml`. Add the new project ID to the `active` list in `~/.squirrel/config.toml`:

```toml
[projects]
active = ["WORK-PROJECT-A", "WORK-PROJECT-B"]  # ← add new ID here
```

Then run `/sq-status` again.

### AI buttons don't appear

1. Confirm `[ai]` section exists in `~/.squirrel/config.toml`
2. Check the API key is valid (test with `curl https://api.anthropic.com/...`)
3. Restart the server: `squirrel web restart`

### Delete button doesn't activate

You need to type the **exact** project ID in the confirmation field (case-sensitive). The button stays disabled until it matches.

---

## Where to go next

- **New to Squirrel?** → Read [First Setup](./first-setup.md) and [First 10 Minutes](./first-10-minutes.md) — the web UI is a supplement to the core loop, not a replacement.
- **Want slash commands?** → [Everyday Use](./everyday-use.md) covers the 5 core commands.
- **Two computers?** → [Two Computers](./two-computers.md) — sync between home and work (stays in CLI, not web UI by design).
- **Want encryption or advanced features?** → [Power User](./power-user.md).

The web UI is designed so non-technical users can use Squirrel without learning any of the above. Both paths lead to the same vault. 🐿️
