---
description: Applies the focus buffer to a time estimate. Usage: /sq-estimate <duration>
allowed-tools: [Bash]
---

# /sq-estimate

Arguments: `$ARGUMENTS`

Applies the focus multiplier to the provided estimate by running `estimate_buffer.py`.

## Step 1: Validate the argument

`$ARGUMENTS` is the user's estimate (e.g. `2h`, `30 min`, `1.5 hours`, `90`).
If empty, ask: "How long do you estimate this will take?"

## Step 2: Locate the script

```bash
SCRIPT=""
for candidate in \
    "${HOME}/.claude/plugins/squirrel/lib/estimate_buffer.py" \
    "$(find "${HOME}/.claude" -name 'estimate_buffer.py' 2>/dev/null | head -1)" \
    "$(find "${HOME}/others" -name 'estimate_buffer.py' -path '*/squirrel/*' 2>/dev/null | head -1)"; do
  [ -f "$candidate" ] && SCRIPT="$candidate" && break
done
[ -z "$SCRIPT" ] && echo "❌ estimate_buffer.py not found. Check the plugin installation." && exit 1
```

## Step 3: Run the script

```bash
RESULT=$(python3 "$SCRIPT" --estimate "$ARGUMENTS" --pretty 2>&1)
EXIT_CODE=$?
```

If `EXIT_CODE != 0`, show the error and stop.

## Step 4: Render the result

With the returned JSON, render:

```
⏱️  Estimate with focus buffer

  Your estimate:   <user_estimate_human>
  Multiplier:      ×<multiplier>
  Real estimate:   <adjusted_human>

  💡 <explanation>
```

Then offer: "Want me to break <adjusted_human> into manageable chunks? Run /sq-chunk <adjusted_human>."
