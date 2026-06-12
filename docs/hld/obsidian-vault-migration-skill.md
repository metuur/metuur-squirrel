# Obsidian → squirrel-vault Migration — High-Level Design

> _Backfilled from the as-built implementation (`apps/cli/lib/vault_migrator.py`,
> shipped v0.7.26). The forward artifact is `docs/tasks/obsidian-vault-migration-skill.md`;
> this HLD/LLD/EARS chain documents the same scope after the fact._

## Overview

New Squirrel users almost always arrive with an existing Obsidian (or plain
Markdown) vault whose folder layout does not match Squirrel's structured
conventions (`01-Active-Projects/`, `02-Parking-Lot/`, `99-Resources/Inbox/`,
`04-Daily/`, …). Asking them to hand-reorganize dozens of notes is the kind of
friction that loses an ADHD user before they ever see value.

This change adds a **two-phase, copy-only migration engine** that scans a source
vault, maps each note to a Squirrel target by heuristic, shows a **dry-run plan**
for confirmation, and only then writes converted notes into the Squirrel vault.
The source vault is **never modified**. It ships as a CLI module
(`vault_migrator.py`) plus an agent skill/command (`/sq-migrate-vault`), and is
the action the desktop popup's `VAULT_UNSTRUCTURED` recovery step points users to
(see `docs/hld/desktop-vault-recovery.md`).

## Stakeholders & Impact

- **New user with an existing vault:** runs one command, reviews a plan, and gets
  their notes reorganized into Squirrel format without touching the original —
  the original folder stays intact as a fallback.
- **Desktop popup recovery flow:** the `VAULT_UNSTRUCTURED` state hands the user
  the exact `/sq-migrate-vault <path>` command, so migration is reachable without
  reading docs.
- **Code readers (`status_aggregator`, scanners):** migrated projects land in the
  folders those readers already expect, so the result is immediately visible to
  every Squirrel surface with no extra indexing step.
- **No external consumers:** local-only, no network, no telemetry.

## Goals

- Convert an existing vault into Squirrel layout with a single command, copy-only.
- The source vault is byte-for-byte untouched after a migration.
- Show a reviewable plan before any write; apply only on explicit confirmation.
- Migration is **re-runnable**: applying twice never overwrites or duplicates —
  existing target files are skipped and reported.
- Migrated projects, tasks, captures, and dailies are immediately visible to
  `aggregate_status()` and the vault scanners.

## Non-Goals

- No in-place reorganization (move/rename) of the source vault — copy only.
- No two-way sync or ongoing mirroring; this is a one-shot import.
- No content rewriting beyond frontmatter normalization and required-field
  injection (wikilinks, body prose, and attachments are copied verbatim).
- No conflict-merge UI — if a target file already exists, it is skipped, not
  merged.
- No non-macOS-specific concerns; the engine is pure Python and platform-neutral,
  but it ships inside the macOS CLI bundle this round.

## Success Criteria

1. **Source untouched:** after `plan` + `apply`, a checksum of every source file
   is unchanged.
2. **Correct mapping:** a top-level folder with notes becomes a project under
   `02-Parking-Lot/<TAG>/` (or `01-Active-Projects/` with `--dest active`); its
   folder-note becomes the project page body; other notes flatten to
   `<TAG>-NOTE-NNN.md` intents; daily folders copy to `04-Daily/`; loose root
   notes become `99-Resources/Inbox/UNFILED-NNN.md`; attachments copy to
   `99-Resources/Obsidian-Attachments/`.
3. **Idempotent apply:** running `apply` twice on the same plan writes zero new
   files the second time and reports each as skipped.
4. **Refuses bad sources:** a source that is missing, equals the target, or is
   already a Squirrel vault exits non-zero with a documented code without writing.
5. **Visible result:** after apply, `aggregate_status()` lists the migrated
   projects in the `parking` bucket.
