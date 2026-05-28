# Squirrel — User Guide (Ages 10–60)

> A friendly, plain-English walkthrough — from "what is this?" all the way to advanced workflows. Read top to bottom if you're new, or jump to the section you need.

**Version:** Squirrel v0.5.0
**Last updated:** 2026-05-24
**Reading time:** ~25 minutes (or 5 minutes if you skim)

---

## Table of Contents

0. [Welcome — What is Squirrel?](#0-welcome--what-is-squirrel)
1. [Before You Start](#1-before-you-start)
2. [Install Squirrel](#2-install-squirrel)
3. [First Setup](#3-first-setup)
4. [Your First 10 Minutes](#4-your-first-10-minutes)
5. [Working with multiple workspaces](#5-working-with-multiple-workspaces)
6. [Everyday Use (Basic)](#6-everyday-use-basic)
7. [Using Squirrel in a browser](#7-using-squirrel-in-a-browser)
8. [Working Smarter (Intermediate)](#8-working-smarter-intermediate)
9. [Two Computers (Advanced)](#9-two-computers-advanced)
10. [Power User (Advanced overview)](#10-power-user-advanced-overview)
11. [When Things Go Wrong](#11-when-things-go-wrong)
12. [Cheat Sheet — every command on one page](#12-cheat-sheet)
13. [Glossary — plain-English definitions](#13-glossary)

---

## 0. Welcome — What is Squirrel?

> 🎯 *What you'll learn:* What this tool does, who it's for, and why it has a funny name.

### The squirrel story

Imagine a squirrel that buries nuts (its food) in many different spots around a park. Without help, it forgets where it hid them. A whole winter's worth of food — gone.

You are the squirrel. The "nuts" are your **projects, ideas, decisions, and notes**. The "park" is your computer, your work, your side-projects, your homework, your visa paperwork, your blog.

**Squirrel-the-tool** is the helper that remembers for you. It lives in small text files on your computer (not in the cloud), and when you sit down to work it tells you:

> *"Yesterday you were working on Project A. You stopped because you were stuck on a bug. The next thing to try is on line 47 of `auth.ts`."*

That's it. That's the whole idea.

### Who is this for?

- **Anyone who juggles a lot at once** — work projects, family stuff, school assignments, hobbies
- **Anyone with ADHD** (it was built for ADHD brains first), but useful for everyone
- **People who use AI assistants** like Claude Code, Codex, or Cursor and want them to *remember* things between conversations
- **People who need to keep work and personal stuff separate** — e.g., research at home, apply at work, never mix the two automatically

### What is it not?

- It is **not a calendar** (use Google Calendar)
- It is **not a chat app** (use Slack/Discord)
- It is **not in the cloud** — your notes stay on your computer
- It is **not an AI itself** — it's a helper that *talks to* AI assistants

### How does it work, in one picture?

```
   You                  Squirrel               Your AI assistant
  -----                -----------             ------------------
   "What was I    ─►   reads your    ─►       answers in plain
    doing?"            note files              English with your
                                               actual context
```

---

## 1. Before You Start

> 🎯 *What you'll learn:* The three things you need on your computer before installing Squirrel. Each one has a "how do I check?" command.

### Check #1 — Do you have Python?

Squirrel uses **Python** (a popular programming language) to do its quiet background work. You need version **3.9 or higher**.

Open your **terminal** (a black-and-white text window — on Mac it's called *Terminal*, on Windows it's *PowerShell* or *Command Prompt*) and type:

```bash
python3 --version
```

**What a good answer looks like:**
```
Python 3.11.5
```

(Any number starting with 3.9, 3.10, 3.11, 3.12, etc. is fine.)

**If you get "command not found":** Install Python from [python.org](https://www.python.org/downloads/). Pick the "latest stable release". On Mac, you can also run `brew install python3` if you have Homebrew.

### Check #2 — Do you have a text editor?

Your notes will be plain text files (the same kind a `.txt` file is, but with a `.md` ending — see *Markdown* in the [Glossary](#13-glossary)). Any of these work:

- **Obsidian** (free, recommended — it understands the note format beautifully): [obsidian.md](https://obsidian.md)
- **VSCode** (free, popular with coders): [code.visualstudio.com](https://code.visualstudio.com)
- **Logseq** (free, similar to Obsidian)
- **Notepad** (built into Windows), **TextEdit** (built into Mac)

You don't *need* a fancy editor — but Obsidian makes the notes look much nicer.

### Check #3 — Do you have an AI assistant?

Squirrel works with several AI coding assistants. Pick **one**:

- **Claude Code** (recommended — best support): [claude.com/claude-code](https://claude.com/claude-code)
- **Codex CLI** (OpenAI's coding terminal)
- **Cursor** (an AI-powered code editor): [cursor.com](https://cursor.com)

If you don't have any of these yet, install **Claude Code** — the rest of this guide assumes it.

💡 *Tip:* You can use Squirrel **without** an AI assistant — there's a built-in terminal command called `squirrel` (see [Section 10](#10-power-user-advanced-overview)). But the AI integration is where it really shines.

---

## 2. Install Squirrel

> 🎯 *What you'll learn:* How to copy Squirrel onto your computer so your AI assistant can find it. Takes about 2 minutes.

### Option A — Claude Code (recommended path)

**Step 1.** Open your terminal and copy the Squirrel folder into Claude Code's plugin directory:

```bash
cp -r /path/to/squirrel ~/.claude/plugins/
```

Replace `/path/to/squirrel` with where you downloaded this project. If you cloned with `git`, it'll be something like `~/projects/adhd-context-bridge` or `~/others/ai-agents/adhd-context-bridge`.

💡 *Tip:* If you want updates from the project to be picked up automatically, use a **symlink** instead of a copy:

```bash
ln -s /path/to/squirrel ~/.claude/plugins/squirrel
```

**Step 2.** Close Claude Code completely and open it again. (Plugins are loaded at startup.)

**Step 3.** Verify it worked. Inside Claude Code, type:

```
/plugin list
```

You should see `squirrel v0.5.0` in the list. ✅

If you don't see it, jump to [Section 11 — When Things Go Wrong](#11-when-things-go-wrong).

### Option B — Codex CLI

```bash
mkdir -p ~/.codex/skills ~/.codex/commands
cp -r squirrel/skills/* ~/.codex/skills/
cp squirrel/commands/*.md ~/.codex/commands/
```

Then add a short note to your `~/.codex/AGENTS.md` file telling Codex these skills exist — see `INSTALL.md` in the project for the exact wording.

### Option C — Cursor / VSCode

```bash
mkdir -p ~/.cursor/rules/squirrel
cp -r squirrel/skills/* ~/.cursor/rules/squirrel/
```

Then in *Cursor → Settings → Rules for AI*, paste:

```
Use ~/.cursor/rules/squirrel/ for managing project context, shutdown notes,
and cross-environment transfers. See SKILL.md files in each subdirectory.
```

---

## 3. First Setup

> 🎯 *What you'll learn:* How to tell Squirrel where your notes will live and what your projects are. This is a one-time thing.

### The `/sq-init` command

Inside your AI assistant (e.g., Claude Code), type:

```
/sq-init
```

It will ask you four questions. Here's what each one means, in plain English:

| Question | What it's asking | Example answer |
|---|---|---|
| `vault_path` | Where on your computer should Squirrel keep your notes? | `~/vault-tdah` (the default) or `~/Documents/my-notes` |
| `environment_name` | A short label for *this* computer | `personal` (or `work`, or `laptop`) |
| `default_email` | Your email — used only when generating draft emails | `you@example.com` |
| `active_projects` | A comma-separated list of project codes you're working on right now | `TAXES-2026,BLOG-SIDE,VISA-FAMILY` |

💡 *Tip on project codes:* Make them ALL-CAPS with dashes, no spaces. Good examples:
- `WORK-PROJECT-A`
- `SCHOOL-MATH-HW`
- `SIDE-BLOG`
- `TRIP-JAPAN-2026`
- `TAXES-2026`

### What `/sq-init` creates

After you answer, Squirrel:

1. Writes a settings file at `~/.squirrel/config.toml` (you can read or edit it anytime)
2. Creates the four main folders inside your vault (the *PARA system* — see [Glossary](#13-glossary)):
   - `01-Proyectos-Activos/` — Active projects you're working on now
   - `02-Areas/` — Long-term areas (e.g., "Health", "Finance")
   - `03-Recursos/` — Reference material (e.g., articles you saved)
   - `04-Archivo/` — Old projects you've finished
3. Creates a demo project so you can see how it looks: `DEMO-INICIO/`
4. Asks if you want to install pretty Obsidian dashboards (say yes if you use Obsidian)

✅ When it's done, run `/sq-where-am-i` — it should show your active projects with the demo entry.

---

## 4. Your First 10 Minutes

> 🎯 *What you'll learn:* You'll capture a note, start a work session, and end it — proving the whole loop works. By the end you'll have files on your disk and know what they look like.

We're going to pretend you're working on a small project called `MY-BLOG`. Follow along.

### Minute 1–2: Make a note about an idea

```
/sq-capture I want to write a blog post about how I use Squirrel
```

**What you'll see:** Squirrel asks which project this belongs to (or guesses from your config), then creates a file like:

```
~/vault-tdah/99-Resources/Captures/MY-BLOG-NOTES-001.md
```

Open the file in your editor. You'll see something like:

```markdown
---
id: MY-BLOG-NOTES-001
proyecto: MY-BLOG
tipo: capture
creado: 2026-05-24
tags: [capture, proyecto/MY-BLOG]
---

# Idea: blog post about Squirrel

I want to write a blog post about how I use Squirrel.
```

The block at the top between the `---` lines is called **frontmatter** ([Glossary](#13-glossary)) — it's how Squirrel keeps track of what kind of note this is.

### Minute 3–6: Start a work session

```
/sq-start MY-BLOG
```

**What you'll see:** Squirrel reads everything it knows about `MY-BLOG` and writes a short "loading note" — about 200 words — that tells you:

- What you were working on
- The last thing you did
- The very next physical action to take (e.g., "open file X line 47")
- Anything that's blocking you

For a brand-new project, the loading note is short:

```
📋 MY-BLOG — fresh start, no prior context

You don't have any prior intents or shutdown notes for this project.
Suggested first action: capture the outline of your first post.

Run /sq-capture <your outline> to begin.
```

### Minute 7–9: Pretend to "work" for a bit

Just type a few things in the chat — even casual notes. For example:

```
The post should have three sections: why I started, the install steps,
and the first week of using it.
```

The AI assistant remembers this as part of the conversation.

### Minute 10: End the session

```
/sq-end
```

**What you'll see:** Squirrel writes a *shutdown note* — a short summary of what just happened — and saves it under `MY-BLOG`. Then it asks: "Do you want to commit to git?" Say no for now if you're not using git.

✅ You did it! Open your vault folder and look at the new files. You now have:

- A capture note (the idea you saved)
- A shutdown note (what you "did")
- A project page (auto-created when you ran `/sq-start`)

**You now know the entire core loop:** capture → start → work → end. The rest of this guide is just more tools for the same loop.

---

## 5. Working with multiple workspaces

> 🎯 *What you'll learn:* When and how to keep more than one vault — useful for separating personal from work, or for client A from client B. Most people skip this section on day one and come back later. That's fine.

### When to use multiple vaults

A **vault** is the folder where Squirrel keeps your notes (the one you picked during `/sq-init`). For most people, **one vault is enough**.

Reach for a second vault when you have material that genuinely cannot mix:

- **Personal vs. work** — your home blog idea has no business living in the same folder as a client's confidential ticket.
- **Client A vs. client B** — two consulting engagements that must not see each other.
- **Public vs. private** — a vault you'd share or publish vs. one that stays local-only.

If you're just organising *topics* (Health, Finance, Hobbies), use **projects** inside one vault instead — that's what the PARA folders are for. Multiple vaults are about **trust boundaries**, not topical filing.

### What changed in v0.6

Up through v0.5, `~/.squirrel/config.toml` had a single `vault_path = ...` line. From v0.6 onward, it has an array of vault entries — any one of them can be the default. The new schema looks like this:

```toml
machine_environment = "personal"   # was: environment_name

[[vaults]]
name = "personal"
path = "~/vault-tdah"
default = true

[[vaults]]
name = "work"
path = "~/work-vault"
default = false
```

**Migration is automatic.** If you upgraded from v0.5 and your config still has the old `vault_path` line, Squirrel rewrites it the next time *any* command reads the file. You'll notice a `# Auto-migrated <date>` comment as the first line — that's the only visible artifact. You do **not** need to run a migration command. Running it twice does nothing extra.

### Managing vaults from the terminal

The `squirrel vaults` subcommand group handles the day-to-day:

```bash
squirrel vaults list                     # show every configured vault, with the default marked
squirrel vaults add work ~/work-vault    # add a new vault entry
squirrel vaults default work             # make 'work' the default
squirrel vaults remove personal          # remove a vault entry (files untouched)
```

Validation lives inside Squirrel — for example, you can't remove the default vault without first picking a different default, and you can't add a path that doesn't exist on disk.

### Adding a vault from Claude Code

Inside your AI assistant, type:

```
/sq-init --add-vault
```

It asks for the new vault's name, path, and whether to set it as the default — then writes the entry. The plain `/sq-init` (no flag) still runs the original one-time setup; the `--add-vault` flow is only for adding to an already-configured machine.

### Pointing a command at a specific vault

Once you have more than one vault, every vault-touching command (`squirrel status`, `squirrel deadlines`, `squirrel recover`, `squirrel dashboard`) and every vault-touching slash command (`/sq-status`, `/sq-deadlines`, `/sq-where-am-i`, `/sq-start`, `/sq-end`, `/sq-capture`, `/sq-brief`, `/sq-decision`, `/sq-recover`, `/sq-chunk-intent`, `/sq-task-initiation`, `/sq-parakeet`, `/sq-dashboard`, `/sq-sync-out`, `/sq-sync-in`) accepts an optional `--vault NAME`:

```bash
squirrel status --vault work             # what's open in the work vault
/sq-where-am-i --vault personal          # same, but from the AI assistant
```

Leave the flag off and Squirrel operates on the **default** vault — so single-vault users see no change at all. The vault-independent commands (`squirrel chunk`, `squirrel estimate`, `/sq-chunk`, `/sq-estimate`) don't take the flag because they don't touch any vault.

---

## 6. Everyday Use (Basic)

> 🎯 *What you'll learn:* The five commands that cover 80% of daily use. Memorize these.

### `/sq-capture <anything>` — Save an idea right now

**Use when:** an idea pops into your head and you don't want to forget it.

```
/sq-capture We should add caching to the login endpoint
/sq-capture Mom's birthday gift idea: a book on bonsai
/sq-capture The bug in the report is probably a timezone issue
```

Squirrel files it in the right project folder automatically (it looks at the wording).

### `/sq-start [PROJECT-TAG]` — Load a project's context

**Use when:** you sit down to work on something.

```
/sq-start WORK-PROJECT-A
```

You'll get a short briefing of "you were here, do this next."

If you don't include the tag, Squirrel asks: *"Which project?"*

### `/sq-end` — Save where you stopped

**Use when:** you're about to stop working — lunch, end of day, switching projects.

```
/sq-end
```

This is the **most important habit** in Squirrel. Future-you (or tomorrow-you) reads this note and instantly knows what to do next. Skip it, and tomorrow you'll spend 15 minutes re-discovering where you were.

⚠️ *Watch out:* If you forget to `/sq-end`, use `/sq-recover` later — see Section 8.

### `/sq-where-am-i` — "What was I doing?"

**Use when:** you sit down and have no idea what's going on.

```
/sq-where-am-i
```

You get a list of every project you're working on, how far along each one is, what was last touched, and one concrete suggestion for what to do today.

### `/sq-status` — Big-picture overview

**Use when:** you want a complete dashboard of everything.

```
/sq-status
```

You get:

- All active projects with progress percentages
- All projects on hold ("parking lot")
- All alerts (e.g., "no activity in 3 days")
- All urgent deadlines
- A recommended focus for today

This is what we call the *Monday-morning command*. Run it once a week minimum.

---

## 7. Using Squirrel in a browser

> 🎯 *What you'll learn:* How to open Squirrel in a regular web browser — useful when you don't have an AI assistant open, or when you'd rather tap than type slash commands. Especially handy on an iPad.

### When this helps

The browser interface is a **second way** to see and use Squirrel, alongside the AI assistant. Reach for it when:

- You're on your phone or iPad and don't want to open Claude / Codex / Cursor.
- A family member or partner wants to add a note without learning slash commands.
- You just want a quick visual check on what's pressing today.

It is **not** required. Everything still works in your AI assistant exactly as before.

### Install it (one command)

Inside the repo:

```bash
bash scripts/install-web-ui.sh
```

The script confirms you have Python 3.9 or newer, registers the `squirrel web` commands, and prints the URL. **No Node.js, no `npm install`, no build step** — it's pure Python from the standard library.

You can also tick the "Web UI (browser interface)" box when running `./install.sh`, or pass `--with-web-ui` to the non-interactive installer.

### Start, stop, open

```bash
squirrel web start        # start the server
squirrel web open         # open the page in your default browser
squirrel web status       # is it running?
squirrel web stop         # stop it when you're done
```

Default URL: **http://127.0.0.1:3939** (only on this computer — see safety below).

To start it automatically every time you log in on macOS:

```bash
bash companions/web-ui/launchd/install.sh
```

### What you can do in the browser

- **Home page** — today's focus, anything pressing, and your list of projects.
- **Project page** — the project's description, recent notes, an Edit button.
- **Note page** — read or edit any note (plain text, no Markdown rendering — keep it simple).
- **Deadlines** — grouped into "Today / Tomorrow", "This week", "Later".
- **History** — the 30 most-recently-touched things.
- **Settings** — switch between light/dark/auto, pick a workspace (only shows up if you have more than one), see the version.

There's always an **"Add a note"** button in the top bar. Tap it, type, save — the note lands in the right project folder (or in "Unfiled" if you don't pick one).

### Add to Home Screen (iPad)

In Safari on iPad, open the URL, tap **Share → Add to Home Screen**. The result behaves like an app: full-screen, its own icon, its own task.

### Safety notes

- **It only runs on your computer.** The URL `127.0.0.1` means "this machine and nothing else". Other people on your Wi-Fi cannot open it.
- **There's no password.** The point above is the reason. If your computer is unlocked, anyone sitting at it can use Squirrel via the browser — exactly the same as if they opened Obsidian or the terminal.
- **It doesn't send your data anywhere.** No telemetry, no cloud sync. Even the optional AI buttons only appear if you have set up an `[ai]` block in `~/.squirrel/config.toml` yourself.
- **To remove it completely:** run `squirrel web uninstall`. That stops the server, removes the auto-start (if you set one up), and cleans up the temp files. Your notes are untouched.

### Common questions

**"Can I use this from my phone over Wi-Fi?"** Not by default. You'd have to start the server with `--lan` and the server warns you in red that there is no password. Don't do this on a coffee-shop network.

**"Can I delete notes from the browser?"** No — by design. Deletion stays in Obsidian or the terminal so accidental taps can't lose work.

**"Can I rename a project here?"** No — same reason. Use Obsidian or your file manager.

**"Where are the logs?"** `~/.squirrel/web-ui.log`. It records only the time, request method, path, and HTTP status — nothing about the contents of your notes.

---

## 8. Working Smarter (Intermediate)

> 🎯 *What you'll learn:* The next five commands — for stakeholders, deadlines, and breaking big things down. Use these once or twice a week.

### `/sq-brief [PROJECT-TAG]` — Status report in 6 sections

**Use when:** your boss asks "where are you on X?" or you need a quick stand-up update.

```
/sq-brief WORK-PROJECT-A
```

You get a structured report:

```
🎯 NOW — What I'm actively building
✅ DONE — Completed this sprint
🎬 NEXT — What's blocked or planned
🧠 DECISIONS — Architectural choices made
🚦 STEPS — Next 3 concrete actions
🌐 CONTEXT — Important links / resources
```

**Useful flags:**
- `/sq-brief WORK-PROJECT-A --short` — 3 lines, perfect for Slack
- `/sq-brief WORK-PROJECT-A --email boss@company.com` — opens a draft email
- `/sq-brief --all` — brief on every active project (great for weekly review)

### `/sq-decision <topic>` — Log an important choice

**Use when:** you've made a real decision that future-you needs to remember. *Why* you chose Option A over Option B is the kind of thing your brain throws away after a week.

```
/sq-decision Use PostgreSQL instead of MySQL for the new service
```

Squirrel walks you through filling in: context, alternatives considered, consequences. The result is a small file that reads like a one-page memo, saved next to the project.

### `/sq-deadlines [--level critical,urgent]` — What's burning?

**Use when:** Monday morning, or anytime you feel "I know there's something due, but what?"

```
/sq-deadlines
```

Shows everything grouped by urgency in 6 levels:

| Level | When |
|---|---|
| 🔴 CRITICAL | Overdue, or due in < 4 hours |
| 🟠 URGENT | Today (≥4h) or tomorrow |
| 🟡 SOON | 2–3 days |
| 🔵 UPCOMING | 4–7 days |
| 🟢 EVENTUAL | 8–30 days |
| ⚪ DISTANT | More than 30 days |

Filter to just the scary ones:

```
/sq-deadlines --level critical,urgent
```

### `/sq-estimate <duration>` — Add the "ADHD tax" to a time estimate

**Use when:** you (or your boss) think something will take 2 hours, and you want to know the realistic number.

```
/sq-estimate 2 hours
```

You get:

```
⏱️  Estimación ADHD-buffered

  Your estimate:    2h
  Multiplier:       ×2.5
  Realistic:        5h

  💡 ADHD context-switching tax: tasks routinely take 2–3× the original guess.
```

It's not pessimism — it's research. (See: Mark et al., "The Cost of Interrupted Work".)

### `/sq-chunk <duration>` — Break a big task into bite-sized pieces

**Use when:** a task is too big to start (more than ~2 hours).

```
/sq-chunk 8 hours
```

You get a plan like:

```
🧩 Chunk Plan — 8 hours

Phases:
  🔬 Research & Planning   (60min)  → 1 chunk
  🛠  Setup & Scaffolding   (60min)  → 1 chunk
  ⚙️  Core Implementation   (240min) → 4 chunks
  ✨ Polish & Edge Cases    (90min)  → 2 chunks
  🧪 Testing & Docs         (50min)  → 1 chunk

Sessions (9 chunks, 2 sessions):
  📅 Session 1 (4h): research, setup, implementation 1–2
  📅 Session 2 (4h): implementation 3–4, polish, testing
```

Now the 8-hour monster is 9 small steps. Much easier to start.

### `/sq-chunk-intent [TAG]` — Break a specific project task

Like `/sq-chunk` but reads a task you already have in your vault and writes the chunks back into it as a checklist. Great for "this intent has been stuck for a week — let me decompose it."

### `/sq-task-initiation` — When you can't start

**Use when:** you're staring at something and can't make yourself begin.

```
/sq-task-initiation
```

Squirrel asks what kind of stuck you are (don't know what to do / can't click "go" / overwhelmed / scared) and applies the matching trick:

- **Smallest Action** — "just open file X, that's it"
- **2-Minute Start** — "work for 2 minutes, then you can stop"
- **Decompose** — "let's chunk this up"
- **Emotional Defusion** — "what would you do if you knew it'd go well?"

### `/sq-parakeet` — Friendly deadline reminders

**Use when:** you want the deadlines list but with kinder wording.

The "parakeet" is the part of Squirrel that nags — but it tunes its tone to urgency. Far-off deadlines get a casual mention. Critical ones are calm and non-judgmental ("here's where we are, here's one step that helps").

### `/sq-recover` — Restore a forgotten session

**Use when:** you forgot to `/sq-end` last time.

```
/sq-recover
```

Squirrel looks at your AI assistant's recent history and reconstructs what was happening, so you don't lose the thread.

### `/sq-dashboard` — Generate a pretty HTML page

**Use when:** you want to show your status to someone, or just enjoy a clean view.

```
/sq-dashboard
```

Creates an HTML file at `~/.squirrel/dashboard.html` and opens it in your browser. Auto-refreshes every 5 minutes.

---

## 9. Two Computers (Advanced)

> 🎯 *What you'll learn:* How to move notes between a personal computer and a work computer **without** any automatic cloud sync. This is the "air-gap" feature, and it's the most distinctive thing about Squirrel.

### The story

You research a tricky problem at home on Saturday. On Monday at work, you want that research available — but your work laptop can't reach your personal cloud, and your personal laptop can't reach work systems. (Welcome to NDAs and compliance rules.)

Squirrel's answer: **never sync automatically**. Instead, generate a *package* on one side, **you** carry it across (email yourself, paste, USB stick, whatever), apply it on the other side. You control every byte that crosses.

This is called an **air-gap** ([Glossary](#13-glossary)).

### Step 1 (home computer) — Generate the package

```
/sq-sync-out --scope=WORK-PROJECT-A:research
```

Squirrel:

1. Collects all "research" notes for `WORK-PROJECT-A`
2. Runs a **compliance check** — scans for accidental secrets (passwords, API keys, etc.)
3. Builds a single text block with a header, a SHA-256 hash (fingerprint), and the notes
4. Asks: copy to clipboard? open mailto:? save to a file?

**The package looks like this:**

```
<!-- SQUIRREL-PACKAGE v1 -->
<!--
  from: personal
  to: work
  generated_at: 2026-05-23T19:30:00Z
  scope: WORK-PROJECT-A:research
  files_count: 1
  hash_sha256: a3f5b8c9...
-->

# 📦 Squirrel Package
...
[your notes here]
...
<!-- END-SQUIRREL-PACKAGE -->
```

### Step 2 — Carry it across

Email it to yourself, paste into a chat app, drop it on a USB stick. It's just text — nothing else moves automatically.

### Step 3 (work computer) — Apply

In your AI assistant on the work computer, **paste the whole block** (from `<!-- SQUIRREL-PACKAGE` all the way to `END-SQUIRREL-PACKAGE -->`) into the chat.

Squirrel detects the marker and asks:

```
📦 Package detected.

From: personal  →  To: work
Hash: ✓ valid
Files: 1

📋 Plan:

| # | Operation | File                          | Status      |
|---|-----------|-------------------------------|-------------|
| 1 | CREATE    | WORK-PROJECT-A-RESEARCH-001.md | doesn't exist ✓ |

Apply? (yes / selective / cancel)
```

Say **yes** and the file lands in your work vault. Every application is logged in `<vault>/.squirrel/applied/` with a timestamp and hash — you have a full audit trail.

### Scope examples

| Command | What it grabs |
|---|---|
| `/sq-sync-out --scope=WORK-PROJECT-A:research` | All research notes for that project |
| `/sq-sync-out --scope=WORK-PROJECT-A:decisions` | All decisions only |
| `/sq-sync-out --scope=WORK-PROJECT-A:*` | The whole project |
| `/sq-sync-out --scope=WORK-PROJECT-A-INTENT-005` | A single specific intent |
| `/sq-sync-out --since=2026-05-20` | Everything modified since that date |
| `/sq-sync-out --manual` | Pick files interactively |

### Why no auto-sync?

Three reasons:

1. **Compliance.** Many workplaces forbid personal-cloud sync of company data. Manual = legal.
2. **Visibility.** You see the diff before applying. No surprise overwrites.
3. **Audit.** Every applied package leaves a record. If you ever need to prove what came in, you have it.

⚠️ *Watch out:* If you copy the package from an email, make sure your mail client didn't add line breaks in the middle of the hash. Hash mismatch → won't apply. See [Section 11](#11-when-things-go-wrong).

---

## 10. Power User (Advanced overview)

> 🎯 *What you'll learn:* Four powerful features at a glance — with pointers to deeper docs. Each is one paragraph.

### Encryption with GPG

For the truly sensitive packages (legal, medical, financial), you can encrypt everything end-to-end with **GPG** ([Glossary](#13-glossary)). In `~/.squirrel/config.toml` set `enabled = true` and your `gpg_recipient` email. Once configured, `/sq-sync-out --encrypt` produces `.gpg`-wrapped packages that only the recipient's private key can decrypt. Pre-requisite: `gpg --gen-key` first. **For full setup details, see `INSTALL.md` section "Cifrado con GPG".**

### Compliance mode (strict)

If you're a contractor or work at a company with strict information rules, turn on `compliance.strict = true` in your config. You can then whitelist which project tags are allowed inbound (`allowed_inbound_tags = ["WORK-*"]`), which environments can send you data (`allowed_inbound_environments = ["personal"]`), and which email domains should never appear in inbound packages (`corporate_domains = ["myemployer.com"]`). Squirrel blocks anything that fails the check. **Full schema in `INSTALL.md` section "Modo strict".**

### HTML dashboard auto-refresh

`/sq-dashboard` creates a self-contained HTML file with your full status. Open `~/.squirrel/dashboard.html` in any browser; it refreshes every 5 minutes. Share it with a teammate by hosting the file on any web server (it has no external dependencies). **Generator script: `lib/dashboard_generator.py`.**

### Standalone terminal CLI (no AI needed)

The whole project ships a binary called `squirrel` that you can run from your terminal without any AI assistant. Useful for cron jobs, scripts, or just quick checks:

```bash
squirrel status                    # WIP projects + alerts
squirrel deadlines                 # all deadlines by urgency
squirrel chunk --hours 8           # decompose a task
squirrel estimate "2 hours"        # ADHD buffer math
squirrel recover                   # find lost sessions
squirrel dashboard                 # generate HTML
squirrel install --agent claude    # install for Claude Code
```

You can also call the individual Python scripts directly:

```bash
python3 lib/status_aggregator.py --vault ~/vault-tdah --pretty
python3 lib/deadline_scanner.py --vault ~/vault-tdah --level critical
python3 lib/chunk_helper.py --hours 8 --pretty
```

**Full architecture in `ARCHITECTURE.md`.**

### macOS notification daemon

On macOS, install a background reminder that fires when critical deadlines approach:

```
/sq-reminders-install
```

Removes cleanly with `/sq-reminders-uninstall`. Linux/Windows: not yet supported.

---

## 11. When Things Go Wrong

> 🎯 *What you'll learn:* The 10 most common stumbles and how to fix each.

### "Slash commands don't show up in Claude Code"

- Confirm the plugin is at `~/.claude/plugins/squirrel/` (with the dot — it's a hidden folder)
- Confirm the file `~/.claude/plugins/squirrel/.claude-plugin/plugin.json` exists and opens as valid JSON
- Close **all** Claude Code windows and reopen — plugins load only at startup

### "`/sq-init` says 'plugin not found'"

The command tries to locate the plugin folder by searching `~/.claude/plugins` and `~/others`. If your install path is unusual, the search misses it.

**Fix:** symlink the project into the standard location:

```bash
ln -s /your/actual/path/squirrel ~/.claude/plugins/squirrel
```

### "vault_path not found in config.toml"

You haven't run `/sq-init` yet, or `~/.squirrel/config.toml` was deleted.

**Fix:** run `/sq-init` again — it's safe to run multiple times.

### "Python 3.9+ required" / "command not found: python3"

Install Python from [python.org](https://python.org/downloads). On Mac, you can also `brew install python3`.

### "Hash mismatch on sync-in"

The package text was truncated or modified between generation and paste — usually a mail client added line breaks.

**Fix:** re-paste, making sure you copy from `<!-- SQUIRREL-PACKAGE` all the way to `END-SQUIRREL-PACKAGE -->` with **nothing** added or removed. If you keep hitting this, save the package as an attachment instead of in the email body.

### "Compliance scan blocks legitimate content"

The secret-scanner is conservative and sometimes flags false positives (e.g., a string that *looks* like an API key but isn't).

**Fix (good):** edit the source note to remove the trigger pattern.
**Fix (escape hatch):** `--force-include` on `/sq-sync-out`. Not recommended for routine use.

### "Skill doesn't trigger automatically"

Some skills (like sync-in detecting a pasted package) rely on automatic triggers. If yours isn't firing:

- Run the matching slash command explicitly (`/sq-sync-in`)
- Check that your agent loads skills from the right directory

### "The vault doesn't have the expected structure"

Skills assume PARA folders (`01-Proyectos-Activos/`, etc.). If your vault is laid out differently:

- Easiest: let `/sq-init` create the PARA folders alongside your existing ones
- Or: edit the relevant skill's `SKILL.md` to match your layout

### "I forgot to `/sq-end` and lost my context"

```
/sq-recover
```

Squirrel reads recent AI session history and reconstructs the shutdown note for you. Not perfect, but usually 80% there.

### "I want to undo a sync-in"

Open `<vault>/.squirrel/applied/` — every application has a timestamped JSON log with the exact files that were created or changed. Delete or revert them manually using git or your editor.

---

## 12. Cheat Sheet

> 🎯 Print this page and tape it next to your monitor.

### Every slash command

| Command | What it does | When to use |
|---|---|---|
| `/sq-init` | First-time setup | Once, after install |
| `/sq-start [TAG]` | Load project context | Beginning of a work session |
| `/sq-end` | Save shutdown note | End of a work session |
| `/sq-capture <text>` | Quickly save a note/idea | Anytime inspiration strikes |
| `/sq-where-am-i` | "What was I doing?" | Sitting down cold |
| `/sq-status` | Full vault overview | Monday morning / weekly review |
| `/sq-brief [TAG]` | 6-section status report | Stakeholder updates, stand-ups |
| `/sq-decision <topic>` | Log an architectural choice | After making a real decision |
| `/sq-deadlines` | Deadlines by urgency | When something feels due |
| `/sq-estimate <time>` | Add ADHD buffer (×2–3) | Before committing to a deadline |
| `/sq-chunk <time>` | Break big task into chunks | Task > 2 hours |
| `/sq-chunk-intent [TAG]` | Chunk a specific vault task | Project task is stuck |
| `/sq-task-initiation` | Anti-paralysis protocols | Can't get started |
| `/sq-parakeet` | Tone-tuned deadline reminders | Want a kinder nag |
| `/sq-recover` | Restore a lost session | Forgot to `/sq-end` |
| `/sq-dashboard` | Generate HTML status page | Sharing with someone |
| `/sq-sync-out --scope=...` | Export package to other machine | Crossing home ↔ work |
| `/sq-sync-in` | Apply a pasted package | Receiving from another machine |
| `/sq-reminders-install` | macOS deadline notifications | Once on macOS, optional |
| `/sq-reminders-uninstall` | Remove the macOS daemon | If you no longer want it |

### Standalone terminal commands

| Command | Equivalent slash command |
|---|---|
| `squirrel status` | `/sq-status` |
| `squirrel deadlines` | `/sq-deadlines` |
| `squirrel chunk --hours N` | `/sq-chunk` |
| `squirrel estimate "<time>"` | `/sq-estimate` |
| `squirrel recover` | `/sq-recover` |
| `squirrel dashboard` | `/sq-dashboard` |
| `squirrel install --agent claude` | (install helper) |

### Key file paths

| Path | What's in it |
|---|---|
| `~/.squirrel/config.toml` | Your settings |
| `~/.squirrel/state.json` | Currently active project + intent |
| `~/.squirrel/dashboard.html` | Generated HTML view |
| `<vault>/01-Proyectos-Activos/` | Active project folders |
| `<vault>/.squirrel/applied/` | Sync audit log |
| `<vault>/.squirrel/outgoing/log.jsonl` | Export history |

---

## 13. Glossary

> 🎯 Every technical word in this guide, in plain English.

**Air-gap** — A computer setup where no automatic data path exists between two systems. You have to physically (or manually) carry information across. Squirrel's sync feature is air-gapped on purpose.

**CLI (Command-Line Interface)** — A text-only program you control by typing commands in a terminal, instead of clicking buttons.

**Compliance** — Rules a workplace has about what data can go where (e.g., "no client info on personal laptops"). Squirrel's "compliance mode" enforces these rules.

**Frontmatter** — The little block at the top of a note file, between two `---` lines, that holds metadata (date, project tag, type). Squirrel reads this to know what each file is.

**GPG (GNU Privacy Guard)** — A widely-used encryption tool. Anyone with the right "private key" can read encrypted data; anyone without it sees only gibberish.

**Hyperfocus** — When an ADHD brain locks onto something for 6+ hours without noticing time. Sometimes great, often costly (you forget to eat, miss meetings). Squirrel's "hyperfocus guardian" feature nudges you out.

**Intent** — A small unit of project work — a single goal you're trying to accomplish. One project has many intents over its lifetime.

**JSON** — A simple data format (text that looks like `{ "key": "value" }`). Squirrel's scripts use it to pass data around.

**Markdown** (`.md` files) — Plain text with a few simple formatting marks (`# heading`, `*italic*`, `**bold**`). Easy for humans to read, easy for computers to parse.

**Package** — A single text block that bundles up notes for transfer between computers. Has a header, a hash, and the notes themselves.

**PARA** — A note-organization system invented by Tiago Forte. Four folders: **P**rojects (active), **A**reas (ongoing), **R**esources (reference), **A**rchive (done). Squirrel uses this.

**Parakeet** — Squirrel's friendly deadline-reminder feature. Named because parakeets chirp at regular intervals — but Squirrel's parakeet tunes its volume to urgency.

**Plugin** — A piece of software that adds new capabilities to a host program. Squirrel is a plugin for Claude Code (and others).

**Python** — A popular programming language. Squirrel's background work is written in Python.

**SHA-256 hash** — A unique fingerprint of a file or block of text. If anything changes (even one character), the fingerprint changes. Squirrel uses it to detect tampering or corruption in transfer.

**Shutdown note** — A short summary you write at the end of a work session: what you did, what's next, what's blocking you. The bridge between today and tomorrow.

**Skill** — A reusable AI-prompt-and-tool bundle that does one specific thing well. Squirrel ships ~13 skills (capture, brief, sync-in, etc.).

**Slash command** — A command in an AI assistant that starts with `/`, like `/sq-start`. It runs a skill.

**Tag** — A short, all-caps code for a project (e.g., `WORK-PROJECT-A`). Squirrel uses tags to know which project a note belongs to.

**TOML** — A simple config-file format. `~/.squirrel/config.toml` is your settings file in TOML.

**Vault** — A folder on your computer where all your notes live. You name yours (default: `~/vault-tdah`).

**YAML** — Another data format, often used inside frontmatter. Looks like `key: value` on each line.

---

## Where to go next

- **Just installed?** → Re-read [Section 4 — Your First 10 Minutes](#4-your-first-10-minutes), then start using `/sq-capture` daily.
- **Using it for a week?** → Add `/sq-end` as a hard habit before you stop working.
- **Using it for a month?** → Try `/sq-brief` to send a stand-up update, and `/sq-status` for your weekly review.
- **Two computers?** → Try the sync flow in [Section 9](#9-two-computers-advanced).
- **Curious about internals?** → Read `ARCHITECTURE.md`.
- **Found a bug?** → File an issue, or drop a note in `99-Resources/squirrel-feedback.md` in your vault.

Welcome to the squirrel club. 🐿️
