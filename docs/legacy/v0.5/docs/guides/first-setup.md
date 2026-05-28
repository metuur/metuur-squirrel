# First Setup — Initialize Squirrel on Your Computer

> 🎯 *What you'll learn:* How to run `/sq-init`, answer the four setup questions, understand what files get created, verify everything works, and troubleshoot common setup errors.

**Version:** Squirrel v0.5.0  
**Last updated:** 2026-05-24  
**Reading time:** ~10 minutes

---

## Table of Contents

1. [What `/sq-init` does](#what-sqqinit-does)
2. [The four setup questions](#the-four-setup-questions)
3. [Real situation: Mariana sets up Squirrel](#real-situation-mariana-sets-up-squirrel)
4. [What gets written to disk](#what-gets-written-to-disk)
5. [Editing your config later](#editing-your-config-later)
6. [Verification steps](#verification-steps)
7. [Troubleshooting](#troubleshooting)

---

## What `/sq-init` does

The `/sq-init` command is a one-time setup wizard that:

1. **Asks four questions** about your setup (where to store notes, what computer you're on, your email, what projects you're working on)
2. **Creates your vault** — a folder on your computer that holds all your Squirrel notes
3. **Builds the PARA system** — four folders inside your vault: Projects, Areas, Resources, Archive (this is Tiago Forte's organization method)
4. **Writes config** — a settings file at `~/.squirrel/config.toml` that tells Squirrel how to find your notes and which projects you're tracking
5. **Creates a demo project** — so you can see what a real project looks like
6. **Optionally installs Obsidian dashboards** — if you're using Obsidian, it creates pretty visual boards for your notes

You only run this once per computer. After that, `/sq-init` is mostly a reference tool if you want to change your settings.

---

## The four setup questions

When you run `/sq-init`, you'll be asked exactly four things. Here's what each one means:

| Question | What it's asking | Why it matters | Example answers |
|---|---|---|---|
| **vault_path** | Where on your computer should your notes live? | This is the folder where every captured note, decision, shutdown note, and project folder will be stored. Pick a path you can remember and that has free disk space. | `~/vault-tdah` (default), `~/Documents/squirrel-notes`, `/Users/mariana/mywork/vault` |
| **environment_name** | What should we call *this* computer? | This label lets Squirrel know which environment you're on. If you use two computers (home + work), you'll give each a different name so sync packages can say "from home → to work" clearly. | `personal`, `home`, `work`, `laptop`, `macbook-pro` |
| **default_email** | What's your email address? | Used only when you ask Squirrel to draft an email (e.g., sending a status brief). If you leave this blank, Squirrel will ask for your email each time. | `mariana@example.com`, `my-work-email@company.com` |
| **active_projects** | What project codes are you working on **right now**? | These are the projects Squirrel should track and show you by default. You can add/remove projects anytime later. Use comma-separated ALL-CAPS codes (no spaces). | `FREELANCE-WEBSITE,VISA-APPLICATION`, `WORK-PROJECT-A,SIDE-BLOG,SCHOOL-MATH` |

**💡 Tip on project codes:** Good project codes are ALL-CAPS with hyphens, 2–4 segments. Examples:
- `WORK-PROJECT-A` — fine, clear
- `FREELANCE-DESIGN-CLIENT` — good, specific  
- `SIDE-BLOG` — good, short
- `TRIP-JAPAN-2026` — great, includes the year
- `TAXES-2026` — perfect for one-time tasks

Avoid single-word codes (`WORK`, `BLOG`) and spaces. If you're unsure, you can always rename them later.

---

## Real situation: Mariana sets up Squirrel

Let's watch Mariana set up Squirrel. She works from home on three projects: a freelance website redesign, a visa application for her family, and personal notes on improving her ADHD workflow. She has one computer (a MacBook).

**Mariana runs:**
```bash
/sq-init
```

**She answers the four questions:**

1. **vault_path:** She types `~/vault-notas` (in her home directory)
2. **environment_name:** She types `macbook-personal`
3. **default_email:** She types `mariana.rivas@gmail.com`
4. **active_projects:** She types `FREELANCE-WEBSITE-REDESIGN,VISA-APPLICATION,ADHD-SELF-STUDY`

**Squirrel then:**
- Creates the folder `~/vault-notas/`
- Inside it, builds four folders:
  - `01-Proyectos-Activos/` (her three active projects will get folders here)
  - `02-Areas/` (long-term areas, like "Health" or "Finance")
  - `03-Recursos/` (reference material she saves)
  - `04-Archivo/` (old finished projects)
- Writes `~/.squirrel/config.toml` (her settings file)
- Creates a demo project folder at `01-Proyectos-Activos/DEMO-INICIO/`
- Asks: "¿Querés instalar los dashboards de Obsidian?" → Mariana says "sí" because she uses Obsidian for her notes

**Success:** Mariana now has a `config.toml` that looks like this (simplified view):

```toml
vault_path = "~/vault-notas"
environment_name = "macbook-personal"
default_email = "mariana.rivas@gmail.com"

[projects]
active = ["FREELANCE-WEBSITE-REDESIGN", "VISA-APPLICATION", "ADHD-SELF-STUDY"]
```

---

## What gets written to disk

After `/sq-init`, your computer now has this structure:

```
~/.squirrel/
├── config.toml                    ← Your settings (the only file you'll edit)
├── state.json                     ← Current session state (auto-maintained)
├── dashboard.html                 ← Generated later by /sq-dashboard
└── applied/                       ← Sync audit log (if you use sync-in)

~/vault-notas/                     ← Your vault (you chose the path)
├── 01-Proyectos-Activos/          ← Active projects
│   ├── FREELANCE-WEBSITE-REDESIGN/
│   ├── VISA-APPLICATION/
│   ├── ADHD-SELF-STUDY/
│   └── DEMO-INICIO/               ← Demo project (safe to delete)
├── 02-Areas/                      ← Long-term areas (e.g., "Salud", "Finanzas")
├── 03-Recursos/                   ← Reference & captured articles
│   └── Captures/                  ← Quick captures from /sq-capture
├── 04-Archivo/                    ← Finished projects (move them here)
├── .squirrel/
│   ├── switches.jsonl             ← Log of project switches
│   ├── applied/                   ← Applied sync packages (with audit trail)
│   └── outgoing/                  ← Log of exported packages
└── index.md                       ← Dashboard index (if Obsidian installed)
```

---

## Editing your config later

Your `config.toml` file is plain text. You can edit it anytime with a text editor. Here are the **5 most-changed keys** and how to adjust them:

### 1. Adding a new project

**Before:**
```toml
[projects]
active = ["FREELANCE-WEBSITE-REDESIGN", "VISA-APPLICATION"]
```

**After (you added TAXES-2026):**
```toml
[projects]
active = ["FREELANCE-WEBSITE-REDESIGN", "VISA-APPLICATION", "TAXES-2026"]
```

**Next time you run `/sq-start`, that project will show up in the list.**

### 2. Changing your vault path

**⚠️ Warning:** Only do this if you're moving your vault folder. Squirrel uses this path to find all your notes.

**Before:**
```toml
vault_path = "~/vault-notas"
```

**After (moved to Documents):**
```toml
vault_path = "~/Documents/squirrel-vault"
```

**Make sure the new folder path actually exists, and all your notes are there.**

### 3. Changing your environment name

If you renamed your computer or realized "personal" is clearer than "macbook-personal":

**Before:**
```toml
environment_name = "macbook-personal"
```

**After:**
```toml
environment_name = "personal"
```

### 4. Updating your email

**Before:**
```toml
default_email = "old-email@example.com"
```

**After:**
```toml
default_email = "new-email@example.com"
```

### 5. Archiving a project

Move a finished project from `active` to `archived`:

**Before:**
```toml
[projects]
active = ["FREELANCE-WEBSITE-REDESIGN", "VISA-APPLICATION", "ADHD-SELF-STUDY"]
archived = []
```

**After (VISA-APPLICATION is done):**
```toml
[projects]
active = ["FREELANCE-WEBSITE-REDESIGN", "ADHD-SELF-STUDY"]
archived = ["VISA-APPLICATION"]
```

**Squirrel will stop showing VISA-APPLICATION in your regular status checks.**

---

## Verification steps

After running `/sq-init`, verify that everything is set up correctly:

### Check 1: Config file exists

```bash
cat ~/.squirrel/config.toml
```

**What you should see:** Your four answers printed out in TOML format (no errors).

### Check 2: Vault folders exist

```bash
ls -la ~/vault-notas
```

**What you should see:**
```
01-Proyectos-Activos
02-Areas
03-Recursos
04-Archivo
```

### Check 3: Test with `/sq-where-am-i`

Open Claude Code and run:

```
/sq-where-am-i
```

**What you should see:**
```
📋 Proyectos activos:

🟢 FREELANCE-WEBSITE-REDESIGN
   Última actividad: nunca
   Siguiente acción: crear primer intent

🟢 VISA-APPLICATION
   Última actividad: nunca
   Siguiente acción: crear primer intent

🟢 ADHD-SELF-STUDY
   Última actividad: nunca
   Siguiente acción: crear primer intent
```

✅ **If you see all three projects, setup is complete.** You're ready for "First 10 Minutes" next.

---

## Troubleshooting

### ❌ "config.toml not found"

**What happened:** `/sq-init` didn't run, or it didn't succeed.

**Fix:**
```bash
ls -la ~/.squirrel/
```

If the file doesn't exist, run `/sq-init` again (it's safe to run multiple times).

### ❌ "vault_path doesn't exist"

**What happened:** You gave a path that doesn't exist on your computer.

**Fix:** Edit `~/.squirrel/config.toml` and change `vault_path` to a valid path:

```bash
# Create the path first if needed
mkdir -p ~/vault-notas

# Then update config.toml
# vault_path = "~/vault-notas"
```

### ❌ "PARA folders missing"

**What happened:** You ran `/sq-init` but the four folders weren't created.

**Fix:** Create them manually:

```bash
mkdir -p ~/vault-notas/{01-Proyectos-Activos,02-Areas,03-Recursos,04-Archivo}
```

Then run `/sq-init` again — it will populate the rest correctly.

### ❌ "Projects list is wrong"

**What happened:** You made a typo in the project codes, or the list doesn't match what you wanted.

**Fix:** Edit `config.toml` directly:

```bash
# Edit the active list
nano ~/.squirrel/config.toml

# Change this line:
# active = ["WRONG-CODE", "ANOTHER-WRONG"]
# To this:
# active = ["CORRECT-CODE-A", "CORRECT-CODE-B"]
```

Save and restart Claude Code.

---

## Where to go next

- **Ready to use Squirrel?** → Read [First 10 Minutes](./first-10-minutes.md) to capture your first note and complete the full loop.
- **Want to understand the PARA system?** → See the Glossary in the [main guide](./getting-started.md#11-glossary).
- **Using two computers?** → Skip ahead to [Two Computers](./two-computers.md) after your first week.

You're all set. Time to capture your first idea. 🐿️
