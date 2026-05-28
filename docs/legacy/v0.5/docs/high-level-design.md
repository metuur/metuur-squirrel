# squirrel — High-Level Design

`squirrel` is a Markdown-first, multi-agent context and task management plugin for software engineers with ADHD. It preserves working context across sessions, projects, and agents (Claude Code, Codex, Cursor), bridges personal and corporate environments via a manual air-gap, and offloads deterministic computation to local scripts so the LLM only handles judgment. Every LLD, EARS spec, and `@spec` annotation traces back here.

---

## Vision

Become the durable working memory and attention-support layer for an engineer with ADHD who juggles many projects across air-gapped environments — so that no context is lost between sessions, no decision is forgotten, no deadline silently slips, and no thought is trapped on the wrong machine. It explicitly does NOT become a project management SaaS, a cloud-synced notes app, or an automated cross-environment sync tool — the human is always the deliberate bridge.

## Principles

Durable architectural commitments. These should change rarely; when they change, every LLD downstream may need to change too.

- **Markdown-first, plain text everywhere**: State lives in `.md` files on disk — no databases, no cloud, no proprietary formats. Works offline, in any editor, on any OS.
- **Manual air-gap between environments**: No automatic sync between personal and corporate environments. The transfer mechanism is a self-contained, hash-verified Markdown package the human deliberately copies, pastes, or emails.
- **Agent-agnostic core**: The portable unit is the Markdown `SKILL.md`. One core of skills runs on any agent that loads skills; agent-specific glue (manifests, hooks, commands) lives only in the `integrations` segment.
- **Scripts-first computation**: Deterministic work (parsing, aggregation, classification, hashing, diffing) is done by local Python stdlib scripts that emit structured JSON. The LLM consumes JSON and exercises judgment — it never re-implements computation. This is the v0.2 token-budget contract.
- **Proactive, not passive**: Hooks and triggers invoke skills automatically on session boundaries, decision-language, and inactivity. The plugin asks questions; it does not wait to be asked.
- **Semantic tags as the universal join**: Every artifact (note, decision, session, package) carries a `PROYECTO-SUBÁREA-COMPONENTE-NNN` tag. Tags are the only cross-segment identifier the system relies on.
- **Idempotent, auditable side-effects**: Applying the same package twice produces the same vault state. Every cross-environment apply leaves an audit record.

## Segments

The product is partitioned into product-behavior segments. Each segment has its own LLD. The full segment registry is `docs/arrows/index.yaml`; this list mirrors it.

| Segment | Prefix | LLD | Owns |
|---|---|---|---|
| capture | `CAPTURE-*` | [docs/llds/capture.md](llds/capture.md) | Quick notes and ADR-style decisions written to vault with semantic tags |
| session | `SESSION-*` | [docs/llds/session.md](llds/session.md) | Session lifecycle: loading notes on start, shutdown notes on end, inactivity detection |
| brief | `BRIEF-*` | [docs/llds/brief.md](llds/brief.md) | Status briefs, "where-am-i" diagnostics, multi-project status summaries |
| sync | `SYNC-*` | [docs/llds/sync.md](llds/sync.md) | Air-gap package protocol: generation, hash verification, parsing, apply, audit log |
| attention | `ATTN-*` | [docs/llds/attention.md](llds/attention.md) | ADHD-specific aids: deadline classification (parakeet), focus scoring, context-switch tracking, task chunking, estimation buffer |
| vault | `VAULT-*` | [docs/llds/vault.md](llds/vault.md) | Vault layout, tag taxonomy, frontmatter schema, intent parser, status aggregator |
| integrations | `INT-*` | [docs/llds/integrations.md](llds/integrations.md) | Agent host adapters (Claude Code, Codex, Cursor), installation, configuration, slash commands, hooks wiring |

## Cross-Segment Invariants

Behaviors that MUST hold across all segments. These are stated once, here, not duplicated in each LLD.

- **Tag schema is canonical**: Every artifact created, updated, or transferred MUST carry a valid `PROYECTO-SUBÁREA-COMPONENTE-NNN` tag. Segments never invent ad-hoc identifiers.
- **No automatic network egress**: The plugin MUST NOT make network requests that cross the personal/corporate boundary. The only cross-environment data movement is human-initiated (copy/paste, email).
- **Scripts-first contract**: When deterministic computation is available (parsing, aggregation, hashing, diffing), the segment MUST call the script in `lib/` and consume its JSON output — not re-implement the logic in the skill prompt.
- **Idempotent writes**: Any operation that writes to the vault (capture, sync apply, session end) MUST produce the same end state when applied twice with the same input.
- **User-confirmed side effects across the air-gap**: `sync-in` MUST present a diff and require explicit confirmation before mutating the local vault.
- **Audit trail for cross-environment applies**: Every applied `sync-in` package MUST leave a record under `.squirrel/applied/` with the package hash, source, scope, and timestamp.
- **Token budget is observable**: Each LLM-facing operation has a declared token-budget target (see README "Token budget per operation" table). Regressions MUST be caught before release.

## Out of Scope

Behaviors this product explicitly does NOT own.

- **Cloud sync or automatic cross-environment transfer**: the air-gap is the feature, not the bug.
- **Vault rendering / WYSIWYG editing**: Obsidian, Logseq, VSCode, vim, and `cat` handle that.
- **Identity federation, SSO, or cloud authentication**: the plugin operates entirely on local files.
- **Long-term GPG key management**: encryption of packages is opt-in and delegated to the user's existing GPG setup.
- **Project management features beyond ADHD-personal scope**: no team boards, no assignees, no shared dashboards.
- **Reading credentials, SSH keys, or other system-sensitive files**: the plugin reads only vault directories the user has explicitly configured.
- **Replacing the agent's native tool surface**: skills compose with the agent's existing read/write/search tools; they do not reimplement them.
- **MCP server**: deliberately not provided. The supported surfaces are the `cb` CLI, the agent-loaded skills, and one-shot `claude -p` invocations. An MCP server would add a long-lived runtime, network surface, and dependency footprint inconsistent with the offline / scripts-first / no-daemon posture.

---

<!--
HLD authorship notes (delete when filling in):

- The HLD is short. If it's longer than ~2 pages, you're writing an LLD or PRD by mistake.
- Every segment listed here MUST have a corresponding entry in docs/arrows/index.yaml,
  a docs/llds/<segment>.md, and a docs/specs/<segment>-specs.md.
- Cross-segment invariants live ONLY here. If a "shared" rule appears in two LLDs, lift it up.
- This document is the cascade anchor: when intent changes, walk down from here.
-->
