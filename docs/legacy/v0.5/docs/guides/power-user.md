# Power User (Advanced) — Encryption, CLI, Dashboards, and Compliance Mode

> 🎯 *What you'll learn:* Four advanced features for power users: GPG encryption, compliance strict mode, HTML dashboards, standalone CLI, Python scripts, and macOS notifications.

**Version:** Squirrel v0.5.0  
**Last updated:** 2026-05-24  
**Reading time:** ~16 minutes

---

## Table of Contents

1. [Web UI companion (browser for non-tech users)](#web-ui-companion--browser-for-non-tech-users)
2. [GPG encryption — end-to-end](#gpg-encryption--end-to-end)
3. [Compliance mode (strict)](#compliance-mode-strict)
4. [HTML dashboard](#html-dashboard)
5. [Standalone CLI (no AI needed)](#standalone-cli-no-ai-needed)
6. [Python scripts directly](#python-scripts-directly)
7. [macOS notification daemon](#macos-notification-daemon)
8. [Full config.toml reference](#full-configtoml-reference)

---

## Web UI companion — browser for non-tech users

For partners, family members, or anyone who prefers a browser interface to slash commands, Squirrel includes a **local web UI** — a friendly browser companion that lets non-technical users access their Squirrel vault without learning Markdown, file paths, or the terminal.

### What it is

A lightweight Python HTTP server (`localhost:3939`) that serves 8 plain HTML pages:

- **Home** — Today's focus, deadlines today/tomorrow, big "Add a note" button
- **Projects** — Browse all projects, view deadlines for each
- **Deadlines** — Grouped simply (Today / This week / Later)
- **History** — Recent activity, 30 items newest-first
- **Note view/edit** — Read or edit a note in a plain textarea
- **Project view/edit** — Read or edit a project description
- **Settings** — Dark mode toggle, vault picker (if multiple)

**Key design decisions:**
- No build step, no Node.js, no React — plain HTML + small vanilla JavaScript (~300 lines)
- Localhost-only by default (no authentication needed, same machine only)
- Designed for iPad + laptop, touch-friendly, accessible (WCAG AA contrast, 44×44 px tap targets)
- Uses plain English ("note", "project", "deadline") — no developer vocabulary ("vault", "frontmatter", "PARA", "intent")
- Optional AI features if you configure an API key

### Start the web UI

```bash
squirrel web start
```

Squirrel starts the server on `http://127.0.0.1:3939` and prints the URL:

```
🌐 Web UI running on http://127.0.0.1:3939
```

**Other commands:**

```bash
squirrel web open          # Start server (if not running) and open in browser
squirrel web status        # Check if running
squirrel web stop          # Stop the server
squirrel web uninstall     # Remove everything (vault untouched)
```

### Real-world scenario: Diego's spouse

Diego uses Squirrel for work via slash commands. His spouse Maria wants to see what deadlines are coming up and add notes sometimes, but she doesn't know Markdown or Claude Code.

**Before:** Maria has to ask Diego "What do we have due?" every time.

**After:** Diego runs `squirrel web start`, gives Maria the bookmark `http://localhost:3939`, and she opens it on her iPad:

```
┌─────────────────────────────────────────────┐
│  🌙 Squirrel                                │
├─────────────────────────────────────────────┤
│                                             │
│  Today's Focus                              │
│  ├─ Prepare dinner for dinner party        │
│  └─ Confirm flight tickets                 │
│                                             │
│  Due Soon                                   │
│  ├─ 🔴 Dinner party — Today                │
│  ├─ 🟠 Flight confirmation — Tomorrow      │
│  └─ 🟡 Hotel booking — This week           │
│                                             │
│  ┌─────────────────────────────────────────┐
│  │ [+ Add a note]                          │
│  └─────────────────────────────────────────┘
│                                             │
│ [All projects]  [Deadlines]  [Settings]    │
│                                             │
└─────────────────────────────────────────────┘
```

Maria taps **"+ Add a note"**, types "Book restaurant for party", taps "Add". The note lands in Diego's vault automatically. No friction.

Tomorrow morning, Maria opens the URL again, sees the updated list. The note she added yesterday is there.

### Features

**Capture (most common):**
1. Tap "+ Add a note" (header, always visible)
2. Type your note
3. Optionally pick a project (defaults to "Unfiled")
4. Tap "Add"
5. Note is saved to the vault, visible in Obsidian and slash commands

**Browse and search:**
- Project pages show recent notes and deadlines for that project
- Deadlines page groups by urgency (Today / This week / Later)
- History page shows last 30 things touched
- Search box (live filtering)

**Edit notes:**
- Open a note, tap "Edit"
- Plain textarea (raw Markdown)
- Save with "Save" button
- If someone else edited it at the same time, you get a simple conflict picker

**Dark mode:**
- Toggle in Settings
- Preference saved (across page refreshes)

**Multi-vault (if you have 2+ configured):**
- Dropdown in header to switch vaults
- Vault choice is remembered

### Optional AI features

If you configure an Anthropic API key in `~/.squirrel/config.toml`:

```toml
[ai]
provider = "anthropic"
api_key = "sk-ant-..."
model = "claude-sonnet-4-6"  # optional
```

Three buttons appear in the UI:

- **"Generate brief" (project page)** — AI reads the project, writes a 6-section status brief, you can save it as a note
- **"Help me decide" (capture modal)** — Step-by-step wizard: you describe a decision, AI asks clarifying questions, result is a decision note
- **"Help me start" (home page)** — AI suggests one concrete next action based on your projects and recent activity

If you remove the `[ai]` block from config, the buttons disappear. The user never knows AI exists.

**Cost is bounded:** `max_tokens=2000` per request, and only one AI request in-flight per browser session.

### Auto-start on macOS (optional)

```bash
bash companions/web-ui/launchd/install.sh
```

This installs a LaunchAgent so the web server starts automatically when you log in. Later:

```bash
bash companions/web-ui/launchd/install.sh --uninstall
```

**On Linux/Windows:** Not yet supported. You can start it manually with `squirrel web start` or add it to your startup script.

### Security model

- **Localhost only by default** — `127.0.0.1:3939`. Anyone on your machine can access it (they already have vault access via the filesystem).
- **Optional LAN access** — `squirrel web start --lan` binds `0.0.0.0` with a yellow warning. Use only on a trusted home network.
- **Never expose to the internet** — No authentication, no encryption, not designed for remote access.
- **Atomic writes** — Every file write uses temp file + atomic replace (same as vault CLI).
- **Concurrency check** — mtime validation on every edit, simple conflict resolution.
- **No telemetry** — The server makes zero outbound requests unless you configure AI (and even then, only when you click the button).

### What's NOT in the web UI

By design, these remain in slash commands and CLI:

- **Delete a file** — Too dangerous for non-technical users
- **Create/rename projects or folders** — Too complex for the target audience
- **Sync packages** (`sync-out` / `sync-in`) — Compliance-sensitive, stays in CLI
- **GPG encryption** — Advanced, stays in CLI
- **Markdown WYSIWYG editor** — Simple textarea is enough; power users use Obsidian

### Reversibility

```bash
# Stop the server
squirrel web stop

# Remove auto-start (macOS)
bash companions/web-ui/launchd/install.sh --uninstall

# Uninstall everything (server stops, launchd removed, PID file deleted)
squirrel web uninstall

# Delete the source files (optional, keeps everything else working)
rm -rf companions/web-ui
```

Your vault and `config.toml` are **never** modified. The web UI is purely optional.

---

## GPG encryption — end-to-end

For truly sensitive vaults (legal documents, medical notes, financial records), you can encrypt every package with GPG. Only your private key can decrypt.

### Setup (one-time)

**Step 1: Generate a GPG key (if you don't have one)**

```bash
gpg --gen-key
```

GPG walks you through key generation. Pick:
- **Name:** Your name or handle
- **Email:** Use your personal email (this becomes the key identifier)
- **Passphrase:** A strong password (you'll type this when decrypting)

After ~30 seconds, you have a key:

```
pub   rsa4096 2026-05-24 [SC]
      A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6
uid           [ultimate] Your Name <your-email@example.com>
sub   rsa4096 2026-05-24 [E]
```

**Step 2: Tell Squirrel to use it**

Edit `~/.squirrel/config.toml` and add:

```toml
[encryption]
enabled = true
gpg_recipient = "your-email@example.com"
```

The `gpg_recipient` is the email from your GPG key above.

### Encrypt a package

```
/sq-sync-out --scope=LEGAL-PROJECT:* --encrypt
```

Squirrel generates the package and pipes it through GPG:

```
-----BEGIN PGP MESSAGE-----
Version: GnuPG v2

jA0EBAABCgA3FiEEA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6
VQI58wvg2E5K7F8...
[long encrypted block]
...
=ABCD
-----END PGP MESSAGE-----
```

**This is unreadable without your private key.** Send it anywhere — email, chat, cloud storage. Only you can decrypt.

### Decrypt and apply (other side)

On your work laptop, paste the encrypted block:

```
-----BEGIN PGP MESSAGE-----
...
-----END PGP MESSAGE-----
```

Squirrel detects it's encrypted, runs `gpg --decrypt` (asks for your passphrase once), and applies the decrypted files. Transparent — you don't need to manually decrypt.

**⚠️ Note:** If you're setting up a second computer, you need to export your GPG private key to it. This is beyond the scope here — consult GPG documentation for `gpg --export-secret-keys`.

---

## Compliance mode (strict)

You're a contractor or work at a company with strict information rules. Squirrel can enforce whitelist/blacklist rules:

### Setup

Edit `~/.squirrel/config.toml`:

```toml
[compliance]
strict = true
allowed_inbound_tags = ["WORK-*"]
allowed_inbound_environments = ["personal"]
corporate_domains = ["mycompany.com"]
allowed_inbound_tags = ["WORK-*", "GENERIC-*"]
```

### What each rule does

| Rule | Example | Effect |
|---|---|---|
| `strict = true` | (boolean) | Enable compliance checks |
| `allowed_inbound_tags` | `["WORK-*"]` | Only accept packages from projects matching these tags. Reject anything tagged `PERSONAL-*`, `SIDE-*`, etc. |
| `allowed_inbound_environments` | `["personal"]` | Only accept packages from these environments. Reject if package says "from: home" |
| `corporate_domains` | `["mycompany.com"]` | Block any package containing email addresses from these domains (prevents accidental leak of internal emails) |

### Real scenario

You're Rajesh, a contractor. Your config says:

```toml
[compliance]
strict = true
allowed_inbound_tags = ["CLIENT-PROJECT-*"]
allowed_inbound_environments = ["personal"]
corporate_domains = ["bigcorp.com"]
```

**What happens:**
- You can bring in packages tagged `CLIENT-PROJECT-A`, `CLIENT-PROJECT-B` ✅
- You **cannot** bring in packages tagged `INTERNAL-RESEARCH` ❌ (not in whitelist)
- You **cannot** bring in packages from `work` environment ❌ (only `personal` allowed)
- You **cannot** bring in packages containing `bigcorp.com` email addresses ❌ (corporate domain)

**If you try to apply a blocked package:**

```
❌ Compliance violation detected

Package failed compliance check:
  - Tag CLIENT-INTERNAL not in allowed list [CLIENT-PROJECT-*]
  - Environment "work" not in allowed list ["personal"]
  - Found email addresses from blocked domain "bigcorp.com"

Apply anyway? (NOT recommended)
```

You say "no", and nothing is applied. **Compliance enforced.**

---

## HTML dashboard

Generate a self-contained, auto-refreshing HTML page showing your full status.

### Generate

```
/sq-dashboard
```

Squirrel creates `~/.squirrel/dashboard.html` and opens it in your browser:

```
┌────────────────────────────────────────────────────┐
│ 📊 Squirrel Dashboard                              │
├────────────────────────────────────────────────────┤
│                                                    │
│ PROJECTS (4 active)                                │
│ ├─ WORK-PROJECT-A — 60% — no blockers            │
│ ├─ WORK-PROJECT-B — 20% — waiting on design       │
│ ├─ SIDE-BLOG — 10% — ready to work               │
│ └─ TAXES-2026 — 0% — not started                 │
│                                                    │
│ DEADLINES (next 7 days)                            │
│ 🟠 WORK-PROJECT-A code review — Friday (3 days)   │
│ 🟡 SIDE-BLOG publish — Sunday (5 days)            │
│                                                    │
│ ALERTS                                             │
│ ⚠️ TAXES-2026 not started; 6 weeks to deadline    │
│                                                    │
│ FOCUS TODAY                                        │
│ 1. WORK-PROJECT-A (closest deadline)              │
│ 2. SIDE-BLOG (if time)                            │
│                                                    │
│ [Auto-refreshes every 5 minutes]                  │
│                                                    │
└────────────────────────────────────────────────────┘
```

### Use cases

**Display on a second monitor:**
Open the HTML file in a browser tab on Monitor 2. It refreshes every 5 minutes. Glance at it whenever you want a status update.

**Share with a teammate:**
Email the HTML file to a teammate. They open it in their browser and see your status (read-only). No need for a sync meeting.

**Embed on a shared dashboard:**
Upload the HTML file to a web server. Your team can view the current status from a shared URL.

### Customize refresh interval

```
/sq-dashboard --refresh 10
```

Refreshes every 10 minutes instead of 5.

---

## Standalone CLI (no AI needed)

Squirrel ships a `squirrel` binary that works from your terminal, no AI assistant needed.

### Installation

```bash
# Copy the binary to your PATH
cp ~/path/to/squirrel/squirrel /usr/local/bin/squirrel
chmod +x /usr/local/bin/squirrel

# Verify
squirrel --version
# squirrel 0.5.0
```

### Available commands

| Command | What it does | Equivalent |
|---|---|---|
| `squirrel status` | Show all WIP projects + alerts | `/sq-status` |
| `squirrel deadlines` | List all deadlines by urgency | `/sq-deadlines` |
| `squirrel deadlines --critical` | Show only critical/urgent | `/sq-deadlines --level critical,urgent` |
| `squirrel chunk --hours 8` | Break an 8-hour task into chunks | `/sq-chunk 8 hours` |
| `squirrel estimate "2 hours"` | Add ADHD buffer to estimate | `/sq-estimate 2 hours` |
| `squirrel recover` | Restore a lost session | `/sq-recover` |
| `squirrel dashboard` | Generate HTML dashboard | `/sq-dashboard` |
| `squirrel install --agent claude` | Install for Claude Code | (one-time setup) |

### Real-world uses

**Cron job (automated daily status email)**

```bash
# Add to crontab: every morning at 7 AM
0 7 * * * squirrel status | mail -s "Daily Status" you@example.com
```

**Quick check in a terminal**

```bash
# You're in the terminal, want to see status fast
squirrel deadlines --critical

# Output:
# 🔴 CRITICAL
# SCHOOL-LAB-3 — due Friday 11:59 PM (2 days)
```

**Scripting**

```bash
#!/bin/bash
# Check if any critical deadlines; if so, send alert
CRITICAL=$(squirrel deadlines --critical | grep -c "🔴")
if [ $CRITICAL -gt 0 ]; then
    echo "Critical deadline(s) found!" | mail you@example.com
fi
```

---

## Python scripts directly

Advanced users can call Squirrel's Python modules directly:

```bash
# Show status with pretty formatting
python3 lib/status_aggregator.py --vault ~/vault-notas --pretty

# Scan for deadlines, output JSON
python3 lib/deadline_scanner.py --vault ~/vault-notas --json

# Generate a chunk plan
python3 lib/chunk_helper.py --hours 8 --output json
```

### Available scripts

| Script | Purpose | Example |
|---|---|---|
| `lib/status_aggregator.py` | Aggregate project status | `--vault <path> --project <tag> --detailed` |
| `lib/deadline_scanner.py` | Scan for deadlines | `--vault <path> --level critical --json` |
| `lib/chunk_helper.py` | Break tasks into chunks | `--hours 8 --pretty` |
| `lib/estimate_helper.py` | ADHD-buffered estimation | `--estimate "2 hours"` |
| `lib/decision_logger.py` | Log decisions | `--vault <path> --project <tag>` |

**For developers:** These modules expose Python APIs. You can import them and build custom tools:

```python
from lib.status_aggregator import StatusAggregator

agg = StatusAggregator(vault_path="~/vault-notas")
status = agg.aggregate_project("WORK-PROJECT-A")
print(f"Progress: {status['progress']}%")
```

---

## macOS notification daemon

On macOS, run a background daemon that sends desktop notifications when critical deadlines approach.

### Install (once, on macOS)

```
/sq-reminders-install
```

This:
1. Creates a LaunchAgent at `~/Library/LaunchAgents/com.squirrel.reminders.plist`
2. Registers it with macOS (runs at login)
3. Starts checking deadlines every 30 minutes

### See it in action

```
🔴 CRITICAL DEADLINE
   SCHOOL-LAB-3 due Friday 11:59 PM (2 days away)
   Next action: run /sq-start SCHOOL-LAB-3
```

The notification pops up on your screen (respects macOS Do Not Disturb settings). Click it to open Claude Code with that project pre-loaded.

### Customize

Edit `~/.squirrel/config.toml`:

```toml
[notifications]
enabled = true
check_interval = 30  # minutes
alert_threshold = 3  # days
min_urgency = "urgent"  # only urgent+critical, not "soon"
```

### Uninstall

```
/sq-reminders-uninstall
```

Removes the LaunchAgent (you won't get notifications anymore).

**Note:** Linux/Windows not yet supported. We're working on systemd and Task Scheduler integrations.

---

## Full config.toml reference

Here's every key in `~/.squirrel/config.toml`, what it means, and defaults:

### Essential (required)

```toml
vault_path = "~/vault-notas"
# Where your notes live. Must exist and be writable.

environment_name = "personal"
# Label for this computer. Used in sync package headers.
# E.g., "personal", "work", "laptop-mac"

default_email = "you@example.com"
# Email used for draft emails, sync recipient headers, etc.
```

### Projects

```toml
[projects]
active = ["WORK-PROJECT-A", "SIDE-BLOG"]
# Projects you're actively working on. These show in /sq-status, /sq-where-am-i

archived = ["TAXES-2025"]
# Finished projects. Won't show in status checks, but notes remain in vault.

default_project = "WORK-PROJECT-A"
# If /sq-start is called with no project, assume this one.
# (If not set, Squirrel asks.)
```

### Encryption (optional, for sensitive vaults)

```toml
[encryption]
enabled = false
# Set to true if you want GPG encryption for sync packages.

gpg_recipient = "you@example.com"
# Your GPG key's email. Squirrel uses this to encrypt packages.
# You must have a GPG key with this email: run `gpg --list-keys`
```

### Compliance (optional, for contractors/regulated work)

```toml
[compliance]
strict = false
# Set to true to enforce whitelist/blacklist rules on inbound packages.

allowed_inbound_tags = []
# If strict=true, only accept packages with tags matching these patterns.
# E.g., ["WORK-*", "CLIENT-*"]. If empty, all tags allowed.

allowed_inbound_environments = []
# If strict=true, only accept packages from these environments.
# E.g., ["personal"]. If empty, all environments allowed.

corporate_domains = []
# If strict=true, block packages containing email addresses from these domains.
# E.g., ["mycompany.com"]. If empty, no domain blocking.
```

### Notifications (optional, macOS only)

```toml
[notifications]
enabled = false
# Set to true to enable desktop notifications for critical deadlines.
# (macOS only; Linux/Windows not yet supported.)

check_interval = 30
# How often to check deadlines, in minutes. Default: 30.

alert_threshold = 3
# How many days out to start alerting. Default: 3 (alert 3+ days ahead).
# Set to 1 for last-minute alerts only.

min_urgency = "urgent"
# Alert on this urgency level and higher.
# Options: "critical", "urgent", "soon", "upcoming", "eventual", "distant"
```

### Advanced

```toml
[behavior]
language = "en"
# UI language. Options: "en" (English), "es" (Spanish).
# Default: detected from system locale.

shutdown_note_max_words = 200
# Limit the length of shutdown notes (prevents infinite length).

session_state_file = "~/.squirrel/state.json"
# Where to store current session state (project, active intent, etc.)
```

---

## Where to go next

- **Ready to ship?** → Use all these tools in combination: encrypt sensitive packages, use the CLI in crons, share dashboards with your team.
- **Want more info on any feature?** → Read the relevant section in [Two Computers](./two-computers.md) (encryption/compliance/audit trail) or [Everyday Use](./everyday-use.md) (core commands).
- **Building custom tools?** → The Python APIs in `lib/` are documented. You can extend Squirrel.

You're now a power user. The vault is yours, the data is yours, and you control every byte. 🐿️
