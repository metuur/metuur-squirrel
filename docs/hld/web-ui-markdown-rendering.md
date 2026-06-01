# Web UI Markdown Rendering — High-Level Design

## Overview

The Squirrel Web UI (`apps/backend/app/`) currently renders persisted note and project bodies by parsing markdown with `marked` and injecting the result through `dangerouslySetInnerHTML` at two sites: `pages/NotePage.tsx` and `pages/ProjectPage.tsx`. This change replaces those two render sites with a single shared `<Markdown>` component built on `react-markdown` + `remark-gfm`, eliminating the raw-HTML injection, enabling SPA-routed internal links, and standardising the read-view rendering pipeline. Editing flows continue to use `MDXEditor` and are out of scope.

## Stakeholders & Impact

- **User (Javier):** Sees the same markdown content, but internal links (e.g. `[task](/projects/foo)`) now stay inside the SPA instead of triggering a full reload, and external links open in a new tab with `rel="noreferrer"`. GitHub-flavored markdown features (tables, task lists, strikethrough, autolinks) render consistently across both read views.
- **No other consumers.** The Tauri desktop shell does not render note/project bodies — it embeds the same web UI via the existing HTTP backend; no separate change is needed there.

## Goals

- Replace `marked.parse(...)` + `dangerouslySetInnerHTML` at the two existing render sites with a shared `<Markdown>` component that returns a React tree.
- Support GitHub-flavored markdown (tables, task lists, autolinks, strikethrough) without per-callsite configuration.
- Route in-app links (`/notes/...`, `/projects/...`, `#anchor`) through `react-router-dom`'s `<Link>` instead of full-page navigation.
- Open external links in a new tab with `target="_blank" rel="noreferrer"`.
- Preserve the existing visual styling (the `prose prose-slate max-w-none text-sm leading-relaxed` wrapper continues to scope Tailwind Typography).
- Remove the `marked` dependency once both callsites are migrated.

## Non-Goals

- No change to the editing pipeline — `MDXEditor` continues to handle authoring in `NoteEditPage`, `ProjectEditPage`, `CaptureModal`, `NewProjectModal`, `NewTaskModal`.
- No raw HTML support inside markdown bodies (no `rehype-raw`) — the security gain from dropping `dangerouslySetInnerHTML` would be undone otherwise.
- No syntax highlighting for fenced code blocks in v1 — fenced blocks render as plain `<pre><code>` and inherit `prose` styling.
- No math, mermaid, footnotes, or other remark/rehype plugins beyond `remark-gfm` in v1.
- No change to how markdown is parsed or stored server-side — bodies remain plain markdown strings in the vault.
- No migration of read views that do not currently render markdown (e.g. `DeadlinesPage`, `HistoryPage`).

## Success Criteria

1. `NotePage` and `ProjectPage` render note/project bodies through `<Markdown>`; neither file imports `marked` or uses `dangerouslySetInnerHTML`.
2. A note body containing `[edit](/notes/abc/edit)` navigates within the SPA (no full reload) when clicked.
3. A note body containing `https://example.com` renders as an `<a target="_blank" rel="noreferrer">`.
4. A note body containing a GFM table, a `- [ ] task list`, and `~~strikethrough~~` renders correctly under the existing `prose` styling.
5. `marked` is removed from `apps/backend/app/package.json` and no longer appears in the build output.
6. The web UI builds (`pnpm --filter squirrel-web-ui build`) and type-checks (`pnpm --filter squirrel-web-ui type-check`) cleanly.
