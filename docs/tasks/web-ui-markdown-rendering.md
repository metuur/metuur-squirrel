# Web UI Markdown Rendering — Tasks

Source specs: `docs/hld/web-ui-markdown-rendering.md`, `docs/lld/web-ui-markdown-rendering.md`, `docs/ears/web-ui-markdown-rendering.md`.
Scope is the Squirrel Web UI (`apps/backend/app/`) read views only — the `MDXEditor` authoring pipeline is untouched (R-6.1), and no Python/Rust/CLI/daemon changes (R-6.2).

> Back-filled after implementation. All units are checked because the migration already shipped on this branch (`Markdown.tsx` exists, both read views use it, `marked` removed, `react-markdown` + `remark-gfm` added).

Dependency layers (LLD build sequence: deps → component → callsites → cleanup):
```
A.1 (package.json: + react-markdown + remark-gfm)
        │
       B.1 (Markdown.tsx — react-markdown + remark-gfm + link policy)
        │
   ┌────┴────┐
  C.1       C.2
 (NotePage) (ProjectPage)
        └────┬────┘
            D.1
     (remove marked + verify build)
```

---

## Unit A: Dependencies — `apps/backend/app/package.json`

- [x] **A.1** Add `react-markdown` + `remark-gfm` runtime deps (est: ~10m)
  - acceptance:
    - R-5.1 — `react-markdown` and `remark-gfm` declared as runtime dependencies.
    - No change to `@mdxeditor/editor` — it stays for the editing pipeline.
  - verify:
    - `pnpm install` resolves; `package.json` shows both deps (`react-markdown ^10`, `remark-gfm ^4`).

## Unit B: Shared component — `apps/backend/app/src/components/Markdown.tsx` (new)

- [x] **B.1** `<Markdown>` component with GFM + link policy (deps: A.1, est: ~35m)
  - acceptance:
    - R-1.1 / R-1.2 — Accepts a single `children: string` prop and renders it through `react-markdown` configured with `remark-gfm`, producing a React tree with **no** `dangerouslySetInnerHTML`.
    - R-1.3 — Introduces no wrapping DOM element of its own (styling stays the caller's responsibility).
    - R-1.4 — Does **not** enable raw-HTML passthrough (no `rehype-raw`).
    - R-2.1 — A link `href` starting with `/` or `#` renders as a `react-router-dom` `<Link to={href}>`.
    - R-2.2 — Any other `href` renders as `<a target="_blank" rel="noreferrer">`.
    - R-2.3 — Visible link text is preserved unchanged for both variants.
    - R-3.1–R-3.4 — GFM tables → `<table>`, task lists → checkboxes, `~~text~~` → `<del>`, bare URLs autolink as external links.
  - verify:
    - Vitest: internal href renders a `<Link>` (no full reload), external href renders `target="_blank" rel="noreferrer"`; a GFM table/task-list/strikethrough/autolink each render as expected; assert no `dangerouslySetInnerHTML` in the tree.

## Unit C: Read-view migration

- [x] **C.1** `NotePage` renders `note.body` via `<Markdown>` (deps: B.1, est: ~15m)
  - acceptance:
    - R-4.1 — `note.body` renders via `<Markdown>` inside the existing `prose prose-slate max-w-none text-sm leading-relaxed` wrapper.
    - R-4.3 — Empty/falsy/whitespace-only `note.body` keeps the `<p class="text-ink-3 italic">This note is empty.</p>` placeholder.
  - verify:
    - Vitest/manual: a populated note renders markdown under `prose`; an empty note shows the placeholder; internal links navigate within the SPA.

- [x] **C.2** `ProjectPage` renders `project.body` via `<Markdown>` (deps: B.1, est: ~15m)
  - acceptance:
    - R-4.2 — `project.body` renders via `<Markdown>` inside the same `prose ...` wrapper.
    - R-4.4 — Empty/falsy/whitespace-only `project.body` keeps the `<p class="text-ink-3 italic">No description yet.</p>` placeholder.
  - verify:
    - Vitest/manual: populated project body renders markdown; empty body shows the placeholder.

## Unit D: Cleanup & build

- [x] **D.1** Remove `marked`, confirm no raw-HTML injection, green build (deps: C.1, C.2, est: ~15m)
  - acceptance:
    - R-4.5 — Neither `NotePage` nor `ProjectPage` imports `marked` or uses `dangerouslySetInnerHTML`.
    - R-5.2 — `marked` removed from `apps/backend/app/package.json`.
    - R-5.3 — `pnpm --filter squirrel-web-ui build` and `type-check` succeed with no new errors.
    - R-6.3 — No syntax highlighting, math, mermaid, footnotes, or plugins beyond `remark-gfm`.
  - verify:
    - `grep -r "marked\|dangerouslySetInnerHTML" apps/backend/app/src/pages/{NotePage,ProjectPage}.tsx` → no matches; `grep '"marked"' package.json` → none; `pnpm --filter squirrel-web-ui build && pnpm --filter squirrel-web-ui type-check` pass.
