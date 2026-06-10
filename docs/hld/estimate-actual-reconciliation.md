# Estimate↔Actual Reconciliation — High-Level Design

## Overview

Squirrel already computes an ADHD-padded time estimate (`estimate_buffer.adjust_estimate`,
`apps/cli/lib/estimate_buffer.py:69`) and already tracks real time spent per intent
(`time_invested_minutes`, written on checkout — `apps/backend/server.py:1022,1031`). The two
halves never meet: the estimate is printed and discarded, the actual is shown alone. This change
**closes the loop** — it persists the estimate onto the intent and surfaces the
estimate-vs-actual variance once work has been tracked. Over time the user sees whether their
padded estimate matched reality, turning time-blindness from a static assumption into a measured,
self-correcting signal.

## Stakeholders & Impact

- **Primary — the engineer with ADHD (the user).** Today they get a padded estimate with no
  feedback; chronic underestimation keeps wrecking planning. After this ships they can compare
  what they estimated time, what Squirrel planned, and what it actually took — on the same surface.
- **Secondary — AI agents** (`/sq-estimate`, `/sq-where-am-i`). The CLI gains the ability to
  persist an estimate to an intent, so agents can set estimates during a session and reference
  variance in their summaries.
- **Secondary — the focus/checkout flow.** Checkout already recomputes `time_invested_minutes`;
  it becomes the natural moment variance becomes meaningful, with no new daemon.

## Goals

- An intent can carry a persisted estimate (raw guess, multiplier, adjusted value) in its
  Markdown frontmatter.
- An estimate can be set from every surface the user already touches: CLI/agent, the desktop
  popup, the focus-pick flow, and the web SPA.
- When an intent has both an estimate and tracked actual time, the system shows them together
  with a variance (delta + ratio), on the desktop popup and the web HomePage.
- All math is local, deterministic, scripts-only — no LLM, no network.
- Variance copy is neutral/calibrating, never shaming.
- Intents without an estimate (including all pre-existing/legacy intents) keep working exactly as
  before — actual shown alone, no variance, no errors.
- An estimate set by mistake can be cleared.
- Estimates apply only to active-project intents (`01-Active-Projects`) — the same scope where
  actuals are tracked and variance is shown — so an estimate is never set where it can't pay off.

## Non-Goals

- No change to the existing multiplier rules or to how `time_invested_minutes` is computed.
- No aggregate calibration across tasks and no auto-tuning of the multiplier from history.
- No charts, timeline, or visual time representation — text numbers only.
- No per-chunk estimates (`chunk_helper.py` phases are untouched); estimates are per-intent.
- No notifications/nudges about variance and no new background behavior.
- No gamification (streaks/confetti for accurate estimates).
- No cloud, no auth, no external time-tracker integration.

## Success Criteria

- Setting an estimate on an intent (any surface) writes durable frontmatter that survives a vault
  re-scan.
- After at least one checkout on an estimated intent, the desktop popup and web HomePage display
  estimate, actual, and the variance ratio together.
- An estimated-but-never-started intent shows the estimate alone; a tracked-but-never-estimated
  (legacy) intent shows the actual alone — neither errors.
- Variance is computed with no LLM import and no outbound request (verified by test).
- All displayed variance copy comes from the approved neutral-framing copy set.
