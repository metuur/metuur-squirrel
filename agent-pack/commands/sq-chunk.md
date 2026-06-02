---
description: Breaks a time estimate into manageable chunks with a per-phase distribution. Usage: /sq-chunk <duration> [--custom-phases name1=N,name2=M]
allowed-tools: [Bash]
---

# /sq-chunk

Arguments: `$ARGUMENTS`

Breaks the task into manageable chunks by running `chunk_helper.py`.

## Step 1: Parse arguments

From `$ARGUMENTS` extract:
- **duration**: number + unit (e.g. `4h`, `90min`, `2.5 hours`, `240 minutes`). Convert to `--hours N` or `--minutes N` for the script.
- **--custom-phases**: if present, pass it through as `--custom-phases "..."`.
- **--threshold**: minimum minutes before chunking kicks in (default: 120). Pass as `--threshold N` to the script if present.

If no duration is specified, ask: "How long do you estimate this task will take?"

## Step 2: Locate the script

```bash
SCRIPT=""
for candidate in \
    "${HOME}/.claude/plugins/squirrel/lib/chunk_helper.py" \
    "$(find "${HOME}/.claude" -name 'chunk_helper.py' 2>/dev/null | head -1)" \
    "$(find "${HOME}/others" -name 'chunk_helper.py' -path '*/squirrel/*' 2>/dev/null | head -1)"; do
  [ -f "$candidate" ] && SCRIPT="$candidate" && break
done
[ -z "$SCRIPT" ] && echo "❌ chunk_helper.py not found. Check the plugin installation." && exit 1
```

## Step 3: Run the script

```bash
RESULT=$(python3 "$SCRIPT" --hours <N> --threshold <T> --pretty 2>&1)
EXIT_CODE=$?
```

If `EXIT_CODE != 0`, show the error and stop.

## Step 4: Render the result

If the JSON contains `"below_threshold": true`, show:

```
✅ This task is ≤{threshold_minutes}min — no chunking needed. Want to start right away?
```

Otherwise, with the returned JSON, render:

```
🧩 Chunk Plan — <total_human>

Phases:
  🔬 Research & Planning   (<min>min)  → <n_chunks> chunk(s)
  🛠  Setup & Scaffolding   (<min>min)  → <n_chunks> chunk(s)
  ⚙️  Core Implementation   (<min>min)  → <n_chunks> chunk(s)
  ✨ Polish & Edge Cases    (<min>min)  → <n_chunks> chunk(s)
  🧪 Testing & Docs         (<min>min)  → <n_chunks> chunk(s)

Suggested sessions (<total_chunks> chunks across <N> session(s)):
  📅 Session 1 (<total_minutes>min): [chunk1, chunk2, ...]
  📅 Session 2 (<total_minutes>min): [...]

Estimate: ~<estimated_days> day(s) of work
```

Then ask: "Want to name the chunks for this specific intent?"
If yes, ask for the intent name and propose contextual names for each chunk.
