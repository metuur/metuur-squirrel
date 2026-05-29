#!/bin/bash
# Unit tests for emit_banner orchestrator — R-1.1/R-1.3/R-1.4/R-1.7/R-2.1/R-2.2/R-2.7
# Run: bash apps/cli/tests/test_emit_banner.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON="${SCRIPT_DIR}/../../../agent-pack/companions/macos-reminders/reminder-daemon.sh"

# Extract compose_deeplink, show_notification_terminal_notifier, log, and emit_banner.
# Each pattern matches from "fn() {" to the closing "}" at column-0.
eval "$(sed -n '/^log()/,/^}$/p; /^compose_deeplink()/,/^}$/p; /^show_notification_terminal_notifier()/,/^}$/p; /^emit_banner()/,/^}$/p' "$DAEMON" 2>/dev/null)" 2>/dev/null || true

pass=0; fail=0

assert_contains() {
    local label="$1" needle="$2" haystack="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        printf 'PASS  %s\n' "$label"; (( pass++ )) || true
    else
        printf 'FAIL  %s\n  missing: %s\n  in:      %s\n' "$label" "$needle" "$haystack"
        (( fail++ )) || true
    fi
}

assert_not_contains() {
    local label="$1" needle="$2" haystack="$3"
    if [[ "$haystack" != *"$needle"* ]]; then
        printf 'PASS  %s\n' "$label"; (( pass++ )) || true
    else
        printf 'FAIL  %s\n  found (should be absent): %s\n  in:                      %s\n' \
            "$label" "$needle" "$haystack"
        (( fail++ )) || true
    fi
}

assert_eq() {
    local label="$1" want="$2" got="$3"
    if [[ "$got" == "$want" ]]; then
        printf 'PASS  %s\n' "$label"; (( pass++ )) || true
    else
        printf 'FAIL  %s\n  want: %s\n  got:  %s\n' "$label" "$want" "$got"
        (( fail++ )) || true
    fi
}

# ─── Guard: verify functions are defined ─────────────────────────────────────

for fn in compose_deeplink show_notification_terminal_notifier emit_banner; do
    if ! declare -f "$fn" >/dev/null 2>&1; then
        echo "FAIL  $fn not defined in $DAEMON"
        exit 1
    fi
done

# ─── Shared temp dir ─────────────────────────────────────────────────────────

TMP_DIR="$(mktemp -d)"
RECORD_FILE="${TMP_DIR}/recorded_args.txt"
RECORDER="${TMP_DIR}/terminal-notifier"

# Stub: write one arg per line so multi-word args are preserved faithfully.
cat > "$RECORDER" <<STUB
#!/bin/bash
printf '%s\n' "\$@" >> "${RECORD_FILE}"
STUB
chmod +x "$RECORDER"

OLD_PATH="$PATH"

# Override LOG_FILE to a temp path so we don't touch the real daemon log.
TMP_LOG="${TMP_DIR}/test-daemon.log"
export LOG_FILE="${TMP_LOG}"
export MAX_LOG_LINES=500

# ─── Test 1: title is composed as "⏰ squirrel: <PROJECT>" ───────────────────

export PATH="${TMP_DIR}:${OLD_PATH}"

emit_banner "PROJ" "My title" "Due tomorrow" ""

export PATH="$OLD_PATH"

RECORDED="$(cat "${RECORD_FILE}" 2>/dev/null || echo '')"

# Each arg is on its own line; the line after "-title" is the title value.
TITLE_VAL="$(awk '/^-title$/{getline; print; exit}' "${RECORD_FILE}" 2>/dev/null || echo '')"

assert_eq "test1: title is '⏰ squirrel: PROJ'" \
    "⏰ squirrel: PROJ" "$TITLE_VAL"
assert_contains "test1: record contains -title flag" \
    "-title" "$RECORDED"

# ─── Test 2: body containing next_action appears in -message ─────────────────

rm -f "${RECORD_FILE}"
export PATH="${TMP_DIR}:${OLD_PATH}"

# Body pre-constructed by caller with next_action appended (R-1.4 pattern)
emit_banner "PROJ" "My title" "Due tomorrow" "My title · → fix X"

export PATH="$OLD_PATH"

MSG_VAL2="$(awk '/^-message$/{getline; print; exit}' "${RECORD_FILE}" 2>/dev/null || echo '')"
assert_contains "test2: -message contains 'fix X'" \
    "fix X" "$MSG_VAL2"

# ─── Test 3: 300-char body is truncated to 240 codepoints ending with … ──────

# Build a 300-character body (all ASCII = 300 codepoints)
LONG_BODY="$(python3 -c "print('A' * 300, end='')")"

rm -f "${RECORD_FILE}"
export PATH="${TMP_DIR}:${OLD_PATH}"

emit_banner "PROJ" "note title" "subtitle" "$LONG_BODY"

export PATH="$OLD_PATH"

MSG_VAL3="$(awk '/^-message$/{getline; print; exit}' "${RECORD_FILE}" 2>/dev/null || echo '')"

assert_contains "test3: truncated body ends with …" \
    "…" "$MSG_VAL3"

CODEPOINTS="$(python3 -c "import sys; b = sys.argv[1]; print(len(b))" "$MSG_VAL3" 2>/dev/null || echo -1)"
assert_eq "test3: truncated body is exactly 240 codepoints" "240" "$CODEPOINTS"

# ─── Test 4: log file contains 'banner' and 'PROJ' ───────────────────────────

rm -f "${RECORD_FILE}"
export PATH="${TMP_DIR}:${OLD_PATH}"

emit_banner "PROJ" "log test title" "subtitle" ""

export PATH="$OLD_PATH"

LAST_LOG_LINE="$(tail -1 "${TMP_LOG}" 2>/dev/null || echo '')"
assert_contains "test4: log line contains 'banner'" \
    "banner" "$LAST_LOG_LINE"
assert_contains "test4: log line contains 'PROJ'" \
    "PROJ" "$LAST_LOG_LINE"

# ─── Cleanup ─────────────────────────────────────────────────────────────────

rm -rf "$TMP_DIR"

echo ""
echo "Results: ${pass} passed, ${fail} failed"
[[ "$fail" -eq 0 ]]
