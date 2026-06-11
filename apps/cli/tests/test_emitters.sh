#!/bin/bash
# Unit tests for three emitter functions — R-1.5/R-1.6/R-2.3/R-2.5/R-2.6
# Run: bash apps/cli/tests/test_emitters.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON="${SCRIPT_DIR}/../../../agent-pack/companions/macos-reminders/reminder-daemon.sh"

# Extract each function body from the daemon without executing the rest of the
# script (which would die on missing config / vault_path).  We extract every
# top-level function we need in order to source them cleanly.
extract_fn() {
    local fn="$1"
    # Grab lines from "fn() {" to the matching closing "}" at col-0
    sed -n "/^${fn}()/,/^}$/p" "$DAEMON" 2>/dev/null
}

eval "$(extract_fn show_notification_terminal_notifier)" 2>/dev/null || true
eval "$(extract_fn show_notification_osascript)"         2>/dev/null || true
eval "$(extract_fn show_dialog_fallback)"                2>/dev/null || true

pass=0; fail=0

assert_eq() {
    local label="$1" want="$2" got="$3"
    if [[ "$got" == "$want" ]]; then
        printf 'PASS  %s\n' "$label"; (( pass++ )) || true
    else
        printf 'FAIL  %s\n  want: %s\n  got:  %s\n' "$label" "$want" "$got"
        (( fail++ )) || true
    fi
}

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

# ─── Guard: verify functions are defined ─────────────────────────────────────

for fn in show_notification_terminal_notifier show_notification_osascript show_dialog_fallback; do
    if ! declare -f "$fn" >/dev/null 2>&1; then
        echo "FAIL  $fn not defined in $DAEMON"
        exit 1
    fi
done

# ─── Test 1: show_notification_terminal_notifier ─────────────────────────────
# Stub terminal-notifier: records all argv into a tmp file, then exits 0.
# notification-icon-branding R-6.1/R-6.2: exercise BOTH the sounded and Silent
# branches and assert each carries -sender com.metuur.squirrel (R-2.1) with the
# -open URL — including its ?action= query — unchanged (R-2.3), and that sound
# stays orthogonal to -sender (R-2.2: sounded keeps -sound, Silent omits it).

TMP_DIR="$(mktemp -d)"
RECORDER="${TMP_DIR}/terminal-notifier"
RECORD_FILE="${TMP_DIR}/recorded_args.txt"

# The stub records argv into RECORD_FILE (path baked in) and exits 0.
cat > "$RECORDER" <<STUB
#!/bin/bash
echo "\$@" >> "${RECORD_FILE}"
STUB
chmod +x "$RECORDER"

# Prepend stub dir so our fake terminal-notifier wins
OLD_PATH="$PATH"
export PATH="${TMP_DIR}:${PATH}"
export RECORD_FILE

# Deep-link with an ?action= query — R-2.1/R-2.3 require it survives -open verbatim.
URL="squirrel://projects/PROJ?action=focus"

# ── 1a: sounded branch (SOUND set to a real cue) ─────────────────────────────
SOUND="Glass"
: > "$RECORD_FILE"
show_notification_terminal_notifier \
    "⏰ squirrel: PROJ" "due in 2h" "Title of the note" "$URL"
SOUNDED="$(cat "${RECORD_FILE}" 2>/dev/null || echo '')"

assert_contains "tn(sound): has -title"                       "-title"                        "$SOUNDED"
assert_contains "tn(sound): has -subtitle"                    "-subtitle"                     "$SOUNDED"
assert_contains "tn(sound): has -message"                     "-message"                      "$SOUNDED"
assert_contains "tn(sound): has -open"                        "-open"                         "$SOUNDED"
assert_contains "tn(sound): -open carries URL incl. ?action=" "$URL"                          "$SOUNDED"
assert_contains "tn(sound): has -group org.squirrel.reminders" "-group org.squirrel.reminders" "$SOUNDED"
assert_contains "tn(sound): keeps -sound (R-2.2)"             "-sound Glass"                  "$SOUNDED"
assert_contains "tn(sound): has -sender (R-2.1)"             "-sender com.metuur.squirrel"   "$SOUNDED"

# ── 1b: Silent branch (SOUND=Silent → omits -sound, retains -sender) ─────────
SOUND="Silent"
: > "$RECORD_FILE"
show_notification_terminal_notifier \
    "⏰ squirrel: PROJ" "due in 2h" "Title of the note" "$URL"
SILENT="$(cat "${RECORD_FILE}" 2>/dev/null || echo '')"

assert_contains "tn(silent): -open carries URL incl. ?action=" "$URL"                         "$SILENT"
assert_contains "tn(silent): has -group org.squirrel.reminders" "-group org.squirrel.reminders" "$SILENT"
assert_contains "tn(silent): has -sender (R-2.1)"            "-sender com.metuur.squirrel"   "$SILENT"
assert_not_contains "tn(silent): omits -sound (R-2.2)"       "-sound"                        "$SILENT"

export PATH="$OLD_PATH"

# ─── Test 2: show_dialog_fallback ─────────────────────────────────────────────
# Stub osascript: records the script passed via -e into a tmp file.

OSA_RECORD="${TMP_DIR}/osascript_args.txt"
OSA_STUB="${TMP_DIR}/osascript"

cat > "$OSA_STUB" <<STUB
#!/bin/bash
echo "\$@" >> "${OSA_RECORD}"
STUB
chmod +x "$OSA_STUB"

export PATH="${TMP_DIR}:${OLD_PATH}"

show_dialog_fallback "PROJ" "subtitle text" "body text"

export PATH="$OLD_PATH"

OSA_RECORDED="$(cat "${OSA_RECORD}" 2>/dev/null || echo '')"

assert_contains "fallback: contains warning prefix" \
    "Notifications are disabled" "$OSA_RECORDED"
assert_contains "fallback: single OK button" \
    'buttons {"OK"} default button "OK"' "$OSA_RECORDED"
assert_not_contains "fallback: no Snooze button" \
    "Snooze" "$OSA_RECORDED"
assert_not_contains "fallback: no Open button" \
    '"Open"' "$OSA_RECORDED"
assert_not_contains "fallback: no Dismiss button" \
    '"Dismiss"' "$OSA_RECORDED"

# ─── Cleanup ─────────────────────────────────────────────────────────────────

rm -rf "$TMP_DIR"

echo ""
echo "Results: ${pass} passed, ${fail} failed"
[[ "$fail" -eq 0 ]]
