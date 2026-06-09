# Working Smarter (Intermediate) — 10 Commands for Complex Situations

> 🎯 _What you'll learn:_ The next level of Squirrel commands for stakeholder updates, deadlines, big tasks, decision logging, recovery, and status reporting. Use these once or twice a week.

**Version:** Squirrel v0.5.0  
**Last updated:** 2026-05-24  
**Reading time:** ~20 minutes

---

## Table of Contents

1. [`/sq-brief` — Status report in 6 sections](#sqbrief--status-report-in-6-sections)
2. [`/sq-decision` — Log an important choice](#sqdecision--log-an-important-choice)
3. [`/sq-deadlines` — What's burning?](#sqdeadlines--whats-burning)
4. [`/sq-estimate` — Add the ADHD buffer](#sqestimate--add-the-adhd-buffer)
5. [`/sq-chunk` — Break big tasks into small pieces](#sqchunk--break-big-tasks-into-small-pieces)
6. [`/sq-task-initiation` — When you can't start](#sqtask-initiation--when-you-cant-start)
7. [`/sq-parakeet` — Friendly deadline reminders](#sqparakeet--friendly-deadline-reminders)
8. [`/sq-recover` — Restore a forgotten session](#sqrecover--restore-a-forgotten-session)
9. [`/sq-dashboard` — Generate a pretty HTML page](#sqdashboard--generate-a-pretty-html-page)
10. [Weekly & biweekly rhythm](#weekly--biweekly-rhythm)

---

## `/sq-brief` — Status report in 6 sections

### What it does

Generates a structured 6-section project status (NOW, DONE, NEXT, DECISIONS, STEPS, CONTEXT) that you can send to a stakeholder, paste into Slack, or review yourself. Ready to send as-is.

### How it works

You run `/sq-brief [PROJECT]` → Squirrel reads the project folder → Squirrel aggregates intents, decisions, shutdown notes → Squirrel produces a structured brief (no longer than 400 words) → You can email it, copy to Slack, or use it as a sync-out package.

### Real-situation examples

**Situation 1: Stand-up update before a meeting**

You're Tomás. Your team lead asked for a status on `WORK-PROJECT-A`. You're in a meeting in 5 minutes:

```
/sq-brief WORK-PROJECT-A --slack
```

Squirrel produces:

```
**WORK-PROJECT-A** [2026-05-24]
- **Ayer**: Finished payment retry logic. 3/3 tests passing.
- **Hoy**: Writing unit tests for edge cases (network timeouts, invalid cards).
- **Bloqueos**: Ninguno.
- **ETA**: Ready for code review Friday.
```

You copy-paste this into Slack, and you're done. 30 seconds.

---

**Situation 2: Email to a freelance client**

You're Marcus. Your client wants a week update. You run:

```
/sq-brief FREELANCE-CLIENT-B --email boss@client.com
```

Squirrel opens a mailto draft:

```
To: boss@client.com
Subject: Context Bridge: FREELANCE-CLIENT-B Progress Update

## 📊 Brief: FREELANCE-CLIENT-B

**Tipo**: Redesign  •  **Deadline**: 2026-06-14  •  **Avance**: 60%

---

## 🎯 What I'm working on
CSS grid layout for the dashboard cards. Testing responsiveness across
three breakpoints (mobile, tablet, desktop).

## ✅ What I finished
- Dashboard mockups approved ✓
- Responsive CSS framework set up ✓
- Mobile cards tested (320px, 768px) ✓

## 🎬 What's next
- Desktop breakpoint testing (1200px)
- Performance optimization (CSS file size)
- Design review with you

## 🚦 Next steps
1. Complete desktop testing (1 day)
2. Performance review (1 day)
3. Schedule design review call

**ETA**: Rough estimates — design review by Friday.
```

Send as-is. Professional, clear, honest about progress.

---

**Situation 3: Self-review during weekly review**

You're Ana. Friday afternoon, you want to see what you got done this week:

```
/sq-brief SCHOOL-LAB-3
```

Squirrel shows:

```
## 📊 Brief: SCHOOL-LAB-3

**Tipo**: Assignment  •  **Deadline**: 2026-05-31  •  **Avance**: 75%

### 🎯 What I'm doing
Debugging the sorting algorithm. Two test cases still failing.

### ✅ What I finished
- Implemented bubble sort ✓
- Implemented merge sort ✓
- Wrote 10 unit tests ✓

### 🎬 What's next
- Fix the edge case in merge sort (when list length is odd)
- Write 3 more tests for edge cases
- Code review check

### 🚦 Next steps
1. Debug merge sort (1 hour)
2. Add edge-case tests (30 min)
3. Self-review

**ETA**: Realistic — should finish by Wednesday evening.
```

You read this and feel proud. Three intents done, three to go. You're on track.

---

### What you see

A 6-section brief:

1. **NOW** — current active intent + next action
2. **DONE** — completed intents (checkmarks)
3. **NEXT** — pending/in-progress intents
4. **DECISIONS** — architectural choices made
5. **STEPS** — 3–5 concrete next actions
6. **CONTEXT** — open questions, blockers, critical details

### Flags / variants

| Command                                       | Effect                                                    |
| --------------------------------------------- | --------------------------------------------------------- |
| `/sq-brief [PROJECT]`                         | Full 6-section brief                                      |
| `/sq-brief [PROJECT] --short`                 | 3 lines, perfect for Slack                                |
| `/sq-brief [PROJECT] --email you@example.com` | Open mailto draft                                         |
| `/sq-brief --all`                             | Brief for every active project (useful for Friday review) |

### Anti-pattern to avoid

❌ **Don't invent decisions or steps you didn't actually make.** The brief is a read-only aggregation. If you didn't decide something or write a shutdown note about it, it doesn't go in the brief.

---

## `/sq-decision` — Log an important choice

### What it does

Creates a structured decision record that captures _why_ you chose Option A over Option B. Future-you will forget the reasoning; this note preserves it.

### How it works

You run `/sq-decision "Your decision topic"` → Squirrel asks you: context, alternatives considered, consequences, and rationale → Squirrel writes a one-page memo to your project folder → Done.

### Real-situation examples

**Situation 1: Architecture decision**

You're Tomás. Your team decided to use SQLite instead of PostgreSQL for the MVP. This is important—write it down:

```
/sq-decision Use SQLite instead of PostgreSQL for the MVP
```

Squirrel asks you to fill in:

```
**Context**:
We're building a payment processing service. Need a database NOW,
not in 2 weeks.

**Alternatives considered**:
1. PostgreSQL (robust, complex, slow setup)
2. SQLite (simple, single-machine, good enough for MVP)
3. MongoDB (schema-less, but we like schemas)

**Consequences**:
- Pro: ship in 1 week instead of 3
- Pro: dev environment doesn't need Docker
- Con: eventual migration to PostgreSQL (not trivial)
- Con: max ~100K records before perf degrades

**Rationale**:
MVP validation > perfect architecture. If the product sells,
we'll have budget for a real database engineer to migrate.
If it doesn't, we didn't waste 3 weeks on setup.
```

Squirrel saves this to a decision note in your project. **Six months later, someone asks "Why SQLite?", and you point them to this note.**

---

**Situation 2: Scope decision**

You're Marcus, a designer. You decided NOT to add animations to the dashboard redesign. Write it:

```
/sq-decision Skip animations in dashboard redesign v1
```

You explain: "Client said 'functionality first, polish later'. Animations are 20% of the work for 5% of the value right now. We'll add them in v2 if the client asks."

**Later, if the client asks "Why no transitions?", you have a paper trail showing it was deliberate, not forgotten.**

---

### What you see

Squirrel walks you through a structured form, then saves a decision memo. Format: ~200 words, clean layout, tagged with the decision date.

### Flags / variants

| Command                             | Effect                                         |
| ----------------------------------- | ---------------------------------------------- |
| `/sq-decision "Topic"`              | Standard decision log                          |
| `/sq-decision "Topic" --quick`      | Skip some fields, just record the decision     |
| `/sq-decision "Topic" --reversible` | Flag this as "can be reversed" vs. "permanent" |

### Anti-pattern to avoid

❌ **Don't skip decisions.** Logging feels like friction now, but it's your paper trail later. "We decided to use SQLite" with zero record is useless in 6 months when someone asks.

---

## `/sq-deadlines` — What's burning?

### What it does

Shows every project deadline grouped by urgency (critical, urgent, soon, upcoming, eventual, distant). One command answers "What do I owe, and when?"

### How it works

You run `/sq-deadlines` → Squirrel reads all project deadlines → Squirrel groups them by urgency → You see at a glance what's on fire.

### Real-situation examples

**Situation 1: Monday morning panic check**

You're Ana. You have 5 classes and 3 side projects. Monday morning, you ask:

```
/sq-deadlines
```

Squirrel shows:

```
🔴 CRITICAL (overdue or due in <4 hours)
   None — you're safe!

🟠 URGENT (today or tomorrow)
   • SCHOOL-MIDTERM-STUDY — Due Thursday (2 days)
   • WORK-PROJECT-A — Code review due Friday (3 days)

🟡 SOON (2–3 days)
   • SCHOOL-LAB-3 — Due Friday (3 days)
   • SIDE-BLOG — Publish by Sunday (5 days)

🔵 UPCOMING (4–7 days)
   • FREELANCE-CLIENT-A — Feedback due next Monday (7 days)

🟢 EVENTUAL (8–30 days)
   • TRIP-PLANNING — Trip June 14 (20 days, prep optional)

⚪ DISTANT (>30 days)
   • TAXES-2026 — April 2027 (12 months away, no urgency)
```

You read this and plan your week: focus on MIDTERM and PROJECT-A this week, LAB-3 is also due Friday (double crunch). This clarity is worth it.

---

**Situation 2: Filter to just the urgent ones**

You're Tomás. You want to ignore "eventual" and see only what's actually burning:

```
/sq-deadlines --level critical,urgent
```

Squirrel shows:

```
🔴 CRITICAL
   None.

🟠 URGENT
   • WORK-PROJECT-A code review — Friday (3 days)
   • WORK-PROJECT-B review blocker — resolve with design by Thursday (2 days)
```

Now you focus only on the things that matter this week.

---

### What you see

A prioritized list of all deadlines, grouped by 6 urgency levels. Each deadline shows: project name, due date, days remaining.

### Flags / variants

| Command                                      | Effect                    |
| -------------------------------------------- | ------------------------- |
| `/sq-deadlines`                              | All deadlines, all levels |
| `/sq-deadlines --level critical,urgent`      | Only red and orange       |
| `/sq-deadlines --level critical,urgent,soon` | Red, orange, yellow       |
| `/sq-deadlines --this-week`                  | Only deadlines < 7 days   |

### Anti-pattern to avoid

❌ **Don't ignore "eventual" and miss something due in 2 months.** Check all deadlines at least weekly (Monday morning is perfect).

---

## `/sq-estimate` — Add the ADHD buffer

### What it does

When you (or your boss) estimate a task will take 2 hours, this command tells you the realistic number **with the ADHD context-switching tax built in**.

### How it works

You run `/sq-estimate "2 hours"` → Squirrel applies research-backed multipliers → You get a realistic estimate.

### Real-situation examples

**Situation 1: Boss asks for an estimate**

Your lead asks: "How long will the refactor take?" You think it's a 2-hour job:

```
/sq-estimate 2 hours
```

Squirrel shows:

```
⏱️ Estimación ADHD-buffered

  Your estimate:    2h
  Multiplier:       ×2.5
  Realistic:        5h

  Why: ADHD context-switching tax.
  Tasks routinely take 2–3× the original guess due to:
  - Distractions (emails, Slack, noise)
  - Hyperfocus recovery (spiking then crashing)
  - Task initiation friction (10–20 min to "boot up" on something new)
```

Now you tell your lead: "5 hours, not 2." Your estimate is honest. **This one number prevents half-finished work and late deliverables.**

---

**Situation 2: Long project estimation**

You're Marcus. You think the dashboard redesign is a "30-hour job". You want realistic:

```
/sq-estimate 30 hours
```

Squirrel shows:

```
⏱️ Estimación ADHD-buffered

  Your estimate:    30h
  Multiplier:       ×2–3 (depends on complexity)
  Realistic:        60–90h (1–2 weeks at 40h/week)
```

You just told your client: "2 weeks", not "1 week". Now you deliver on time, not in crisis.

---

### What you see

Your estimate + the multiplier + the realistic total. Includes a note on why the multiplier exists.

### Flags / variants

| Command                              | Effect                                  |
| ------------------------------------ | --------------------------------------- |
| `/sq-estimate "2 hours"`             | Apply standard ADHD multiplier          |
| `/sq-estimate "2 hours" --low`       | Conservative multiplier (×1.5)          |
| `/sq-estimate "2 hours" --high`      | Pessimistic multiplier (×3.5)           |
| `/sq-estimate "2 hours" --no-buffer` | Just the raw estimate (not recommended) |

### Anti-pattern to avoid

❌ **Don't estimate for your boss without the buffer.** If you say "2 hours" and it takes 5, they lose trust. Say "5 hours" and finish in 4? Hero.

---

## `/sq-chunk` — Break big tasks into small pieces

### What it does

A task that feels impossible ("build the entire checkout flow") becomes a sequence of small, doable chunks ("write validation → test validation → wire to UI → test flow → deploy").

### How it works

You run `/sq-chunk 8 hours` → Squirrel breaks it into phases (research, setup, implementation, testing) → Squirrel suggests a 2–3 session plan → You work through the chunks.

### Real-situation examples

**Situation 1: Big refactor**

You're Tomás. You need to refactor the authentication system. It feels like 2 weeks of chaos:

```
/sq-chunk 40 hours
```

Squirrel breaks it down:

```
🧩 Chunk Plan — 40 hours

Phases:
  🔬 Research & Planning     (120min) → 1 chunk
    (Read current auth code, document flow, plan new flow)

  🛠  Setup & Scaffolding     (120min) → 1 chunk
    (Create new auth module structure, imports, stubs)

  ⚙️  Core Implementation    (1800min) → 6 chunks
    (Token generation, validation, refresh logic, etc.)

  ✨ Polish & Edge Cases      (180min) → 2 chunks
    (Error handling, logging, security checks)

  🧪 Testing & Docs          (180min) → 2 chunks
    (Unit tests, integration tests, API docs)

Sessions (12 chunks, 3 sessions of ~4h each):
  📅 Session 1 (4h): research, setup, implementation 1–2
  📅 Session 2 (4h): implementation 3–4, polish 1
  📅 Session 3 (4h): implementation 5–6, polish 2, testing & docs
```

Now it's not "refactor auth system" (scary). It's "Session 1: research & setup" (doable). Much easier to start.

---

**Situation 2: New feature**

You're Ana. The lab assignment is 10 hours of work. It feels overwhelming:

```
/sq-chunk 10 hours
```

Squirrel shows:

```
🧩 Chunk Plan — 10 hours

Sessions (6 chunks, 2 sessions):
  📅 Session 1 (5h): understand problem, write pseudocode, implement core algorithm
  📅 Session 2 (5h): fix bugs, write tests, clean code, submit
```

Instead of "spend all day Saturday on the lab", it's "Saturday morning: understand + code" and "Saturday afternoon: test + submit". Two chunks, you're done.

---

### What you see

A breakdown of the big task into phases, with time estimates for each, plus a recommended session plan (usually 2–3 sessions, each 4–5 hours).

### Flags / variants

| Command                                 | Effect                          |
| --------------------------------------- | ------------------------------- |
| `/sq-chunk 8 hours`                     | Break into optimal chunk sizes  |
| `/sq-chunk 8 hours --session-length 2h` | Make sessions shorter (2h each) |
| `/sq-chunk 8 hours --sessions 3`        | Force exactly 3 sessions        |

### Anti-pattern to avoid

❌ **Don't create chunks that are >2.5 hours each.** Anything longer than that, people get fatigued and lose focus. Stick to 60–90 min per chunk.

---

## `/sq-task-initiation` — When you can't start

### What it does

You're staring at something and your brain won't let you begin. This command figures out _why_ you're stuck and applies the matching anti-paralysis trick.

### How it works

You run `/sq-task-initiation` → Squirrel asks "what kind of stuck?" (don't know what to do / can't click go / overwhelmed / scared) → Squirrel suggests the matching trick → You start immediately.

### Real-situation examples

**Situation 1: "I don't know what to do first"**

You're Tomás. The refactor seems complex. You don't know where to start. You run:

```
/sq-task-initiation
```

Squirrel asks: "What kind of stuck?" You say: "don't know what to do"

Squirrel replies:

```
🎯 Trick: Smallest Action

Just open the auth.ts file. That's it. Nothing else.
You don't need to refactor it, understand it all, or plan anything.
Just open it. 2 seconds.

Once it's open, I bet you'll see something obvious to start with.
This is the "smallest possible action" trick.
```

You open the file. You see the login function. You realize: "I'll start here." You're off.

---

**Situation 2: "I know what to do but I can't make myself start"**

You're Ana. You know you need to write the lab code, but you're procrastinating. You run:

```
/sq-task-initiation
```

You say: "can't click go"

Squirrel suggests:

```
💡 Trick: 2-Minute Start

Set a timer for exactly 2 minutes. Work on the lab for just 2 minutes.
After 2 minutes, you can stop if you want. You promised yourself nothing more.

Most of the time, once you start, you'll keep going. But if you don't,
that's okay—you worked for 2 minutes. You're not "procrastinating", you're
"working (briefly)".

The trick: remove the pressure to do the WHOLE thing. Just do 2 minutes.
```

You set a timer. You start. After 2 minutes, you're in flow. You keep going.

---

**Situation 3: "It's too big, I'm overwhelmed"**

You're Marcus. The redesign feels enormous. You run:

```
/sq-task-initiation
```

You say: "overwhelmed"

Squirrel suggests:

```
🧩 Trick: Decompose

Let's break this down. What are the 3 biggest sub-tasks?
1. Wireframes
2. CSS grid layout
3. Responsive testing

Pick ONE. Just one. Ignore the other two for now.
Which one do you want to work on first?
```

You focus on just wireframes. Suddenly it's doable.

---

### What you see

Squirrel asks "what kind of stuck?", you answer, and Squirrel suggests the matching trick: Smallest Action, 2-Minute Start, Decompose, or Emotional Defusion.

### Flags / variants

| Command                                 | Effect                        |
| --------------------------------------- | ----------------------------- |
| `/sq-task-initiation`                   | Ask what kind of stuck        |
| `/sq-task-initiation --smallest-action` | Jump to smallest action trick |
| `/sq-task-initiation --two-minute`      | Jump to 2-minute timer trick  |
| `/sq-task-initiation --decompose`       | Jump to decompose trick       |

### Anti-pattern to avoid

❌ **Don't force yourself to "feel motivated" before starting.** You don't need motivation; you need momentum. Use these tricks to start; motivation follows.

---

## `/sq-parakeet` — Friendly deadline reminders

### What it does

Shows your deadlines like `/sq-deadlines`, but with kinder wording. The "parakeet" tunes its tone to urgency: far-off deadlines get a casual mention, critical ones are calm and supportive (not scary).

### How it works

You run `/sq-parakeet` → Squirrel reads deadlines → Squirrel generates a friendlier version → You see what's due without stress.

### Real-situation examples

**Situation 1: Routine friendly reminder**

You're Ana. You want a deadline check, but in a kind way:

```
/sq-parakeet
```

Squirrel shows:

```
🐦 Parakeet Deadline Reminder

Hey, a few things on the horizon:

📌 This week
- SCHOOL-MIDTERM-STUDY: exam Thursday. You have 4 study sessions planned?
  Maybe spend 30 min each evening this week. Totally doable.

📌 Next week
- WORK-PROJECT-A: code review due Friday.
  You're on track. Keep the pace and you'll finish Wed.

📌 Later (not urgent)
- FREELANCE-CLIENT-A: client feedback due June 2.
  Far enough away. You've got time.

---
You're doing great. Pick one thing to focus on today. That's all.
```

The tone is supportive, not scary. It helps you prioritize without stressing.

---

**Situation 2: When something is actually critical**

The parakeet still nudges, but calmly:

```
🐦 Parakeet — Critical Alert

SCHOOL-LAB-3 is due Friday 11:59 PM. That's 2 days.
You haven't started yet.

Here's one step that helps:
1. Open the lab brief right now (60 seconds)
2. Capture one thing you understand (2 minutes)
3. Make a plan for Wednesday (20 minutes)

That's it. By Wednesday night, you'll have momentum.

You've handled tight deadlines before. This is one of those times.
You've got this.
```

It's honest but supportive, not guilt-tripping.

---

### What you see

A deadline list with tone-adjusted messaging. Critical deadlines are calm, gentle nudges. Far-away deadlines are casual.

### Flags / variants

| Command                       | Effect                                  |
| ----------------------------- | --------------------------------------- |
| `/sq-parakeet`                | Full reminder, kind tone                |
| `/sq-parakeet --critical`     | Show only the red ones (but still kind) |
| `/sq-parakeet --motivational` | More encouraging tone                   |

### Anti-pattern to avoid

❌ **Don't use this as your only deadline reminder.** It's kind, but `/sq-status` gives clearer data. Use both.

---

## `/sq-recover` — Restore a forgotten session

### What it does

If you forgot to `/sq-end` last time, this command reads your chat history and reconstructs the shutdown note. Not perfect, but usually 80% there.

### How it works

You run `/sq-recover` → Squirrel reads the AI session history → Squirrel reconstructs what you were doing → Squirrel shows you a draft shutdown note → You can save it or edit it.

### Real-situation examples

**Situation 1: Forgot shutdown, next day**

You're Tomás. Yesterday you worked for 3 hours, then closed Claude Code without `/sq-end`. Today you realize: "Oh no, I lost the thread."

You run:

```
/sq-recover
```

Squirrel reads yesterday's chat and reconstructs:

```
### 2026-05-23 16:30 [reconstructed from chat history]
- **Estado**: Finished implementing password reset flow. Tests pending.

- **Next physical action**: Run test_auth_password_reset.py with -vv flag
                            to see detailed output. Likely quick fix.

- **Hipótesis activa**: The email mock isn't being called correctly in the test.

- **Open loops**: Need to verify email sending actually works (not just mocked).
```

It's not perfect (Squirrel estimated time the timestamp), but it's 80% there. You can confirm or edit, then save.

---

**Situation 2: Recover when you're really lost**

You're Ana. You didn't use Squirrel for a week. You're back:

```
/sq-recover
```

Squirrel reads the last week of chat and shows you a reconstructed note. It might be fuzzy (Squirrel isn't sure if you finished or just paused), but it gives you enough to ask Claude Code: "Wait, where did I leave off?"

---

### What you see

A draft shutdown note reconstructed from your chat history. Marked `[reconstructed]` so you know it's an educated guess, not a saved record.

### Flags / variants

| Command                           | Effect                             |
| --------------------------------- | ---------------------------------- |
| `/sq-recover`                     | Reconstruct most recent session    |
| `/sq-recover --project [PROJECT]` | Reconstruct for a specific project |
| `/sq-recover --hours 24`          | Look back 24 hours (default is 12) |

### Anti-pattern to avoid

❌ **Don't rely on recover.** It's a safety net, not a feature. Get in the habit of `/sq-end` daily.

---

## `/sq-dashboard` — Generate a pretty HTML page

### What it does

Creates a self-contained HTML file with your full status. Open it in any browser; it refreshes every 5 minutes. Great for displaying on a second monitor or sharing with a teammate.

### How it works

You run `/sq-dashboard` → Squirrel generates `~/.squirrel/dashboard.html` → You open it in your browser → It shows a clean view of all projects, deadlines, progress, alerts.

### Real-situation examples

**Situation 1: Display on a second monitor**

You're Tomás. You have two monitors. You want a live view of your projects on the second screen:

```
/sq-dashboard
```

Squirrel generates the HTML. You open it in a browser tab on Monitor 2. It shows:

```
📊 Squirrel Dashboard

PROJECTS (3 active)
├─ WORK-PROJECT-A — 60% done — No blockers
├─ WORK-PROJECT-B — 20% done — Waiting on design
└─ SIDE-BLOG — 10% done — Ready to work

DEADLINES (next 7 days)
├─ 🟠 WORK-PROJECT-A code review — Friday (3 days)
└─ 🟡 SIDE-BLOG publish — Sunday (5 days)

FOCUS TODAY
1. WORK-PROJECT-A (closest deadline)
2. SIDE-BLOG (if time)
```

Every 5 minutes it refreshes. You glance at Monitor 2, see your status at a glance.

---

**Situation 2: Share with a teammate**

You're Ana. Your study partner wants to see your lab progress:

```
/sq-dashboard
```

You email them the HTML file. They open it and see your progress, next steps, and blockers. No need for a synchronous status meeting.

---

### What you see

A self-contained HTML file (no dependencies, no cloud calls). Shows projects, deadlines, progress, alerts, focus suggestions. Auto-refreshes every 5 minutes.

### Flags / variants

| Command                              | Effect                           |
| ------------------------------------ | -------------------------------- |
| `/sq-dashboard`                      | Generate and open in browser     |
| `/sq-dashboard --file /path/to/save` | Save to a custom path            |
| `/sq-dashboard --refresh 10`         | Refresh every 10 minutes (not 5) |

### Anti-pattern to avoid

❌ **Don't stare at the dashboard all day.** It's a _view_, not a replacement for `/sq-start` and `/sq-end`. Use it for glance-checks, not as your primary interface.

---

## Weekly & biweekly rhythm

Here's how to weave the intermediate commands into your week:

```
📅 Monday 9 AM
  ├─ /sq-status  (see the full landscape)
  └─ /sq-deadlines  (what's due this week?)

📅 During the week
  ├─ /sq-deadline  (if something feels urgent, check)
  ├─ /sq-decision  (whenever you make a real choice)
  └─ /sq-task-initiation  (if you get stuck)

📅 Wednesday or Thursday
  └─ /sq-estimate  (boss asks for eta? be realistic)

📅 Friday 5 PM
  ├─ /sq-status  (see what you finished, what's carrying over)
  ├─ /sq-brief --all  (brief on every project, for weekly review)
  └─ /sq-dashboard  (share status with team if applicable)

📅 Biweekly (first and third Monday)
  └─ /sq-parakeet  (kind reminder, tune your focus)
```

---

## Where to go next

- **Using intermediate commands?** → [Two Computers](./two-computers.md) to sync between home and work.
- **Want power features?** → [Power User](./power-user.md) covers encryption, CLI, and advanced setups.
- **Need a refresher on basics?** → [Everyday Use](./everyday-use.md).

These 10 commands solve 95% of real-world scenarios. 🐿️
