# Project Name + Tag Auto-generation — High-Level Design

## Overview
Add a human-readable **Name** field to the New Project modal. As the user types, the Tag is auto-derived from the Name (uppercase, dash-separated). The Tag remains editable so users can override the suggestion. This removes the need to manually format a Tag from scratch and makes the form more intuitive.

## Stakeholders & Impact
- **User creating a project**: currently must know and type the Tag format manually. After this ships, they type a natural name and get the Tag for free.
- **API / backend**: receives a new `name` field alongside `tag`. No existing field changes.

## Goals
- Users can enter a free-text project name.
- The Tag field auto-populates from the name as the user types.
- Users can manually edit the Tag to override the auto-derived value.
- Derived Tag always conforms to the existing `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$` format.
- The scaffolded project markdown page opens with `# {name}` as the H1, not `# {tag}`.

## Non-Goals
- No changes to Type A/B/C semantics.
- No changes to Tag validation rules.
- No renaming of existing projects.
- No AI-assisted name suggestions.
- `name` is NOT stored in YAML frontmatter — it is only the markdown H1.

## Success Criteria
- Typing "My Cool App" auto-fills Tag as `MY-COOL-APP`.
- Manually editing Tag breaks the auto-sync (user-overridden state).
- Form cannot be submitted without a valid Tag and Name.
- The generated `MY-COOL-APP.md` file starts with `# My Cool App` (not `# MY-COOL-APP`).
- CLI / legacy callers without a name still render `# {tag}` as before.
