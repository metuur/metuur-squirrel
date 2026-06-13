# Web UI Guide Page — High-Level Design

> _Backfilled from the as-built `apps/backend/app/src/pages/GuidePage.tsx`
> (shipped v0.7.26, FAQ section added shortly after)._

## Overview

Squirrel meets the user on four surfaces — the coding agent (slash commands), the
native desktop app + menu-bar icon, this Web UI, and the `squirrel` CLI — each with
its own vocabulary and affordances. New users had no single in-app place to learn
how the pieces fit, what the core concepts mean, or how to handle common snags
(Gatekeeper, "Backend offline", non-clickable notifications).

This change adds a **self-contained, searchable Guide page** in the Web UI: core
concepts (with two schematic illustrations), where configuration lives, a typical
day, every agent slash command, the desktop popup and menu-bar features, the CLI
commands, the Web UI tour, the dashboard board/list explainer, and a FAQ. A sticky
search box filters every section live; a quick-jump sub-sidebar navigates sections
when not searching. The same content is reachable in-app from the popup's "?" and
the tray's "How to use Squirrel".

## Stakeholders & Impact

- **New user:** learns Squirrel's model and commands without leaving the app or
  reading a website; the FAQ answers the most common install/troubleshooting
  questions inline.
- **Desktop popup & tray:** their "?" / "How to use Squirrel" entries deep-link
  here, so help is one click from anywhere.
- **Docs maintenance:** the command/FAQ content mirrors `agent-pack/commands/` and
  the CLI; it is static page data, not fetched, so it ships with the build.

## Goals

- One in-app page that explains concepts, configuration, the daily flow, and every
  command across all four surfaces.
- Live, client-side search across every section with a visible match count and a
  clear empty state.
- Section-at-a-time reading via a quick-jump sub-sidebar; search overrides the
  selection and sweeps all sections.
- Content mirrors the real commands (`agent-pack/commands/`, `apps/cli/squirrel`)
  so the guide stays truthful to what ships.

## Non-Goals

- No server round-trip: the guide is static page data, not a backend resource.
- No editable / user-contributed content.
- No localization this round (English only).
- No deep-linking to individual subsections via URL (the sub-sidebar is in-page
  state, not routed).

## Success Criteria

1. The Guide route renders all sections: Concepts, Configuration, A typical day,
   Agent commands, Desktop popup, Menu bar, CLI, Web UI, Dashboard, FAQ.
2. Typing in the search box filters every section simultaneously, shows an
   `N matches` count, and shows a "Nothing matches" empty state at zero.
3. Selecting a quick-jump chip shows just that section and scrolls to top; clearing
   search restores single-section navigation.
4. Each command row expands to show what it does and a concrete example; FAQ rows
   expand to their answer.
5. The popup "?" and tray "How to use Squirrel" open this same guide.
