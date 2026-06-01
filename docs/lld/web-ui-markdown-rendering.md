# Web UI Markdown Rendering — Low-Level Design

## Architecture

A single `<Markdown>` component wraps `react-markdown`, configured once with `remark-gfm` and a small `components` override map that rewrites `<a>` to either a `react-router-dom` `<Link>` (internal hrefs) or a sandboxed `<a target="_blank" rel="noreferrer">` (external hrefs). The two existing read views drop their `marked.parse` calls and render `<Markdown>{body}</Markdown>` inside the same `prose` wrapper they already use.

```
[NotePage]    apps/backend/app/src/pages/NotePage.tsx
   └ <div className="prose prose-slate ..."><Markdown>{note.body}</Markdown></div>

[ProjectPage] apps/backend/app/src/pages/ProjectPage.tsx
   └ <div className="prose prose-slate ..."><Markdown>{project.body}</Markdown></div>
                         │
                         ▼
[Markdown]    apps/backend/app/src/components/Markdown.tsx
   └ <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ a: LinkRenderer }}>
       {children}
     </ReactMarkdown>
       │
       ├─ internal href (starts with "/" or "#")  → <Link to={href}>...</Link>
       └─ external href                            → <a target="_blank" rel="noreferrer">...</a>
```

### Dependency changes

`apps/backend/app/package.json`:
- **Add:** `react-markdown` (^9), `remark-gfm` (^4).
- **Remove:** `marked` (^15).
- No change to `@mdxeditor/editor` — it stays for the editing pipeline.

### New component

`apps/backend/app/src/components/Markdown.tsx`:

```tsx
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Link } from 'react-router-dom';
import type { ComponentProps } from 'react';

type Props = { children: string };

export function Markdown({ children }: Props) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        a: ({ href, children, ...rest }: ComponentProps<'a'>) => {
          const target = href ?? '';
          const isInternal = target.startsWith('/') || target.startsWith('#');
          if (isInternal) {
            return <Link to={target}>{children}</Link>;
          }
          return (
            <a href={target} target="_blank" rel="noreferrer" {...rest}>
              {children}
            </a>
          );
        },
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
```

### Callsite migration

`apps/backend/app/src/pages/NotePage.tsx`:
- Remove `import { marked } from 'marked';`.
- Add `import { Markdown } from '@/components/Markdown';`.
- Replace lines 68–75 (the `note.body ? <div dangerouslySetInnerHTML=... /> : <p>...</p>` block) with:
  ```tsx
  {note.body ? (
    <div className="prose prose-slate max-w-none text-sm leading-relaxed">
      <Markdown>{note.body}</Markdown>
    </div>
  ) : (
    <p className="text-ink-3 italic">This note is empty.</p>
  )}
  ```

`apps/backend/app/src/pages/ProjectPage.tsx`:
- Remove `import { marked } from 'marked';`.
- Add `import { Markdown } from '@/components/Markdown';`.
- Replace lines 95–104 (the `project.body ? <div dangerouslySetInnerHTML=... /> : <p>...</p>` block) with:
  ```tsx
  {project.body ? (
    <div className="prose prose-slate max-w-none text-sm leading-relaxed">
      <Markdown>{project.body}</Markdown>
    </div>
  ) : (
    <p className="text-ink-3 italic">No description yet.</p>
  )}
  ```

The outer `prose prose-slate max-w-none text-sm leading-relaxed` class stays on the wrapper `<div>` so Tailwind Typography continues to style the rendered tree. `<Markdown>` does not add its own wrapper.

### No backend changes

The Python backend, Tauri Rust process, CLI, and daemon are untouched. The vault stores markdown as plain strings; only the client-side render path changes.

## Constraints

- **No `dangerouslySetInnerHTML` in the new render path.** Adding `rehype-raw` (or any equivalent) is explicitly disallowed — it re-enables raw HTML injection and undoes the security gain. If a future need for HTML inside markdown bodies arises, it must come with a sanitizer (e.g. `rehype-sanitize`) and a separate design review.
- **Internal-link detection is intentionally simple** (`startsWith('/')` or `startsWith('#')`). This matches the vault's link conventions; if richer link semantics are needed later (e.g. `mailto:`, custom schemes), the renderer override is the single place to extend.
- **Visual parity must be preserved** — the `prose prose-slate max-w-none text-sm leading-relaxed` wrapper stays on the outer `<div>` at both callsites; the `<Markdown>` component does not introduce its own wrapper element.
- **No code-fence highlighting in v1.** Fenced blocks render as `<pre><code>` and inherit Tailwind Typography defaults; adding a highlighter is a separate change with its own bundle-size tradeoff.
- **Bundle size acceptable.** `react-markdown` + `remark-gfm` (~80–100 KB gzipped) replaces `marked` (~30 KB). The web UI is shipped from a local backend to a local user; size budget is not a constraint.

## Key Decisions

- **Single shared component over inline `<ReactMarkdown>` at each callsite** — keeps plugin choice, link policy, and the security posture in one file. If a third read view needs markdown later, it drops in `<Markdown>` without rediscovering the configuration.
- **`remark-gfm` in v1** — vault content is GitHub-flavored markdown by convention (task lists, tables, autolinks already appear in notes). Shipping without GFM would visibly regress current notes.
- **No `rehype-raw`** — see Constraints; XSS surface reduction is one of the explicit goals of the migration.
- **Link rewrite via `components.a`, not a remark plugin** — the rewrite is a presentation concern (route via SPA), not a syntactic transform. A `components` override is the smallest correct hook.
- **External links open in new tab with `rel="noreferrer"`** — matches existing conventions in the web UI and prevents tab-napping on user-authored links.
- **Editing pipeline untouched** — `MDXEditor` is a richer authoring surface (toolbar, source toggle, embedded plugins). Swapping it would be a separate change with its own UX impact; this design is read-view-only.

## Out of Scope

- Syntax highlighting for fenced code blocks.
- Math / mermaid / footnotes / admonitions and other plugins beyond `remark-gfm`.
- Raw HTML support inside markdown bodies.
- Migration of the `MDXEditor`-based authoring surfaces.
- Server-side markdown rendering or pre-parsing.
- Read views that do not currently render markdown (`DeadlinesPage`, `HistoryPage`, settings, etc.).
- Custom link schemes (`mailto:`, `obsidian://`, vault-internal `[[wikilinks]]`).
