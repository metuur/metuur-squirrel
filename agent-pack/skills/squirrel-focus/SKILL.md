---
name: squirrel-focus
description: Show or change the user's manual focus pick for today or this week from the chat. Use when the user says "what's my focus", "set focus to X", "switch focus", "clear focus", "what's my focus for today", "change the focus", or invokes /sq-focus. All mutations flow through the backend's /api/focus/* endpoints — never touch vault files directly. Mirrors the heuristic FocusWidget but is user-driven.
---

# squirrel:focus

## Purpose

User-driven pin of a `(project + intent)` pair into the **today** or **this-week** manual-focus slot.

This is distinct from the heuristic focus shown by the `FocusWidget` / `/api/home.focus` — that one is computed by the 3-rule engine in `status_aggregator._recommend_focus()`. The manual focus pick is what the *user* says they want to work on, independent of what the heuristic recommends.

Read-time semantics (handled server-side):
- A `focus_today` value from yesterday is auto-treated as **unset** (returns `null`).
- A `focus_week` value from a previous ISO week is auto-treated as **unset**.
- No background job enforces expiry — it happens at API request time.

## When to invoke

**Explicit triggers:**
- `/sq-focus` slash command (any form)
- "what's my focus", "what's my focus for today", "what's today's focus"
- "set focus to X", "pin X as today's focus", "pin X as focus", "change the focus to X"
- "clear focus", "clear my focus", "I have no focus today"

**Implicit triggers (offer, don't auto-execute):**
- User says "today I'm focusing on X" / "today I'm working on X" — offer to pin via `/sq-focus today TAG/INTENT-SLUG`.
- User pivots mid-session and explicitly drops the current focus — offer `/sq-focus today --clear` or `today --clear` + set the new one.

Do **not** trigger:
- For pure status questions ("how's project X going") — that's `/sq-status` or `/sq-where-am-i`.
- For deadline reminders — that's `/sq-deadlines` / `/sq-parakeet`.

## Workflow

The actual execution lives in the slash command `/sq-focus` (see `agent-pack/commands/sq-focus.md`). This skill is the discoverability layer — it exists so Claude routes user intent to the right command.

When triggered:

1. **Identify the slot.** Did the user mean *today* or *this week*?
   - "today", "this afternoon", "right now" → `today`
   - "this week", "for the week" → `week`
   - Ambiguous → default to `today` and confirm.

2. **Identify the action.**
   - Read (no arguments) → `/sq-focus`
   - Set → `/sq-focus today TAG/INTENT-SLUG` or `/sq-focus week TAG/INTENT-SLUG`
   - Clear → `/sq-focus today --clear` or `/sq-focus week --clear`

3. **Resolve the TAG/INTENT-SLUG** if setting:
   - If the user gave both → use them verbatim.
   - If the user gave only a project (e.g. "set focus to VISA") → ask which intent, or look at `/api/home.projects[]` for the active intent of that project and propose it.
   - Never guess silently — confirm before issuing the PUT.

4. **Run the slash command.** Hand off to `/sq-focus` with the resolved arguments. The command handles backend-offline (R-7.6) and 404 intent_not_found (R-7.7) error messages.

## Output

After the command runs, surface the result verbatim. Don't paraphrase:
- `Today: VISA / RESEARCH-001`
- `Today's focus set: VISA/RESEARCH-001`
- `Today's focus cleared.`
- `Backend offline — run \`make backend-start\``
- `No such intent: VISA/RESEARCH-001`

## Anti-patterns

- Do NOT write `focus_today:` / `focus_week:` into intent files yourself. All mutations go through `/api/focus/*` (R-7.8).
- Do NOT touch `~/.squirrel/state.json` — the manual focus pick is vault state, not session state (R-10.4).
- Do NOT override the heuristic focus card — the manual pick lives next to it, not in place of it.
- Do NOT auto-set the focus without user confirmation when the trigger is implicit. Implicit triggers → offer; explicit triggers → execute.
- Do NOT call this skill for general "status" or "deadlines" questions. Route those to their dedicated commands.
