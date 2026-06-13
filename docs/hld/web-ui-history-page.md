# Web UI Recent-Activity (History) Page — High-Level Design

> _Backfilled from the as-built `apps/backend/app/src/pages/HistoryPage.tsx` and the
> `api_history` handler (`GET /api/history`) in `apps/backend/server.py`._

## Overview

When a user returns to Squirrel after an interruption, the first question is
usually "what was I just touching?". The Web UI needed a low-friction re-entry
point that answers that without making the user remember a project name or scan
the board.

This change adds a **Recent activity page**: a flat, reverse-chronological list of
the most recently modified notes and project pages in the vault, each linking
straight to its detail view. It is a read-only, glanceable index built directly
from file modification times — no separate activity log to maintain.

## Stakeholders & Impact

- **Returning user:** sees the last things they edited across all projects in one
  list and jumps back in with one click.
- **Backend:** serves the list by scanning vault `.md` mtimes; no new persistence.
- **Vault:** treated as the source of truth — recency is file mtime, so anything
  that edits a note (agent, CLI, popup, Obsidian) shows up here.

## Goals

- A single reverse-chronological list of recently touched notes and project pages.
- Each entry links to the correct detail route (project vs. note) and shows a
  relative "time ago".
- Built from file mtimes so it reflects edits from every surface with no extra
  bookkeeping.
- Clear loading and empty states.

## Non-Goals

- No full audit trail or per-edit history (no diffs, no who/when log).
- No pagination or infinite scroll — a fixed recent window is enough.
- No inclusion of Post-its (they have their own board surface).
- No filtering / search on this page (search is its own feature).

## Success Criteria

1. The page lists the most recently modified vault notes and project pages, newest
   first.
2. A project page links to `/projects/<slug>`; a note links to `/notes/<note_id>`.
3. Each row shows a relative timestamp derived from the file's modification time.
4. While loading, a skeleton placeholder shows; with no activity, an explicit
   "Nothing yet." empty state shows.
5. Hidden files and the Post-its directory never appear in the list.
