# Web UI (Simple) — High-Level Design

## Overview

A browser-accessed companion for Squirrel designed for **non-technical users**: the project author's spouse, the author themself, and ~60-year-old users who are comfortable with a web browser and an iPad but not with Markdown editors, file trees, terminals, AI chat interfaces, or YAML. The UI exposes only the user-facing concepts (today's focus, projects, deadlines, captures, recent notes) and hides every developer-oriented internal concept (PARA folder names, frontmatter YAML, file paths, vault terminology, multiple vaults if only one is configured, urgency-level taxonomy, tag syntax, wiki-link syntax, backlinks). It runs as a localhost-only HTTP server, ships as plain HTML + small vanilla JS (no build pipeline, no Node.js), and works comfortably on iPad and laptop browsers. AI-augmented features (brief, decision wizard, task-initiation) are an optional add-on in a later milestone; the core product is fully functional without any AI.

## Stakeholders & Impact

- **Primary user — a non-technical adult.** Specifically the project author's spouse and ~60-year-old users. Today they cannot use Squirrel at all: the slash command interface requires Claude Code (terminal, prompts), the CLI is a terminal, Obsidian has a steep mental model (PARA, frontmatter, wiki-links). After this ships they can open a browser, see their day, add a note, and check what's due — in the same time and effort as opening their email.
- **Secondary user — the project author when they want a browser surface.** Same UI works for them; advanced features remain in the slash commands and CLI.
- **Out of audience.** Developers wanting a code-style Markdown editor. They use Obsidian.
- **Out of audience.** Users wanting Squirrel skill operations with AI augmentation in the browser. Optional Milestone D-AI covers this; ship without it for v1.
- **Out of audience.** Users wanting LAN, remote, or multi-device access. Localhost-only.

## Goals

- **G1 — Open the browser, see your day.** The home page loads in under one second and shows: today's focus, items due today/tomorrow, projects, a big "Add a note" button. Nothing else.
- **G2 — One tap to capture.** Any user can add a note from any page in one tap or click. No mandatory project selection — the note can be unfiled and sorted later.
- **G3 — Plain-English vocabulary.** The UI never displays the words "vault", "frontmatter", "PARA", "tag", "wiki-link", "intent", "shutdown note", "parakeet", or `.md`. It uses: "note", "project", "deadline", "today", "history".
- **G4 — No file-system mental model.** No file paths, no folder tree, no extensions visible. Projects are listed by their human name. Notes belong to projects (or are unfiled). That's the entire model.
- **G5 — Touch-first and accessible.** Layout works at iPad width and laptop width. Tap targets are at least 44×44 px. Default font is 18 px or larger. High-contrast colors. Dark mode toggle.
- **G6 — No login.** Localhost only. The user types `http://localhost:3939` (or taps a bookmark / shortcut) and they're in.
- **G7 — No build pipeline, no Node dependency, no React.** The UI is plain HTML pages rendered server-side by a stdlib Python server, with small inline vanilla JavaScript for interactivity (add-note modal, deadline filter, edit-in-place). Anyone with a text editor can read and modify the templates.
- **G8 — Multi-vault aware but invisible by default.** Reads multi-vault config from the underlying core (separate spec). If exactly one vault is configured, the UI shows no vault picker and no "vault" word. If multiple vaults are configured, a single discreet dropdown in the header lets the user switch.
- **G9 — Optional AI proxy (Milestone D-AI).** When the project author configures an Anthropic API key in `~/.squirrel/config.toml`, the UI gains "Generate brief", "Help me decide", and "Help me start" buttons that proxy to the API. Without a key, these buttons do not appear.
- **G10 — Reversible install.** A single command removes the companion files and stops the server. The user's vault is untouched.

## Non-Goals

- **N1 — Obsidian replacement.** No file tree, no CodeMirror, no syntax highlighting, no wiki-link rendering, no backlinks panel, no tag browser, no frontmatter editor, no Dataview rendering.
- **N2 — Power-user features.** No keyboard command palette, no multi-select bulk operations, no side-by-side diff, no merge UI. Editing is single-file, plain text.
- **N3 — AI in the core product.** AI features are an explicit later milestone (D-AI) and entirely optional.
- **N4 — Authentication, LAN, mobile-native app.** Localhost only. Mobile browser supported, native iOS app not.
- **N5 — Real-time collaboration.** Single user, no presence, no operational transforms.
- **N6 — Deleting files.** No delete button in v1. The user removes notes by editing them to empty / moving them out manually.
- **N7 — Vault structure mutations from the UI.** No creating projects, no renaming folders, no moving files between PARA categories from the UI. Project creation happens via `/sq-init --add-vault` or by the user creating a folder in their vault.
- **N8 — Replacing slash commands or the CLI.** Power users keep their existing interfaces. The web UI is additive, not competitive.
- **N9 — Sync operations from the UI.** `sync-out` / `sync-in` are advanced flows with compliance implications. They remain in the slash command and CLI surfaces. The web UI does not expose them.
- **N10 — Tag editing, frontmatter editing, backlink browsing.** All of these are developer-oriented features that confuse the target audience.

## Success Criteria

- **S1.** A new non-technical user, after a 30-second introduction from someone, can open the URL, find today's focus, and add a new note — without help.
- **S2.** The home page (today's focus + deadlines + add-note button) loads in under one second on a five-year-old laptop and on an iPad.
- **S3.** The UI uses no developer vocabulary anywhere a user can see it. A linter check across all rendered HTML rejects the words "vault", "frontmatter", "PARA", "intent", "wiki-link", `.md`, "tag" (in raw form — "topic" or "label" is allowed).
- **S4.** A note added through the UI is visible in the user's Obsidian vault as a normal Markdown file with frontmatter, and is observable by slash commands like `/sq-where-am-i`.
- **S5.** The UI works on a default iPad in Safari with no plugins or extensions, and on Firefox / Chrome / Safari on macOS.
- **S6.** All UI text and key tap targets meet WCAG 2.1 AA contrast and touch-target sizing.
- **S7.** A user with one configured vault never sees the word "vault" or any vault picker.
- **S8.** A user with two or more configured vaults sees one discreet picker in the header; switching it changes the data shown without a full page reload (or with a clean reload — either is acceptable).
- **S9.** Stopping the server (`squirrel web stop` or closing the terminal that launched it) does not affect any other Squirrel command or any vault file.
- **S10.** The server has zero non-stdlib Python dependencies; the frontend has zero JavaScript build artifacts in git.
- **S11.** When no Anthropic API key is configured, the UI shows no AI-related buttons or copy. The user is unaware AI integration is possible.
- **S12.** Removing the companion (`squirrel web uninstall` or `rm -rf companions/web-ui/`) leaves the rest of Squirrel functional.
