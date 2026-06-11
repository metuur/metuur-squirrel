---
name: squirrel-changelog
description: Generate a user-facing changelog for Squirrel from git history — translating technical commits into clear feature/improvement/fix entries grouped by surface (CLI, Desktop app, Web UI). Use when the user says "update the changelog", "write release notes", "what changed in this release", "changelog for v0.x", "generate the changelog", "draft release notes", or before tagging/shipping a version. Drafts assisted (you review before it writes) and writes to the root CHANGELOG.md in Keep a Changelog format. Focus is on what changed for the user, not code-level churn.
---

# squirrel:changelog

## Purpose

Turn Squirrel's git history into a changelog a **user** understands — someone
running the menu-bar app, the CLI, or the Web UI — not an engineer reading
diffs. Every entry answers "what changed for me?" Code-level churn (refactors,
test fixes, graphify refreshes, version bumps, audit-ID cleanups) is dropped.

This is **assisted**: scan → draft → you review/trim → write. Never write the
file without a review pause unless told to.

## Core principle

Translate the **mechanism** (commit) into the **outcome** (changelog line):

| Commit (code-focused) | Changelog entry (user-focused) |
|---|---|
| `fix(cli): timezone-aware datetimes across scanners` | Reminders now fire at the correct local time across timezones |
| `feat(web-ui): add Guide page with how-to docs` | New in-app Guide explaining the desktop app and menu-bar icon |
| `fix(desktop): tray notification hardening` | Menu-bar notifications are more reliable |
| `fix(tray): redact runtime token from URL log lines` | Hardened: runtime tokens are no longer written to logs |
| `chore: refresh graphify knowledge graph` | *(dropped — no user impact)* |

If you can't state why a user would care, the line doesn't belong.

## Procedure

### 1. Determine the range
- Find the last released version: `git tag --sort=-creatordate | head -1`
  (fall back to "since the last `## [x.y.z]` header in CHANGELOG.md").
- Target version: read `package.json` → `version` (currently the working
  version). Confirm with the user if ambiguous.
- Collect commits: `git log <last-tag>..HEAD --pretty="%s%n%b%n---"`.

### 2. Draft
- Read each commit subject + body. Categorize using the rules below — group by
  surface, then by impact. Translate every line from mechanism to outcome.

### 3. Filter noise (drop these entirely)
See `references/voice.md` for the full list. Always drop:
`chore:`, `test:`, `ci:`, `build:` (unless it changes what users install),
`refactor`/"Refactor code structure", graphify commits, `version to`/`bump
to` commits, `.graphify_extract.json` adds, and audit-ID-only fixes where the
user-visible effect is nil.

### 4. Group by surface, then by impact
Map each surviving commit to one surface using the scope (see voice.md):

- **⌨️ CLI** — `cli`, `installer`, `build-pkg`, `migrate-vault`
- **🖥 Desktop app** — `desktop`, `tray`, `notif-branding`, `reminder-daemon`
- **🌐 Web UI** — `web-ui`, `backend`, `guide`
- **✨ General** — `onboarding`, `projects`, unscoped product changes

Within each surface, bucket by Keep a Changelog impact:
`Added` / `Changed` / `Fixed` / `Security` / `Removed`.

### 5. Write the entry (Keep a Changelog format)
- Newest version on top, under `## [Unreleased]` if not yet tagged.
- Surface as `### 🖥 Desktop app`; impact as `**Added**` / `**Fixed**` inline
  bold lead-ins, or sub-bullets — match the existing CHANGELOG.md style.
- Each line: benefit-first, one sentence, no PR numbers, no author names, no
  audit IDs (M6/H2/etc.), no commit hashes.
- 3–8 lines per version is healthy. If a surface has nothing user-facing,
  omit it — don't pad.
- Voice: short, scannable, ADHD-friendly (matches Squirrel's other skills).
  See `references/highlights_examples.md` for tone.

### 6. Finalize
- Write to root `CHANGELOG.md`. Keep the `[Unreleased]` running section at the
  top for the next cycle.
- Show the user the diff and confirm before committing.

## Output format (root CHANGELOG.md)

```markdown
## [0.7.26] — 2026-06-11

### 🖥 Desktop app
- Menu-bar notifications are more reliable
- **Security:** runtime tokens are no longer written to logs

### ⌨️ CLI
- Reminders fire at the correct local time across timezones
- Vault paths with spaces now install correctly

### 🌐 Web UI
- **Added:** in-app Guide covering the desktop app and menu-bar icon
- Stale background responses no longer overwrite newer data
```

## References
- `references/voice.md` — noise-filter list, scope→surface map, tone rules
- `references/highlights_examples.md` — few-shot examples of good highlights
