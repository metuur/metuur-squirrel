# Squirrel — Messaging Kit

> Source: `.uncle-dev/research/2026-06-04-squirrel-golden-circle-why-how-what.md`
> Contents: long-form post · README intro · LinkedIn post · elevator pitch

---

## 1. Long-form post

### Squirrel: working memory for the ADHD engineer who keeps too many tabs open in their head

If you have ADHD and you write software, you already know the real bug isn't in your code. It's in the handoff between *you yesterday* and *you today*. You close the laptop mid-thought. You switch from the work repo to the side project to the visa paperwork. Your AI agent forgets the entire conversation the moment the session ends. And somewhere in that churn, a decision evaporates, a deadline slips quietly past, and a brilliant idea gets stranded on the wrong machine.

That gap is what Squirrel exists to close.

**The why.** Squirrel is the durable working memory and attention-support layer for engineers with ADHD who juggle many projects across separate, air-gapped environments. The goal is simple and stubborn: *no context lost between sessions, no decision forgotten, no deadline silently slipped, no thought trapped on the wrong machine.* It is deliberately **not** a project-management SaaS, not a cloud-synced notes app, not an automatic sync robot. The human stays the deliberate bridge — always. This isn't productivity folklore, either; the design leans on attention research (Barkley; Hallowell & Ratey's *ADHD 2.0*; Leroy on context-switching cost; Mark et al. on interrupted work; Ashinoff & Abu-Akel on hyperfocus) layered on top of GTD, PARA, and Deep Work.

**The how.** Squirrel is opinionated on purpose:

- **Local-first, no cloud, no auth.** Everything runs on `127.0.0.1:3939`. Going on the network is an explicit opt-in, never the default. Privacy isn't a setting you find — it's the floor you start on.
- **Markdown is the source of truth.** Your state lives in plain `.md` files you can open in Obsidian, grep from a terminal, and version with Git. No proprietary database holding your brain hostage. (Where history genuinely matters — focus and time tracking — a local SQLite store handles the log, while frontmatter stays the truth for *current* state.)
- **Air-gap by design.** Moving context between your personal and corporate worlds happens through hash-verified, self-contained Markdown packages *you* paste — diffed against your vault and applied atomically, with zero network calls. The human is the bridge, by construction.
- **It lives inside your AI agents.** Squirrel ships *into* Claude Code, Codex, Cursor, Copilot, and Windsurf as portable skills and `/sq-*` commands — not as one more cloud API you have to authenticate against.
- **Scripts do the math, the LLM does the judgment.** Deterministic work (parsing, aggregation, classification, hashing) runs in local Python and emits JSON. The model only reasons over the result — which cuts a typical one-hour session from ~25K to ~10K tokens.
- **Proactive, not passive.** It asks. The standout is the Mind Journal: every four hours it nudges, *"What is your mind thinking right now?"* and *"What are you doing right now?"* with a one-tap mood. For an ADHD brain, externalizing the transient state is the whole game.

**The what.** One vault, five surfaces:

- A **macOS menu-bar popup** (Tauri v2 + React) — summon it from anywhere with `Ctrl+Cmd+S`, pick your AM/PM/week focus, see what's pressing, log the Mind Journal, get native notifications.
- A **`squirrel` CLI** (pure Python stdlib) — `status`, `deadlines`, `chunk`, `estimate`, `recover`, and more.
- A **local web UI + API** on `:3939` — projects, notes, deadlines, history, journal, search, settings.
- **AI-agent skills** — ~22 `/sq-*` commands and ~15 skills (including a `hyperfocus-guardian`) across five agents.
- A **macOS reminders daemon** — native banners that deep-link straight back to the right card.

It installs two ways: **Squirrel.app**, a tray popup with a backend it supervises itself (no terminal), or a **full installer** with the CLI plus agent integration for power users.

Squirrel won't manage you. It remembers *for* you, so the version of you that shows up tomorrow doesn't have to reconstruct the version that logged off today.

---

## 2. README intro

> **Squirrel** — local-first working memory for engineers with ADHD.

Squirrel is the durable context and attention-support layer for engineers who juggle many projects across separate, air-gapped environments — so no context is lost between sessions, no decision is forgotten, no deadline silently slips, and no thought is trapped on the wrong machine.

It's **local-first** (everything runs on `127.0.0.1`, no cloud, no auth), **Markdown-native** (your state is plain `.md` files you can open in Obsidian, grep, and version with Git), and it lives **inside your AI agents** — Claude Code, Codex, Cursor, Copilot, and Windsurf — as portable `/sq-*` skills rather than yet another cloud API. Deterministic work runs in local scripts and the LLM only handles judgment, so a typical session costs a fraction of the tokens.

One vault, five surfaces: a macOS menu-bar popup, a `squirrel` CLI, a local web UI + API, AI-agent skills, and a native reminders daemon. The human is always the deliberate bridge — Squirrel just makes sure nothing falls through it.

---

## 3. LinkedIn post

If you have ADHD and write code, the hardest bug isn't in your code. It's in the handoff between *you yesterday* and *you today*. 🐿️

You close the laptop mid-thought. You bounce from the work repo to a side project to life admin. Your AI agent forgets everything the second the session ends. And a decision, a deadline, or a good idea quietly disappears.

I've been building **Squirrel** to close that gap — a local-first working-memory layer for engineers with ADHD.

What makes it different:

🔒 **Local-first.** Runs entirely on your machine. No cloud, no account, no auth. Privacy is the default, not a setting.

📝 **Markdown is the source of truth.** Your state lives in plain files you can open in Obsidian, grep, and commit to Git. Nothing locked in a database.

🤖 **It lives inside your AI agents.** Claude Code, Codex, Cursor, Copilot, Windsurf — Squirrel ships as `/sq-*` skills, not one more API to log into. Scripts do the math; the model only does the judgment (≈2.5× fewer tokens per session).

🧠 **It's proactive.** Every few hours it asks: *"What is your mind thinking right now? What are you doing right now?"* — because externalizing the transient state is the whole game for an ADHD brain.

It explicitly does NOT try to become a project-management SaaS or a cloud sync robot. The human stays the deliberate bridge. Squirrel just makes sure nothing falls through.

Built on attention research (Barkley, *ADHD 2.0*, Leroy on context-switching) — not productivity folklore.

Curious how others handle context loss across projects. What's your system? 👇

#ADHD #SoftwareEngineering #LocalFirst #DeveloperTools #Productivity #AI

---

## 4. Elevator pitch (one paragraph)

Squirrel is a local-first working-memory companion for engineers with ADHD who juggle many projects across separate environments — so no context is lost between sessions, no decision is forgotten, no deadline silently slips, and no thought gets stranded on the wrong machine. It keeps your state in plain Markdown files you own (no cloud, no auth, everything on `127.0.0.1`), lives directly inside your AI agents (Claude Code, Codex, Cursor, Copilot, Windsurf) as `/sq-*` skills, and proactively nudges you with focus picks and a four-hour mind-and-mood check-in. It deliberately refuses to be a SaaS or a sync robot — the human is always the deliberate bridge, and Squirrel just makes sure nothing falls through it.
