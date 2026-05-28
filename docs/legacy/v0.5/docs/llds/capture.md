# LLD: capture

Capture behavior: how the plugin records notes, ideas, and architectural decisions to the vault on demand or in response to detected triggers, always tagged and timestamped.

---

## Segment Boundary

- **Prefix**: `CAPTURE-*`
- **EARS specs**: [docs/specs/capture-specs.md](../specs/capture-specs.md)
- **Arrow doc**: [docs/arrows/capture.md](../arrows/capture.md)
- **HLD parent section**: [docs/high-level-design.md#segments](../high-level-design.md#segments)

### What this segment owns

- Quick capture of free-form notes (`/sq-capture`, `capture` skill)
- ADR-style decision capture (`/sq-decision`, `decision` skill)
- Detection of decision-language in user prompts ("voy a usar X", "decidí Y")
- Suggesting and applying a semantic tag at capture time
- Writing the resulting note into the correct vault location

### What this segment does NOT own

- Vault layout, tag schema validation, or frontmatter format (owned by `vault`)
- Session-boundary captures (loading note, shutdown note — owned by `session`)
- Producing summaries or briefs from captured notes (owned by `brief`)
- Cross-environment transfer of captured notes (owned by `sync`)
- Hook wiring that fires capture on `UserPromptSubmit` (owned by `integrations`; capture only exposes the skill entrypoint)

## Responsibilities

- **One capture, one note, one tag**: every capture produces exactly one Markdown file with a single canonical tag. No multi-tag composites at capture time.
- **Tag-or-ask**: if the segment cannot infer a tag with high confidence, it asks the user before writing. It never writes untagged.
- **Decision capture is structured**: when a decision is detected, the note follows the ADR-ligero template (`templates/decision-adr.md`) — context, alternatives, decision, consequences.
- **Idempotent on identical content**: capturing the same content twice within a small time window updates the existing note rather than creating a duplicate.
- **No interpretation**: capture preserves the user's words verbatim. Summarization or rewording happens in `brief`, not here.

## Key Flows

### Flow: Quick capture on demand

```
1. User invokes /sq-capture (or says "anotá esto", "guarda esto")
2. Skill infers project context from active session
3. Skill proposes a tag (PROYECTO-SUBÁREA-COMPONENTE-NNN); asks if unsure
4. Skill writes note to vault with frontmatter (id, proyecto, tags, creado, tipo)
5. Skill confirms with tag + path
```

→ EARS specs: `CAPTURE-001`, `CAPTURE-003`

### Flow: Decision detected mid-conversation

```
1. UserPromptSubmit hook detects decisional language
2. decision skill activates, parses context/decision/justification/consequences
3. Skill presents draft ADR for confirmation
4. On confirm, writes decision note linked from project page
```

→ EARS specs: `CAPTURE-002`, `CAPTURE-004`

## Constraints

- Must work offline; capture cannot depend on remote services.
- Must complete within the per-operation token budget for capture (see README table).
- Must not block the user's turn on long inference — if tagging is uncertain, ask once and proceed.

## Open Questions

- [x] How should capture handle multi-project ambiguity when the user is between sessions? **Decision: ask with a short numbered list** of the last 2–3 active projects; require a single selection. If no response fits the token budget, capture to `02-Areas/inbox/` with an `INBOX-GENERAL-CAPTURE-NNN` tag and flag it for later classification. Never silently pick a project.
- [x] Should decision-capture support retroactive linking to a prior intent? **Decision: yes, opt-in and explicit.** After drafting the ADR, capture prompts "Link to a prior intent? (enter ID or skip)". If provided, the decision note gets `linked_intent:` in its frontmatter. No auto-search; manual entry only to avoid false positives.
