# Example: Complete personal → work package

## Example context
- On your personal PC you researched 3 auth libraries for `TRABAJO-PROYECTO-A`
- You generated a comparison table and made a preliminary decision
- Now you want to take the research + decision to work

## Command executed on personal machine
```
/cb-sync-out --scope=TRABAJO-PROYECTO-A:research --scope=TRABAJO-PROYECTO-A:decisions
```

## Result (this is the block you copy to email/clipboard)

```
<!-- CONTEXT-BRIDGE-PACKAGE v1 -->
<!--
  from: personal
  to: work
  generated_at: 2026-05-23T19:30:00Z
  generated_by: claude-code@home-mbp
  scope: TRABAJO-PROYECTO-A:research,TRABAJO-PROYECTO-A:decisions
  files_count: 2
  hash_sha256: a3f5b8c9d1e2f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9
  intent: research-results-for-work-auth-decision
  receiver_instructions: apply-with-sync-in
-->

# 📦 Context Bridge Package

**From**: personal  →  **To**: work
**Generated**: May 23 2026, 19:30 (local)
**Scope**: TRABAJO-PROYECTO-A:research, TRABAJO-PROYECTO-A:decisions
**Files**: 2

> 📋 To apply: in the other environment, open Claude Code / Codex and paste THIS entire block
> into the chat. The `context-bridge:sync-in` skill will process it automatically.

---

## 📑 Package summary

- `01-Proyectos-Activos/TRABAJO-PROYECTO-A/TRABAJO-PROYECTO-A-RESEARCH-001.md` — create — Auth.js vs Clerk vs Lucia comparison
- `01-Proyectos-Activos/TRABAJO-PROYECTO-A/TRABAJO-PROYECTO-A-DECISION-001.md` — create — Preliminary decision: Auth.js v5

---

## 📂 Files to apply

### File 1: 01-Proyectos-Activos/TRABAJO-PROYECTO-A/TRABAJO-PROYECTO-A-RESEARCH-001.md

**Operation**: create
**Tag**: `TRABAJO-PROYECTO-A-RESEARCH-001`
**Conflict if exists**: ask

` ` `markdown
---
id: TRABAJO-PROYECTO-A-RESEARCH-001
proyecto: TRABAJO-PROYECTO-A
tipo: research
estado: done
creado: 2026-05-23
imported_from: personal
tags: [research, proyecto/TRABAJO-PROYECTO-A]
---

# TRABAJO-PROYECTO-A-RESEARCH-001 — Auth library comparison

## Context
We need to choose an auth library for the OAuth+JWT feature of the project.
Candidates: Auth.js (NextAuth), Clerk, Lucia.

## Findings

| Criteria | Auth.js v5 | Clerk | Lucia |
|---|---|---|---|
| Cost | Free (self-hosted) | Free tier limited, $25/mo | Free (self-hosted) |
| Maturity | High | Very high | Medium |
| Customization | High | Medium | Very high |
| OAuth providers | 80+ built-in | 30+ built-in | DIY |
| Mobile SDK | Not native | Yes, official | DIY |
| Vendor lock-in | Low | High | None |
| Setup time | 1-2 days | <1 day | 3-5 days |
| Bundle size | Medium | Large | Small |

## Recommendation
**Auth.js v5** is the optimal balance for our use case:
- Free, self-hosted, no vendor lock-in
- Sufficient maturity (v5 stable since 2024)
- 80+ providers (Google already implemented built-in)
- Active community
- Applicable to our Next.js 14 stack

Clerk is attractive for its DX but the lock-in and cost at scale rule it out.
Lucia is more flexible but requires too much boilerplate code for our timeline.

## References
- https://authjs.dev/getting-started/installation
- https://clerk.com/pricing
- https://lucia-auth.com/
- Discussion: https://github.com/nextauthjs/next-auth/discussions/...

## Source
- Session: 2026-05-23 19:00-19:30 (personal)
- Agent: claude-code
- Triggered by: research request before work decision
` ` `

---

### File 2: 01-Proyectos-Activos/TRABAJO-PROYECTO-A/TRABAJO-PROYECTO-A-DECISION-001.md

**Operation**: create
**Tag**: `TRABAJO-PROYECTO-A-DECISION-001`
**Conflict if exists**: ask

` ` `markdown
---
id: TRABAJO-PROYECTO-A-DECISION-001
proyecto: TRABAJO-PROYECTO-A
tipo: decision
estado: proposed
creado: 2026-05-23
revisado: 2026-05-23
imported_from: personal
tags: [decision, proyecto/TRABAJO-PROYECTO-A]
stakeholders: [arquitecto, lead, PM-Sarah]
---

# TRABAJO-PROYECTO-A-DECISION-001 — Use Auth.js v5 for auth

## 📌 Status
proposed (review with @arquitecto at work before accepting)

## 🎯 Decision
Use **Auth.js v5** (formerly NextAuth) as the authentication library
for the project, with Google OAuth as the primary provider.

## 🌐 Context
See [[TRABAJO-PROYECTO-A-RESEARCH-001]] for the full comparative analysis.

Project constraints:
- Stack: Next.js 14, Node 20, Postgres
- Deadline: 15-Jun-2026
- Team: 3 people, no deep auth experience
- Mobile: we need mobile app support (future)

## 🤔 Alternatives considered

### Option A: Clerk ← rejected
- ✅ Pros: excellent DX, official mobile SDK, setup in <1 day
- ❌ Cons: high vendor lock-in, $25/mo at scale, external dependency for auth
- ⚖️ Verdict: rejected due to lock-in and future cost

### Option B: Lucia ← rejected
- ✅ Pros: maximum flexibility, small bundle, no lock-in
- ❌ Cons: requires a lot of boilerplate, DIY mobile, tight timeline
- ⚖️ Verdict: rejected due to implementation cost vs deadline

### Option C: Auth.js v5 ← CHOSEN
- ✅ Pros: free, self-hosted, 80+ providers, proven maturity, active community
- ❌ Cons: no native mobile (workaround with REST tokens), medium bundle
- ⚖️ Verdict: best cost/benefit balance for our use case

## 📊 Consequences

### Positive
- No licensing costs
- No vendor lock-in
- Google OAuth built-in (one import)
- Manageable team learning curve

### Negative / costs
- Self-hosting auth implies security responsibility
- For mobile we will need to implement custom REST endpoints
- Requires non-trivial NextAuth.config.ts configuration

### Future commitments
- We are tied to the NextAuth architecture (changing would be costly)
- Future migration to Clerk/Auth0 would be expensive (re-implement flow)

## 🔗 Related
- Parent project: [[TRABAJO-PROYECTO-A]]
- Affected intents: [[TRABAJO-PROYECTO-A-AUTH-001]], [[TRABAJO-PROYECTO-A-AUTH-002]]
- Research: [[TRABAJO-PROYECTO-A-RESEARCH-001]]

## 📚 References
- https://authjs.dev/
- Internal discussion (to confirm with @arquitecto)

## 🗒️ Discussion notes
Research done from home because at work I cannot install all 3
libraries to evaluate them. Preliminary decision — needs validation with
@arquitecto before marking as `accepted`.

Action upon returning to work:
1. Apply this package with `/cb-sync-in`
2. Brief with `/cb-brief TRABAJO-PROYECTO-A`
3. Send @arquitecto the research + proposal
4. If approved: change status to `accepted` and start implementation
` ` `

---

<!-- END-CONTEXT-BRIDGE-PACKAGE -->
```

## At work (the next day)

1. Open email
2. Copy the entire block (from `<!-- CONTEXT-BRIDGE-PACKAGE` to `END-CONTEXT-BRIDGE-PACKAGE -->`)
3. Paste into the Claude Code / Codex chat

## What happens automatically

The `UserPromptSubmit` hook detects the marker and triggers the `sync-in` skill:

```
📦 Package detected.

From: personal  →  To: work
Generated: 2026-05-23 19:30
Hash: ✓ valid
Files: 2

📋 Application plan:

| # | Operation | File | Local status |
|---|-----------|------|--------------|
| 1 | CREATE    | TRABAJO-PROYECTO-A-RESEARCH-001.md | does not exist ✓ |
| 2 | CREATE    | TRABAJO-PROYECTO-A-DECISION-001.md  | does not exist ✓ |

Apply? (yes / selective / cancel)
```

You reply "yes", and:

```
✅ Applied:
  • Created: TRABAJO-PROYECTO-A-RESEARCH-001.md
  • Created: TRABAJO-PROYECTO-A-DECISION-001.md

🔗 Suggestion: link these files from TRABAJO-PROYECTO-A.md:
  - Add under "Components and Intents": [[TRABAJO-PROYECTO-A-RESEARCH-001]]
  - Add under "Decisions": [[TRABAJO-PROYECTO-A-DECISION-001]]

Apply the links?
```

"yes" → links are added.

```
Log: ~/work-vault/.context-bridge/applied/2026-05-24T08-15-00Z-a3f5b8c9.json

Suggestion: run /cb-brief TRABAJO-PROYECTO-A to see the updated status
with the new research and decision.
```

## Total time invested

- On personal machine: 30 min research + 1 min `/cb-sync-out` + 30 sec copy to email = ~32 min
- Transit (email): 0 seconds of your attention
- At work: 30 sec paste + 5 sec confirm = ~1 min

**Benefit**: complete, structured, traceable research, without sharing anything automatically, with an audit log of what entered the corporate environment.
