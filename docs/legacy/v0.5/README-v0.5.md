# 🌉 squirrel v0.5.0

> A Markdown-based, multi-agent context and task management system with an air gap between personal and corporate environments, **optimized for minimal LLM token usage**.

Plugin for Claude Code, Codex, Cursor, and other LLM agents. Designed specifically for software engineers with ADHD who work across multiple simultaneous projects.

---

## 🆕 What’s new in v0.2.0

### “Scripts-first” architecture
The key difference from v0.1.0: **scripts do the deterministic work, the LLM only makes the judgment call**.

Before:
- The LLM read 30+ `.md` files from the vault
- Parsed frontmatter, sections, and dates
- Calculated percent done, days since activity, and deadlines
- Composed the output

Now:
- A Python script scans the vault and returns structured JSON
- The LLM consumes the JSON and formats it
- **Savings: 45-80% in tokens depending on the operation**

### 6 new scripts (stdlib-only, no dependencies)

| Script | Function |
|---|---|
| `intent_parser.py` | YAML frontmatter + Markdown section parser |
| `status_aggregator.py` | Central aggregator — the game changer |
| `deadline_scanner.py` | Parakeet engine: classifies deadlines in 6 levels |
| `switch_tracker.py` | Tracks context switches, calculates `focus_score` |
| `estimate_buffer.py` | ADHD multiplier for estimates (×2-3) |
| `chunk_helper.py` | Breaks tasks into ADHD-friendly chunks/sessions |

### Test suite
24 automated tests covering parsing, stats computation, and end-to-end CLIs.

```bash
python3 -m unittest tests.test_foundation
# Ran 24 tests in 0.139s — OK
```

---

## 📊 Token budget per operation

| Operation | v0.1.0 | v0.2.0 | Savings |
|---|---|---|---|
| `/sq-where-am-i` | ~3000 | ~500 | **6×** |
| `/sq-status` | ~3000 | ~500 | **6×** |
| `/sq-brief X` | ~2500 | ~800 | **3×** |
| `/sq-start X` | ~2000 | ~500 | **4×** |
| `/sq-sync-out` | ~2000 | ~600 | **3×** |
| `/sq-sync-in` | ~2500 | ~800 | **3×** |

**Typical 1-hour session**: 25K tokens → 10K tokens. **2.5× total savings**.

---

## 🚀 Quick start

### 1. Try the scripts without installing anything

```bash
# Full vault status
python3 lib/status_aggregator.py --vault ~/vault-tdah --pretty

# Critical deadlines
python3 lib/deadline_scanner.py --vault ~/vault-tdah --level critical,urgent

# Time estimate with ADHD buffer
python3 lib/estimate_buffer.py --estimate "2 hours"

# Chunk a large task
python3 lib/chunk_helper.py --hours 8 --pretty

# Tests
python3 -m unittest tests.test_foundation
```

### 2. Install in Claude Code

```bash
cp -r squirrel ~/.claude/plugins/
```

Restart → slash commands `/sq-*` should appear.

### 3. Initialize and use

```
/cb-init           # configuration
/cb-where-am-i     # diagnostic (uses the script — cheap)
/cb-start FOO      # load context
/cb-end            # save shutdown note
/cb-brief FOO      # stakeholder status
/cb-sync-out       # export to another environment
```

---

## 🏗️ Repository structure

```
squirrel/
├── .claude-plugin/plugin.json
├── ARCHITECTURE.md              # v0.1 design
├── README.md                    # This file
├── INSTALL.md
│
├── docs/
│   ├── ANALYSIS-skills-externas.md
│   └── PLAN-construccion-v0.2.md
│
├── skills/                      # 8 skills, thin SKILL.md files
│   ├── capture/  session-start/  session-end/
│   ├── brief/    decision/
│   ├── sync-out/ sync-in/
│   └── where-am-i/              # NEW — first v0.2 script-driven skill
│
├── commands/                    # 10 slash commands
│
├── hooks/hooks.json             # Proactive hooks
│
├── lib/                         # ★ The core
│   ├── intent_parser.py
│   ├── status_aggregator.py
│   ├── deadline_scanner.py
│   ├── switch_tracker.py
│   ├── estimate_buffer.py
│   ├── chunk_helper.py
│   └── package_protocol.py
│
├── tests/
│   ├── test_foundation.py       # 24 tests
│   └── fixtures/vault-minimal/
│
├── templates/
└── examples/
```

---

## 🛣️ Roadmap

### v0.2.0 ✅
- [x] 6-script foundation with 24 tests
- [x] Token savings demonstrated (45% in minimal vault, 5-10× projected in a real vault)
- [x] `where-am-i` skill refactored to be script-driven
- [x] Analysis of 7 external ADHD skills incorporated

### v0.3.0 (current) ✅
- [x] `hyperfocus-guardian` skill — circuit breaker for long sessions
- [x] `parakeet` skill — deadline reminders with urgency-based tone
- [x] `task-initiation` skill — 4 protocols against startup paralysis
- [x] `chunk-intent` skill — breaks large intents into chunks ≤60 min
- [x] Standalone `cb` CLI — status / deadlines / chunk / estimate / recover / dashboard
- [x] HTML dashboard generator — static vault view with auto-refresh
- [x] Dataview templates (4) — Obsidian dashboards
- [x] 55 tests (19 new for the `cb` CLI + dashboard)

### v0.4.0 (current) ✅
- [x] Refactored `session-start` + `brief` skills to be script-driven (`--detailed` flag in `status_aggregator`)
- [x] Added academic references to 5 legacy skills (session-end, capture, decision, sync-in, sync-out)
- [x] `cb install` — automated installation for Claude Code, Codex, and Cursor with `--dry-run`
- [x] Codex `AGENTS.md` + Cursor MDC manifest in `companions/`
- [x] End-to-end GPG encryption in `package_protocol.py` (`--encrypt` / `--decrypt` / auto-detect `.gpg`)

---

## 🙏 Credits

### Theoretical foundations
David Allen (GTD), Tiago Forte (PARA), Cal Newport (Deep Work), Hemingway (stop while it’s going well), Brendan Mahan (Wall of Awful), William Dodson (Interest-Based Nervous System), Michael Nygard (ADR), Ryder Carroll (Bullet Journal).

### External skills analyzed (v0.2.0)
project-management-guru-adhd, hyperfocus-management, context-switching, parakeet-reminders, task-chunking, executive-function-toolkit, dopamine-menu. See `docs/ANALYSIS-skills-externas.md` for what was incorporated and what was not.

### Research
- Barkley (2015): "Attention-Deficit Hyperactivity Disorder" (4th ed)
- Hallowell & Ratey (2021): "ADHD 2.0"
- Leroy (2009): "Why Is It So Hard to Do My Work?" (context switching cost)
- Mark et al. (2008): "The Cost of Interrupted Work"
- Ashinoff & Abu-Akel (2021): "Hyperfocus: The Forgotten Frontier of Attention"

## 📜 License

MIT
