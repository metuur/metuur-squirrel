# @squirrel/design-system

CSS-only design system for the Squirrel apps. Tokens, themes, primitives,
and component recipes — consumed today by `@squirrel/desktop` (Tauri popup)
and, in a future change, by the web SPA at `apps/backend/app/`.

## Usage

```css
/* In the consuming app's entry CSS: */
@import "@squirrel/design-system";
```

Activate a theme by setting the attribute on the document root:

```html
<html data-theme="paper-indigo">
```

## Anatomy

| File                              | Purpose                                                            |
|-----------------------------------|--------------------------------------------------------------------|
| `src/index.css`                   | Public entry — imports everything below in cascade-layer order     |
| `src/tokens.css`                  | `@theme` block — canonical token names + Tailwind utility generation |
| `src/themes/paper-indigo.css`     | Concrete values under `[data-theme="paper-indigo"]`                |
| `src/primitives.css`              | `@font-face`, body chrome, dot grid, `.accent-line`                |
| `src/recipes.css`                 | `.panel`, `.card`, `.btn`, `.chip`, `.stripe-*`, typography helpers, motion |

## Adding a new theme

1. Create `src/themes/<name>.css`.
2. Override the `--color-*` tokens under `[data-theme="<name>"]`.
3. Wire the import into `src/index.css` (inside `@layer theme`).
4. Switch the consuming app's `<html data-theme>` to the new name.

The component recipes consume tokens via `var(--color-*)`, so a theme swap
is a CSS-only change — no React/Tauri rebuild required.

## Source specs

- `docs/hld/desktop-theme-architecture.md` — High-Level Design
- `docs/lld/desktop-theme-architecture.md` — Low-Level Design
- `docs/ears/desktop-theme-architecture.md` — EARS requirements
