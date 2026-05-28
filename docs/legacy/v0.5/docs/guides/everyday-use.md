# Everyday Use (Basic) — The Five Commands You'll Use Daily

> 🎯 *What you'll learn:* The five core Squirrel commands that cover 80% of daily use. You'll see how each one works, real situations where you'd use it, and expected output for each.

**Version:** Squirrel v0.5.0  
**Last updated:** 2026-05-24  
**Reading time:** ~18 minutes

---

## Table of Contents

1. [`/sq-capture` — Save an idea instantly](#sqcapture--save-an-idea-instantly)
2. [`/sq-start` — Load a project's context](#sqstart--load-a-projects-context)
3. [`/sq-end` — Save where you stopped](#sqend--save-where-you-stopped)
4. [`/sq-where-am-i` — "What was I doing?"](#sqwhere-am-i--what-was-i-doing)
5. [`/sq-status` — Big-picture overview](#sqstatus--big-picture-overview)
6. [Daily rhythm](#daily-rhythm)
7. [Habit card](#habit-card)

---

## `/sq-capture` — Save an idea instantly

### What it does

Captures a quick idea, task, or note and files it in the right project folder automatically. You never lose a thought again.

### How it works

You type an idea → Squirrel reads your text, figures out which project it belongs to → Squirrel creates a capture note in `03-Recursos/Captures/` → Done in 2 seconds.

### Real-situation examples

**Situation 1: Developer with a bug suspicion**

You're Tomás, a full-stack developer. While reading the auth code, you notice something: *"The refresh token might not clear on logout."*

```
/sq-capture The refresh token lingering after logout might cause security issues. 
            Check AuthController.logout() and ensure httpOnly cookie is cleared.
```

**Expected result:** A file appears at `~/vault/03-Recursos/Captures/WORK-PROJECT-A-NOTES-006.md` with your idea.

---

**Situation 2: Student juggling classes**

You're Ana, a computer science student. In the shower, you remember: *"Need to email Professor Kim about the lab extension."*

```
/sq-capture Email Professor Kim — ask about lab 3 extension for ADHD accommodations. 
            Due Friday, need 2 more days.
```

**Expected result:** Filed to your `SCHOOL-LAB-3` project automatically.

---

**Situation 3: Freelancer with a client idea**

You're Marcus, a designer. Your client texts you an idea for a new feature. You want to remember to discuss it next week.

```
/sq-capture Client suggestion: add "favorites" button to the dashboard. 
            Discuss scope + impact in next check-in.
```

**Expected result:** Captured to your `FREELANCE-CLIENT-A` project.

---

### What you see

```
✅ Capture guardada:
   WORK-PROJECT-A-NOTES-006
   proyecto: WORK-PROJECT-A
   tipo: capture
   creado: 2026-05-24

📁 Ubicación: ~/vault/03-Recursos/Captures/WORK-PROJECT-A-NOTES-006.md
```

### Flags / variants

| Command | Effect |
|---|---|
| `/sq-capture <text>` | Standard — Squirrel guesses the project |
| `/sq-capture <text> --project=SIDE-BLOG` | Explicit — force this project |
| `/sq-capture <text> --tag research` | Add a custom tag (beyond "capture") |
| `/sq-capture <text> --silent` | Don't show the file path, just confirm |

### Anti-pattern to avoid

❌ **Don't overthink the wording.** Captures are *rough ideas*, not polished notes. "Fix the bug" is fine. "Fix the potential race condition in the login state machine, need to review the Barkley paper on ADHD context switching" is overthinking. Capture rough, flesh out later.

---

## `/sq-start` — Load a project's context

### What it does

When you sit down to work on a project, this command reads everything Squirrel knows about that project (past shutdown notes, intents, decisions) and produces a brief that tells you exactly where to resume.

### How it works

You call `/sq-start [PROJECT]` → Squirrel reads your project folder in the vault → Squirrel finds your last shutdown note → Squirrel produces a "loading note" (200 words max) with the next physical action → You start immediately, no re-reading.

### Real-situation examples

**Situation 1: Developer resuming after the weekend**

You're Tomás. Monday morning, you open Claude Code:

```
/sq-start WORK-PROJECT-A
```

Squirrel reads your shutdown note from Friday and shows:

```
## 🔵 Sesión: WORK-PROJECT-A
Última actividad: 2026-05-21 (3 días atrás)

### 🎯 Estás haciendo
Implementing the checkout payment flow. You had just added error handling 
for failed card transactions.

### ✅ Lo último que hiciste
- Wrote the PaymentError exception handler
- Added retry logic for network timeouts
- Deployed a test to staging

### 🎬 Próximo paso físico
Open services/payment.py línea 142 and write unit tests for PaymentError.
Three tests minimum: timeout, invalid card, network error.

### 🎬 Próximo paso físico
Open services/payment.py línea 142 and write unit tests for PaymentError.
Three tests minimum: timeout, invalid card, network error.

### 💡 Decisiones clave
- Retry on timeout (not permanent fail) — client feedback: better UX

### 🚧 Bloqueos
None — ready to code.
```

**You now know exactly what to do.** No scrolling through Slack, no re-reading code. Just: open line 142, write three tests.

---

**Situation 2: Freelancer context-switching between projects**

You're Marcus. You have two active projects: `FREELANCE-CLIENT-A` and `FREELANCE-CLIENT-B`. You worked on A all week, but today you're scheduled to work on B.

```
/sq-start FREELANCE-CLIENT-B
```

Squirrel loads B's context and reminds you:

```
### 🎯 Estás haciendo
Dashboard redesign. You paused on the CSS grid layout for the card component.

### 🎬 Próximo paso físico
Open src/components/CardGrid.scss línea 23. Test three breakpoints: 
mobile (320px), tablet (768px), desktop (1200px).
```

**Context switch complete.** You're not carrying Client A's mental state into Client B.

---

### What you see

The loading note is always 150–200 words, structured, and action-oriented. 

### Flags / variants

| Command | Effect |
|---|---|
| `/sq-start [PROJECT]` | Load that project |
| `/sq-start` | (no arg) → Squirrel asks which WIP project |
| `/sq-start --last` | Resume the last project you were on |
| `/sq-start --list` | Show all WIP projects without loading any |

### Anti-pattern to avoid

❌ **Don't call `/sq-start` multiple times on the same day.** If you already ran it once this morning, calling it again just repeats the same loading note. You're already loaded.

---

## `/sq-end` — Save where you stopped

### What it does

This is the **most important command**. When you stop working (lunch, end of day, switching projects), this saves a structured "shutdown note" so tomorrow you remember everything.

### How it works

You type `/sq-end` → Squirrel reads the conversation history → Squirrel extracts what you did → Squirrel drafts a shutdown note with: current state, next action, decisions, open questions → You confirm → It's saved forever in your intent file.

### Real-situation examples

**Situation 1: Developer pausing at 5 PM**

You're Tomás. You've been working for 6 hours. It's 5 PM, time to close the laptop:

```
/sq-end
```

Squirrel reads your session (you implemented a test, ran it, it failed, you debugged for 30 min). Squirrel drafts:

```
### 2026-05-24 17:00
- **Estado**: One test still failing. Payment retry logic not triggering 
             on timeout. Everything else passing (2/3 tests OK).

- **Next physical action**: services/payment.py línea 167 — add 
                            exponential backoff for retries. Print debug logs 
                            to understand why the timeout handler isn't called.

- **Hipótesis activa**: The timeout exception is being caught somewhere else 
                        in the call stack (maybe in the HTTP client wrapper).

- **Bloqueado por**: None.

- **Decisiones tomadas hoy**: Use pytest fixtures for mocking network 
                              failures (not manual mocks).

- **Open loops**: Why is the timeout not bubbling up? Need to trace through 
                  the HTTP client code.

- **Hemingway**: Pausing with 2/3 tests passing. Good momentum for tomorrow.
```

You read it and say "sí". Now tomorrow morning, you run `/sq-start WORK-PROJECT-A` and that exact note is the first thing you read. No confusion.

---

**Situation 2: Student ending a homework session**

You're Ana. You've been working on your lab for 2 hours. Your brain is fried:

```
/sq-end
```

Squirrel reminds you what you did (wrote the main algorithm, started debugging) and suggests:

```
### Next physical action
Run test_solution.py with verbose output (-vv flag) to see where 
the algorithm diverges from expected output.
```

You confirm, close the laptop. **Tomorrow, you open that file and immediately continue.** You didn't lose the thread.

---

### What you see

Squirrel shows you the draft shutdown note, asks "¿Aplico?", you say "sí" or "ajustá".

### Special: The Hemingway question

After a shutdown, Squirrel asks:

```
💡 Hemingway trick: ¿Querés dejar algo incompleto para facilitar el 
   re-inicio mañana?

   Stopping mid-task (not at a natural "done") makes tomorrow easier to start.
   
   ¿Hay algo que querés dejar a medias a propósito? (sí — describí cuál / no)
```

**This is optional but powerful:** if you say "sí" and describe something like *"leave the test running but don't check the result — that way tomorrow I just need to run it and see what broke"*, Squirrel includes that in your shutdown note. Tomorrow it'll say: "Left intentionally incomplete: test running, check result."

### Flags / variants

| Command | Effect |
|---|---|
| `/sq-end` | Standard — drafts and asks confirmation |
| `/sq-end --quick` | Short shutdown for <15 min sessions (no elaborate note) |
| `/sq-end --no-commit` | Skip git commit suggestion |
| `/sq-end --force` | Skip the Hemingway question |

### Anti-pattern to avoid

❌ **Don't write generic shutdown notes** ("worked on stuff, made progress"). Be specific: what file, what line, what state, what's the next physical action. "Worked on auth" is useless. "Added CSRF token validation to POST /login; tested with Postman; next: add unit test for the validate() function in auth.ts" is gold.

---

## `/sq-where-am-i` — "What was I doing?"

### What it does

When you sit down cold and have no idea what's going on, this command reminds you of every active project, what state each one is in, and suggests what to focus on today.

### How it works

You run `/sq-where-am-i` → Squirrel reads all your active projects → Squirrel shows last activity date, current status, and one suggestion → You can then `/sq-start [PROJECT]` on the one you want.

### Real-situation examples

**Situation 1: Monday morning overwhelm**

You're Marcus. You have 4 active projects. It's Monday 9 AM and you don't know where to start. You ask:

```
/sq-where-am-i
```

Squirrel shows:

```
📋 Proyectos activos:

🟢 FREELANCE-CLIENT-A (website redesign)
   Última actividad: 2026-05-21 (3 días atrás)
   Estado: In progress, no blockers
   Sugerencia: Resumir con /sq-start FREELANCE-CLIENT-A

🟠 FREELANCE-CLIENT-B (dashboard)
   Última actividad: 2026-05-17 (7 días atrás)
   Estado: Waiting on client feedback, no action needed
   Sugerencia: Check email for client response

🔴 TAXES-2026 (tax prep)
   Última actividad: nunca
   Estado: Not started
   Sugerencia: Capturá el primer paso

🟢 SIDE-BLOG (personal project)
   Última actividad: 2026-05-20 (4 días atrás)
   Estado: Ready to work, unblocked
   Sugerencia: Resumir con /sq-start SIDE-BLOG

---
📌 Recomendación de hoy:
   Enfocate en FREELANCE-CLIENT-A (deadline cercana) o 
   FREELANCE-CLIENT-B (esperando feedback).
   
   Si querés distraerte, SIDE-BLOG está listo.
```

**Now you know exactly what's going on.** You can see at a glance which projects need attention and which are waiting.

---

**Situation 2: Jumping back after a week away**

You're Tomás. You took a week off. You're back Monday and disoriented:

```
/sq-where-am-i
```

Squirrel reminds you of everything, sorted by urgency. You might see "WORK-PROJECT-A: 8 days since activity, 2 intents in progress, ready to continue." That's your cue: `/ sq-start WORK-PROJECT-A`.

---

### What you see

A bulleted list of all WIP projects with status, last activity, and one suggestion per project. Total: ~150 words.

### Flags / variants

| Command | Effect |
|---|---|
| `/sq-where-am-i` | Full list, all WIP projects |
| `/sq-where-am-i --summary` | Ultra-short: 1 line per project |
| `/sq-where-am-i --blocked` | Show only blocked projects |
| `/sq-where-am-i --focus` | Show the TOP 1 recommended project to work on |

### Anti-pattern to avoid

❌ **Don't use this as a replacement for `/sq-start`.** This shows you the landscape; `/sq-start` actually loads one project. Use `/sq-where-am-i` to decide, then `/sq-start [PROJECT]` to load it.

---

## `/sq-status` — Big-picture overview

### What it does

The "Monday morning command." Shows every active project, progress %, deadlines, recent activity, alerts, and a recommended focus for the day. One command, full picture.

### How it works

You run `/sq-status` → Squirrel aggregates data from ALL active projects → Squirrel shows them grouped by urgency/deadline → You see what's at risk, what's healthy, what's waiting.

### Real-situation examples

**Situation 1: Weekly review Monday 9 AM**

You're Ana, a student. You have 3 classes and 2 side projects. Monday morning:

```
/sq-status
```

Squirrel shows:

```
📊 FULL STATUS — 2026-05-24

ACTIVE PROJECTS: 5
├─ 🟢 2 healthy (on track)
├─ 🟠 2 at risk (deadline soon or no recent activity)
├─ 🔴 1 critical (overdue or blocked)

---

🔴 CRITICAL PRIORITY
   SCHOOL-LAB-3 — Lab due Friday 11:59 PM (4 days, 7 hours away)
   Progress: 40% (2 of 5 parts done)
   Last activity: Never (not started!)
   Blocker: None
   Next: /sq-start SCHOOL-LAB-3 and create first intent

🟠 URGENT — This week
   SCHOOL-MIDTERM-STUDY — Midterm Thursday
   Progress: 0% (flashcards created, no review yet)
   Last activity: 1 day ago
   Next: /sq-start SCHOOL-MIDTERM-STUDY and schedule 1 hour review daily

🟢 HEALTHY — On track
   SIDE-BLOG — Personal project
   Progress: 30%
   Last activity: 2 days ago
   Next: /sq-start SIDE-BLOG

---

🔔 ALERTS
   ⚠️ SCHOOL-LAB-3: Not started yet. 4 days to deadline.
   💡 SCHOOL-MIDTERM-STUDY: 0 minutes of review. Suggest 30 min daily x 4 days.

---

📌 FOCUS TODAY
   1. SCHOOL-LAB-3 (critical, not started)
   2. SCHOOL-MIDTERM-STUDY (review time)
   3. SIDE-BLOG (if time remains)
```

**In 30 seconds, you know what's on fire and what to prioritize.**

---

**Situation 2: Manager checking a team member's work**

(You're not using Squirrel for team status yet, but imagine:) You're a lead. Your report, Tomás, sends you a `/sq-status` brief every Friday. You see in 2 minutes: 2 projects on track, 1 project blocked waiting for design, deliverable due next Wednesday. You can course-correct before Thursday.

---

### What you see

A structured status report with:
- How many projects are healthy/at-risk/critical
- Each project grouped by urgency
- Deadline info + progress %
- Alerts (if any)
- Recommended focus (numbered 1, 2, 3…)

### Flags / variants

| Command | Effect |
|---|---|
| `/sq-status` | Full report, all projects |
| `/sq-status --critical` | Show only red projects (overdue, blocked) |
| `/sq-status --upcoming` | Show only yellow projects (deadline < 7 days) |
| `/sq-status --slack` | Format for pasting into Slack (short) |

### Anti-pattern to avoid

❌ **Don't run this every 5 minutes.** It's a weekly or bi-weekly review tool, not a moment-to-moment dashboard. Run it Monday morning and Friday afternoon. That's enough.

---

## Daily rhythm

Here's how the five commands flow through a typical day:

```
📅 Morning
  ├─ /sq-where-am-i  (9 AM, decide what to work on)
  └─ /sq-start [PROJECT]  (9:15 AM, load context)

📅 During the day
  ├─ /sq-capture <idea>  (anytime: capture a new thought)
  ├─ /sq-capture <idea>  (2 PM: capture another idea)
  └─ /sq-capture <idea>  (4 PM: capture a meeting note)

📅 Afternoon / End of day
  └─ /sq-end  (5 PM, save shutdown note)

📅 Next morning
  └─ /sq-start [PROJECT]  (9 AM, load exactly where you left off)

📅 Weekly (Monday 9 AM)
  └─ /sq-status  (full landscape, plan the week)

📅 Weekly (Friday 5 PM)
  └─ /sq-status  (see what you finished, what's carrying over)
```

---

## Habit card

Print this and tape it next to your monitor:

```
┌──────────────────────────────────────────────────────────┐
│  SQUIRREL HABIT CARD — The Five Daily Commands          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  START YOUR DAY                                          │
│  ├─ /sq-where-am-i    [see what's active]              │
│  └─ /sq-start [PROJECT]  [load context]                │
│                                                          │
│  DURING THE DAY                                          │
│  └─ /sq-capture "your idea"  [save ideas anytime]     │
│                                                          │
│  END YOUR DAY                                            │
│  └─ /sq-end    [save shutdown note]                    │
│                                                          │
│  ONCE A WEEK (Monday morning)                           │
│  └─ /sq-status  [full picture]                         │
│                                                          │
│  THE RULE: Always /sq-end before closing the laptop.   │
│  This is the one habit that makes everything else work.│
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Where to go next

- **Using these commands for a week?** → Read [Working Smarter](./working-smarter.md) to learn 10 more commands for trickier situations (deadlines, big tasks, decisions, blockers).
- **Saving emails into notes, or generating email summaries for stakeholders?** → [Email Workflows](./email-workflows.md) — two recipes (`/sq-capture` for incoming email, `/sq-brief --email` for outgoing) with concrete examples and troubleshooting.
- **Want to sync between two computers?** → [Two Computers](./two-computers.md) shows the air-gap sync system.
- **Curious about power features?** → [Power User](./power-user.md) covers encryption, CLI, dashboards, and more.

Master these five commands first. Everything else is a power tool on top. 🐿️
