# Web UI Markdown Rendering — EARS Specifications

## Unit 1: Shared rendering component

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | THE SYSTEM SHALL expose a `Markdown` React component at `apps/backend/app/src/components/Markdown.tsx` that accepts a single `children: string` prop containing markdown source. |
| R-1.2 | THE `Markdown` component SHALL render its input by passing it through `react-markdown` configured with `remark-gfm`, producing a React element tree with no use of `dangerouslySetInnerHTML`. |
| R-1.3 | THE `Markdown` component SHALL NOT introduce a wrapping DOM element of its own; styling SHALL remain the responsibility of the caller's surrounding container. |
| R-1.4 | THE SYSTEM SHALL NOT enable raw-HTML passthrough (e.g. via `rehype-raw`) in the `Markdown` component. |

## Unit 2: Link handling

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | WHEN the markdown source contains a link whose `href` begins with `/` or `#`, THE `Markdown` component SHALL render it as a `react-router-dom` `<Link>` with `to` equal to the original `href`. |
| R-2.2 | WHEN the markdown source contains a link whose `href` does not begin with `/` or `#`, THE `Markdown` component SHALL render it as an `<a>` element with `target="_blank"` and `rel="noreferrer"`. |
| R-2.3 | THE `Markdown` component SHALL preserve the link's visible text content unchanged for both internal and external link variants. |

## Unit 3: GitHub-flavored markdown features

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | WHEN the markdown source contains a GFM table, THE `Markdown` component SHALL render it as a semantic `<table>` element tree. |
| R-3.2 | WHEN the markdown source contains a GFM task list item (`- [ ]` or `- [x]`), THE `Markdown` component SHALL render a checkbox reflecting the checked/unchecked state. |
| R-3.3 | WHEN the markdown source contains `~~text~~`, THE `Markdown` component SHALL render it as `<del>text</del>`. |
| R-3.4 | WHEN the markdown source contains a bare URL such as `https://example.com`, THE `Markdown` component SHALL render it as an external link per R-2.2 (GFM autolink behaviour). |

## Unit 4: Read-view migration

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | THE SYSTEM SHALL render `note.body` on `apps/backend/app/src/pages/NotePage.tsx` via the `Markdown` component, inside a wrapping `<div>` retaining the existing `prose prose-slate max-w-none text-sm leading-relaxed` class. |
| R-4.2 | THE SYSTEM SHALL render `project.body` on `apps/backend/app/src/pages/ProjectPage.tsx` via the `Markdown` component, inside a wrapping `<div>` retaining the existing `prose prose-slate max-w-none text-sm leading-relaxed` class. |
| R-4.3 | WHEN `note.body` is empty, falsy, or whitespace-only, `NotePage` SHALL render the existing `<p class="text-ink-3 italic">This note is empty.</p>` placeholder instead of invoking `Markdown`. |
| R-4.4 | WHEN `project.body` is empty, falsy, or whitespace-only, `ProjectPage` SHALL render the existing `<p class="text-ink-3 italic">No description yet.</p>` placeholder instead of invoking `Markdown`. |
| R-4.5 | NEITHER `NotePage` NOR `ProjectPage` SHALL import `marked` or use `dangerouslySetInnerHTML` after this change. |

## Unit 5: Dependencies & build

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | THE SYSTEM SHALL declare `react-markdown` and `remark-gfm` as runtime dependencies in `apps/backend/app/package.json`. |
| R-5.2 | THE SYSTEM SHALL remove `marked` from `apps/backend/app/package.json` once both read-view callsites have been migrated. |
| R-5.3 | THE web UI build (`pnpm --filter squirrel-web-ui build`) and type-check (`pnpm --filter squirrel-web-ui type-check`) SHALL succeed with no new errors after the migration. |

## Unit 6: Scope boundary

| ID    | EARS statement |
|-------|----------------|
| R-6.1 | THE SYSTEM SHALL NOT modify the markdown authoring pipeline (`MDXEditor` and its callsites in `NoteEditPage`, `ProjectEditPage`, `CaptureModal`, `NewProjectModal`, `NewTaskModal`) as part of this change. |
| R-6.2 | THE SYSTEM SHALL NOT modify the Python backend, Tauri Rust process, CLI, or reminders daemon as part of this change; vault bodies SHALL continue to be stored and served as plain markdown strings. |
| R-6.3 | THE SYSTEM SHALL NOT add syntax highlighting, math, mermaid, footnotes, or remark/rehype plugins beyond `remark-gfm` as part of this change. |
