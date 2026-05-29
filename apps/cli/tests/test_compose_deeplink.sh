#!/bin/bash
# Unit tests for compose_deeplink — R-1.9
# Run: bash apps/cli/tests/test_compose_deeplink.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAEMON="${SCRIPT_DIR}/../../../agent-pack/companions/macos-reminders/reminder-daemon.sh"

eval "$(sed -n '/^compose_deeplink()/,/^}$/p' "$DAEMON" 2>/dev/null)" 2>/dev/null || true

pass=0; fail=0

assert_eq() {
    local label="$1" want="$2" got="$3"
    if [[ "$got" == "$want" ]]; then
        printf 'PASS  %s\n' "$label"; (( pass++ )) || true
    else
        printf 'FAIL  %s\n  want: %s\n  got:  %s\n' "$label" "$want" "$got"; (( fail++ )) || true
    fi
}

if ! declare -f compose_deeplink >/dev/null 2>&1; then
    echo "FAIL  compose_deeplink not defined in $DAEMON"
    exit 1
fi

assert_eq "both present, id != project" \
    "squirrel://projects/FOO/BAR" "$(compose_deeplink FOO BAR)"

assert_eq "task == project (dedup)" \
    "squirrel://projects/FOO" "$(compose_deeplink FOO FOO)"

assert_eq "task empty" \
    "squirrel://projects/FOO" "$(compose_deeplink FOO '')"

assert_eq "project empty — legacy fallback to task" \
    "squirrel://projects/BAR" "$(compose_deeplink '' BAR)"

# Action argument — R-8.1 (manual-focus-pick)
assert_eq "action=focus, project only (legacy 2-arg signature with action)" \
    "squirrel://projects/FOO?action=focus" "$(compose_deeplink FOO FOO focus)"

assert_eq "action=focus, project + task" \
    "squirrel://projects/FOO/BAR?action=focus" "$(compose_deeplink FOO BAR focus)"

assert_eq "empty action — no query string appended" \
    "squirrel://projects/FOO" "$(compose_deeplink FOO FOO '')"

echo ""
echo "Results: ${pass} passed, ${fail} failed"
[[ "$fail" -eq 0 ]]
