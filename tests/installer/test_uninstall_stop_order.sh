#!/usr/bin/env bash
# tests/installer/test_uninstall_stop_order.sh
#
# Locks the load-bearing stop ordering in uninstall.sh (R-4.1): the launchd
# service must be booted out BEFORE the backend is killed, or KeepAlive respawns
# the process we just killed (the "Backend offline" loop). The script is sourced
# and its external ops are mocked, so no live app or service is touched.

set -uo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$THIS_DIR/../.." && pwd)"
UNINST="$REPO_ROOT/installer/uninstall.sh"

# shellcheck disable=SC1090
source "$UNINST" >/dev/null 2>&1

CALLS=()
stop_app()               { CALLS+=("app"); }
retire_launchd_service() { CALLS+=("bootout"); }
kill_backend()           { CALLS+=("kill"); }
port_3939_listener()     { CALLS+=("portcheck"); return 1; }   # report port free
hdr() { :; }; info() { :; }; ok() { :; }; warn() { :; }

stop_squirrel

PASS=0; FAIL=0
order="${CALLS[*]}"
if [[ "$order" == "app bootout kill portcheck" ]]; then
  printf '  ✓ stop order is app→bootout→kill→portcheck\n'; PASS=$((PASS+1))
else
  printf '  ✗ unexpected stop order: %s\n' "$order"; FAIL=$((FAIL+1))
fi

bi=-1; ki=-1
for i in "${!CALLS[@]}"; do
  [[ "${CALLS[$i]}" == bootout ]] && bi=$i
  [[ "${CALLS[$i]}" == kill ]] && ki=$i
done
if [[ $bi -ge 0 && $ki -ge 0 && $bi -lt $ki ]]; then
  printf '  ✓ bootout (#%d) precedes kill_backend (#%d) — KeepAlive-safe\n' "$bi" "$ki"; PASS=$((PASS+1))
else
  printf '  ✗ bootout must precede kill_backend (bootout=#%d kill=#%d)\n' "$bi" "$ki"; FAIL=$((FAIL+1))
fi

echo "  ── $PASS passed, $FAIL failed ──"
[[ $FAIL -eq 0 ]]
