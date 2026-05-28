# Your First 10 Minutes — The Full Loop

> 🎯 *What you'll learn:* You'll run the complete capture → start → work → end cycle, see what files get created, and prove to yourself that the whole system works.

**Version:** Squirrel v0.5.0  
**Last updated:** 2026-05-24  
**Reading time:** ~12 minutes

---

## Table of Contents

1. [The loop diagram](#the-loop-diagram)
2. [Minute 1–2: Capture an idea](#minute-12-capture-an-idea)
3. [Minute 3–5: Start a work session](#minute-35-start-a-work-session)
4. [Minute 6–8: Do some "work"](#minute-68-do-some-work)
5. [Minute 9–10: End the session](#minute-910-end-the-session)
6. [What you created](#what-you-created)
7. [Common first-timer mistakes](#common-first-timer-mistakes)

---

## The loop diagram

This is Squirrel's core cycle. You'll repeat it hundreds of times:

```
   You (user)              Claude Code + Squirrel
   ─────────              ──────────────────────

   Have idea       ──→    /sq-capture
   (anytime)             (saves to vault)

   Sit down        ──→    /sq-start [PROJECT]
   to work              (loads context)

   Work for        ──→   (chat, edit files,
   30–120 min          implement stuff)

   Stop working    ──→    /sq-end
   (lunch, tired)         (saves shutdown note)

      [Tomorrow]
   Sit down again  ──→    /sq-start [PROJECT]
   (repeat)              (remembers exactly where
                          you left off)
```

The magic: at each transition, Squirrel reads/writes plain-text Markdown files. No cloud sync, no magic — just files on your disk that your AI assistant reads and helps you interpret.

---

## Minute 1–2: Capture an idea

**Scenario:** You're Tomás, a developer working on a recipe app. While in Claude Code, an idea hits you: *"The search should show results as you type, not wait for Enter."*

You don't want to forget this, so you capture it right now:

```
/sq-capture Show search results in real-time, not on Enter key press. Make UX snappier.
```

**What Squirrel does:**

Squirrel looks at your text, figures out it belongs to `RECIPE-APP` (from your active projects list), and creates a file:

```
~/vault-notas/03-Recursos/Captures/RECIPE-APP-NOTES-001.md
```

**The file looks like this:**

```markdown
---
id: RECIPE-APP-NOTES-001
proyecto: RECIPE-APP
tipo: capture
creado: 2026-05-24
tags: [capture, proyecto/RECIPE-APP]
---

# Idea: Real-time search results

Show search results in real-time, not on Enter key press. Make UX snappier.
```

The block at the top between the `---` lines is **frontmatter** — metadata that Squirrel uses to know what kind of note this is, which project it belongs to, and when it was created.

✅ **You just created your first Squirrel file.** You can open it in any text editor, or it'll stay in Squirrel's vault and get linked to your project automatically.

---

## Minute 3–5: Start a work session

Now it's tomorrow morning. You sit down to work on `RECIPE-APP`. You tell Claude Code:

```
/sq-start RECIPE-APP
```

**What Squirrel does:**

Squirrel:
1. Reads everything it knows about `RECIPE-APP` (all capture notes, past shutdown notes, decisions)
2. Finds the latest shutdown note from your previous session (if any)
3. Writes a "loading note" — a brief summary that tells you exactly where to resume

**You see:**

```
## 🔵 Sesión: RECIPE-APP
Última actividad: 2026-05-23 (1 día atrás)

### 🎯 Estás haciendo
Backend API for ingredient search. You were testing the search endpoint with Postman.

### ✅ Lo último que hiciste
- Added GET /api/search?q=<term> endpoint
- Tested with sample data
- Noticed results were slow (0.8s per request)

### 🎬 Próximo paso físico
Open database/recipes.db and add an INDEX on the ingredient_name column.
Line 47 of lib/db.py shows the table schema.

### 💡 Decisiones clave
- Using SQLite, not PostgreSQL (simpler for MVP)

### 🚧 Bloqueos / preguntas abiertas
None — you're unblocked.

### 🔧 Sugerencia de apertura
1. Abrí lib/db.py línea 47
2. Agregá el INDEX
3. 25 minutos: testeá con Postman de nuevo

---
¿Empezamos por 1?
```

**Notice:** This brief is short (7 lines of actual content), super concrete ("open lib/db.py line 47"), and action-oriented. No fluff. Tomorrow-you doesn't have to re-read 20 files.

---

## Minute 6–8: Do some "work"

You say "sí" to the suggestion, and you and Claude Code have a brief chat:

**You:** "Sí, abrí el archivo. Agregá el índice en la columna ingredient_name."

**Claude Code:** 
```python
# lib/db.py, around line 47
def init_db():
    conn = sqlite3.connect('recipes.db')
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY,
            ingredient_name TEXT NOT NULL
        )
    ''')
    
    # Add this line:
    c.execute('CREATE INDEX IF NOT EXISTS idx_ingredient_name ON ingredients(ingredient_name)')
    
    conn.commit()
    conn.close()
```

**You:** "Copié ese cambio. Ahora corro el test de búsqueda."

**Claude Code:** "Dale, ejecutá tests/test_search.py"

You run the test, it passes. You say:

**You:** "Pasó. Ahora la búsqueda es casi instantánea. Listo para UI."

(This is the conversation Claude Code sees, and it'll remember all of this in your shutdown note.)

---

## Minute 9–10: End the session

Lunch time. You type:

```
/sq-end
```

**What Squirrel does:**

Squirrel:
1. Reads your chat history (the conversation above)
2. Extracts what you did (added index, tested, passed)
3. Asks Hemingway question: "Do you want to leave something intentionally incomplete for tomorrow?"
4. Drafts a shutdown note
5. Asks for your confirmation
6. Writes it to your `RECIPE-APP` project folder

**The draft it shows you:**

```markdown
### 2026-05-24 12:30
- **Estado**: Índice en ingredient_name completado y testeado. Tests passing. 
             Búsqueda ahora instantánea. Ready for UI layer.

- **Next physical action**: Abrir components/SearchBox.tsx y agregar onChange handler 
                            que llame a /api/search en real-time.

- **Hipótesis activa**: Real-time search will improve user engagement (lower bounce).

- **Bloqueado por**: Nada.

- **Decisiones tomadas hoy**: Confirmamos que indexing en SQLite es suficiente 
                              (no necesitamos migrar a PostgreSQL todavía).

- **Open loops**: ¿Debería debounce la búsqueda (0.3s delay) o buscar directamente? 
                  Revisar en próxima sesión.

- **Hemingway**: Paramos con tests pasando. Punto de partida bueno para mañana.
```

You review it and say "sí".

✅ **Done.** The shutdown note is now saved in your vault. Tomorrow, when you run `/sq-start RECIPE-APP` again, this note will be the first thing Squirrel reads, and it'll tell you exactly what to do next.

---

## What you created

Open your vault folder and look at what exists now:

```
~/vault-notas/
├── 01-Proyectos-Activos/
│   └── RECIPE-APP/
│       ├── RECIPE-APP.md              ← Project Page (auto-created)
│       └── RECIPE-APP-INTENT-001.md   ← Main intent (auto-created)
│           (Contains your shutdown notes, goal, Definition of Done)
│
├── 03-Recursos/
│   └── Captures/
│       └── RECIPE-APP-NOTES-001.md    ← Your captured idea
│
└── .squirrel/
    └── state.json                     ← Current session state
```

**Three files, all plain Markdown:**
1. **RECIPE-APP.md** — the project overview (goal, stakeholders, deadline)
2. **RECIPE-APP-INTENT-001.md** — the main task, with your shutdown notes nested inside
3. **RECIPE-APP-NOTES-001.md** — your captured idea

All of these are human-readable. You can open them in Obsidian, VSCode, Notepad, or any editor.

---

## What happens next time

Tomorrow morning, you sit down and run:

```
/sq-start RECIPE-APP
```

Squirrel reads those three files, finds your latest shutdown note, and produces a fresh loading brief:

```
### 🎬 Próximo paso físico
Abrir components/SearchBox.tsx y agregar onChange handler que llame a 
/api/search en real-time.

### 🎯 Open loops
¿Debería debounce la búsqueda (0.3s delay) o buscar directamente?
```

**Zero friction.** You don't have to re-read anything. You already know:
- What you were doing
- The exact next physical action (open file X)
- What's unclear and needs a decision

This is the whole point of Squirrel.

---

## Common first-timer mistakes

### ❌ Mistake 1: Forgetting to `/sq-end`

**What happens:** You work for an hour, then close Claude Code without running `/sq-end`. Tomorrow you sit down and run `/sq-start RECIPE-APP`, but Squirrel has no shutdown note from yesterday. So the loading brief is vague: "You were working on something. Not sure what."

**Fix:** `/sq-end` is a habit you build, like saving a document. The moment you feel yourself "done" or "pausing", type `/sq-end`. Takes 30 seconds. Prevents tomorrow's 15 minutes of "where was I?"

**If you already forgot:** Run `/sq-recover` and Squirrel will scan your chat history to reconstruct the shutdown note. Not perfect, but usually 80% there.

### ❌ Mistake 2: Using vague project codes

**What happens:** You captured "Let me add caching", but your project codes are `WORK`, `HOME`, `SIDE`. Squirrel can't figure out which project it belongs to and asks you to pick.

**Fix:** Use clear, specific codes from the start: `WORK-PROJECT-A`, `SIDE-BLOG`, `TRIP-JAPAN-2026`. If you realize a code is bad, edit `config.toml` and rename it in the vault folder too.

### ❌ Mistake 3: Pasting the wrong thing into `/sq-capture`

**What happens:** You capture "finish the report", but you meant to capture "add caching to the login endpoint". Now your notes are messy.

**Fix:** It's okay, just create another capture with the right text. Old captures don't hurt. If you really want to delete one, open the file and delete it manually (it's just a `.md` file).

### ❌ Mistake 4: Not creating intents

**What happens:** You've captured 10 ideas, but you never run `/sq-start [PROJECT]` to begin actual work. All those captures sit in 03-Recursos/ and never become real intents.

**Fix:** Captures are *ideas*. When you're ready to actually work on one, run `/sq-start [PROJECT]` and tell Claude Code which capture to turn into your first intent. Then Squirrel will create the intent file and you can start the loop.

### ❌ Mistake 5: Editing shutdown notes after the fact

**What happens:** You run `/sq-end`, save a shutdown note, then an hour later realize "wait, I should mention X". You edit the shutdown note file directly.

**Fix:** It's fine to edit! The notes are just Markdown files. But for audit purposes, Squirrel keeps ALL shutdown notes (they're appended, not overwritten). So if you realize something later, just create a new capture or add a comment to the note. Don't stress about perfect notes — they're good-enough if they help you resume the next day.

---

## Where to go next

- **Done with the loop?** → Read [Everyday Use](./everyday-use.md) to learn the 5 core commands you'll use daily.
- **Want intermediate tricks?** → [Working Smarter](./working-smarter.md) shows 10 more commands for trickier situations (deadlines, big tasks, decisions).
- **Feeling confident?** → Jump straight to [everyday use](./everyday-use.md) and start using Squirrel for real work.

You now know the whole core loop. The rest of Squirrel is just variations on this theme. 🐿️
