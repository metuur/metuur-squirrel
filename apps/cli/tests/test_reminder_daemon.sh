#!/bin/bash
# Unit tests for emit_banner emitter selection via PATH manipulation (R-9.1).
# Three scenarios → three log tags: banner, banner-fallback-osascript, banner-fallback-dialog.
# Run: bash apps/cli/tests/test_reminder_daemon.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON="${SCRIPT_DIR}/../../../agent-pack/companions/macos-reminders/reminder-daemon.sh"

# Extract all helpers needed for emit_banner.
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
        printf 'FAIL  %s\n  found (should be absent): %s\n  in: %s\n' "$label" "$needle" "$haystack"
        (( fail++ )) || true
    fi
}

for fn in compose_deeplink show_notification_terminal_notifier emit_banner; do
    if ! declare -f "$fn" >/dev/null 2>&1; then
        echo "FAIL  $fn not defined in $DAEMON"
        exit 1
    fi
done

# ─── Shared setup ────────────────────────────────────────────────────────────

TMP_DIR="$(mktemp -d)"
TMP_LOG="${TMP_DIR}/test-daemon.log"
export LOG_FILE="${TMP_LOG}"
export MAX_LOG_LINES=500

OLD_PATH="$PATH"
PYENV_ROOT_T="${PYENV_ROOT:-${HOME}/.pyenv}"
# Minimal system path: pyenv shims (python3) + /usr/bin + /bin.
# /opt/homebrew/bin is intentionally excluded so terminal-notifier is not found.
MINIMAL_PATH="${PYENV_ROOT_T}/shims:${PYENV_ROOT_T}/bin:/usr/bin:/bin"

# ─── Scenario A: terminal-notifier on PATH → tag "banner" ────────────────────

SA_TMP="$(mktemp -d)"
SA_TN="${SA_TMP}/terminal-notifier"
SA_RECORD="${SA_TMP}/tn_calls.txt"

cat > "$SA_TN" <<STUB
#!/bin/bash
printf '%s\n' "\$@" >> "${SA_RECORD}"
exit 0
STUB
chmod +x "$SA_TN"

_OSASCRIPT_PERM_DENIED=false
export PATH="${SA_TMP}:${MINIMAL_PATH}"

emit_banner "PROJ-A" "title-A" "subtitle-A" "body-A"

export PATH="$OLD_PATH"

LOG_A="$(cat "${TMP_LOG}" 2>/dev/null || echo '')"
assert_contains "scenarioA: log tag is 'banner'" "banner project=PROJ-A" "$LOG_A"
assert_not_contains "scenarioA: no osascript fallback tag" "banner-fallback" "$LOG_A"

rm -rf "$SA_TMP"
> "${TMP_LOG}"

# ─── Scenario B: no terminal-notifier; osascript succeeds → "banner-fallback-osascript" ─

SB_TMP="$(mktemp -d)"
SB_OA="${SB_TMP}/osascript"
SB_RECORD="${SB_TMP}/oa_calls.txt"

cat > "$SB_OA" <<STUB
#!/bin/bash
printf '%s\n' "\$@" >> "${SB_RECORD}"
exit 0
STUB
chmod +x "$SB_OA"

_OSASCRIPT_PERM_DENIED=false
export PATH="${SB_TMP}:${MINIMAL_PATH}"   # no terminal-notifier

emit_banner "PROJ-B" "title-B" "subtitle-B" "body-B"

export PATH="$OLD_PATH"

LOG_B="$(cat "${TMP_LOG}" 2>/dev/null || echo '')"
assert_contains "scenarioB: log tag is 'banner-fallback-osascript'" \
    "banner-fallback-osascript project=PROJ-B" "$LOG_B"
assert_not_contains "scenarioB: no terminal-notifier tag" "banner project=" "$LOG_B"
assert_not_contains "scenarioB: no dialog tag" "banner-fallback-dialog" "$LOG_B"

rm -rf "$SB_TMP"
> "${TMP_LOG}"

# ─── Scenario C: no terminal-notifier; osascript fails → "banner-fallback-dialog" ──

SC_TMP="$(mktemp -d)"
SC_OA="${SC_TMP}/osascript"
SC_RECORD="${SC_TMP}/dialog_calls.txt"

cat > "$SC_OA" <<'STUB'
#!/bin/bash
for arg in "$@"; do
    if [[ "$arg" == *"display notification"* ]]; then exit 1; fi
    if [[ "$arg" == *"display dialog"* ]]; then
        printf '%s\n' "$arg" >> "${SC_DIALOG_RECORD}"
        exit 0
    fi
done
exit 0
STUB
chmod +x "$SC_OA"

export SC_DIALOG_RECORD="$SC_RECORD"

_OSASCRIPT_PERM_DENIED=false
export PATH="${SC_TMP}:${MINIMAL_PATH}"   # no terminal-notifier; osascript stubs

emit_banner "PROJ-C" "title-C" "subtitle-C" "body-C"

export PATH="$OLD_PATH"

LOG_C="$(cat "${TMP_LOG}" 2>/dev/null || echo '')"
assert_contains "scenarioC: log tag is 'banner-fallback-dialog'" \
    "banner-fallback-dialog project=PROJ-C" "$LOG_C"
assert_contains "scenarioC: permission-denied logged" "permission-denied" "$LOG_C"

DIALOG_CONTENT="$(cat "$SC_RECORD" 2>/dev/null || echo '')"
assert_contains "scenarioC: show_dialog_fallback was called" "display dialog" "$DIALOG_CONTENT"

rm -rf "$SC_TMP"

# ─── Cleanup ─────────────────────────────────────────────────────────────────

rm -rf "$TMP_DIR"

echo ""
echo "Results: ${pass} passed, ${fail} failed"
[[ "$fail" -eq 0 ]]
