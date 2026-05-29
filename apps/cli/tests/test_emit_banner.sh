#!/bin/bash
# Unit tests for emit_banner orchestrator — R-1.1/R-1.3/R-1.4/R-1.7/R-2.1/R-2.2/R-2.7
# Run: bash apps/cli/tests/test_emit_banner.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON="${SCRIPT_DIR}/../../../agent-pack/companions/macos-reminders/reminder-daemon.sh"

# Extract all helper functions needed for tests (including permission-denied fallback path).
eval "$(sed -n '/^log()/,/^}$/p; /^compose_deeplink()/,/^}$/p; /^show_notification_terminal_notifier()/,/^}$/p; /^show_notification_osascript()/,/^}$/p; /^show_dialog_fallback()/,/^}$/p; /^emit_banner()/,/^}$/p' "$DAEMON" 2>/dev/null)" 2>/dev/null || true

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

# ─── Test 5: permission-denied fallback — _OSASCRIPT_PERM_DENIED flag (R-2.4) ─

PERM_TMP="$(mktemp -d)"
DIALOG_RECORD="${PERM_TMP}/dialog_calls.txt"
OSASCRIPT_STUB="${PERM_TMP}/osascript"

# Stub: exit 1 on display notification; record args + exit 0 on display dialog.
cat > "$OSASCRIPT_STUB" <<'STUB'
#!/bin/bash
for arg in "$@"; do
    if [[ "$arg" == *"display notification"* ]]; then exit 1; fi
    if [[ "$arg" == *"display dialog"* ]]; then
        printf '%s\n' "$arg" >> "${DIALOG_RECORD_FILE}"
        exit 0
    fi
done
exit 0
STUB
chmod +x "$OSASCRIPT_STUB"

export DIALOG_RECORD_FILE="$DIALOG_RECORD"

# Reset per-run flag and run two banners with NO terminal-notifier on PATH.
_OSASCRIPT_PERM_DENIED=false
OLD_LOG_LINES="$(wc -l < "${TMP_LOG}" 2>/dev/null | tr -d ' ')"

# Minimal PATH: osascript stub first, then pyenv shims (python3), then system.
# Excludes /opt/homebrew/bin so terminal-notifier is not found.
PYENV_ROOT_T="${PYENV_ROOT:-${HOME}/.pyenv}"
export PATH="${PERM_TMP}:${PYENV_ROOT_T}/shims:${PYENV_ROOT_T}/bin:/usr/bin:/bin"

emit_banner "PROJ2" "title2" "Due tomorrow" "body2"
emit_banner "PROJ3" "title3" "Due in 3d" "body3"

export PATH="$OLD_PATH"

NEW_LOG="$(tail -n +$((OLD_LOG_LINES + 1)) "${TMP_LOG}" 2>/dev/null || echo '')"

PERM_DENIED_COUNT="$(printf '%s\n' "$NEW_LOG" | grep -c 'permission-denied' || true)"
assert_eq "test5: exactly one permission-denied log line" "1" "$PERM_DENIED_COUNT"

DIALOG_CALLS="$(cat "$DIALOG_RECORD" 2>/dev/null || echo '')"
assert_contains "test5: second call used show_dialog_fallback" \
    "display dialog" "$DIALOG_CALLS"

assert_contains "test5: log has banner-fallback-dialog" \
    "banner-fallback-dialog" "$NEW_LOG"

rm -rf "$PERM_TMP"

# ─── Cleanup ─────────────────────────────────────────────────────────────────

rm -rf "$TMP_DIR"

echo ""
echo "Results: ${pass} passed, ${fail} failed"
[[ "$fail" -eq 0 ]]
