#!/bin/bash
# squirrel macOS Reminder Daemon
#
# Polls deadline_scanner.py for critical/urgent items and shows osascript
# dialogs during the configured workday window.
#
# Called by launchd via plist.template (StartInterval = cadence).
# State: $VAULT_PATH/.squirrel/reminders-state.json
#
# Usage (called by launchd):
#   reminder-daemon.sh
#
# Usage (manual test):
#   reminder-daemon.sh --force   (bypass workday window check)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORCE_MODE=false
[[ "${1:-}" == "--force" ]] && FORCE_MODE=true

# ─── Config ──────────────────────────────────────────────────────────────────

CONFIG_FILE="${HOME}/.squirrel/config.toml"
LOG_FILE="${HOME}/.squirrel/reminders-daemon.log"
MAX_LOG_LINES=500

# Defaults (overridable via config.toml [reminders] section)
WORKDAY_START="09:00"
WORKDAY_END="18:00"
CADENCE_MINUTES=120
MAX_DIALOGS_PER_DAY=8
# Workdays: 1=Mon ... 7=Sun (isoweekday)
WORKDAYS="1 2 3 4 5"

# ─── Helpers ─────────────────────────────────────────────────────────────────

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE" 2>/dev/null || true
    # Rotate
    if command -v wc >/dev/null 2>&1; then
        local lines
        lines=$(wc -l < "$LOG_FILE" 2>/dev/null || echo 0)
        if [ "$lines" -gt "$MAX_LOG_LINES" ]; then
            tail -n $((MAX_LOG_LINES / 2)) "$LOG_FILE" > "${LOG_FILE}.tmp" \
                && mv "${LOG_FILE}.tmp" "$LOG_FILE"
        fi
    fi
}

die() { log "ERROR: $*"; exit 1; }

# Compose a squirrel:// deep-link URL for an item (R-1.9).
# Args: project task
# Both may be empty strings; task may equal project.
compose_deeplink() {
    local project="${1:-}" task="${2:-}"
    if [ -z "$project" ] && [ -n "$task" ]; then
        echo "squirrel://projects/${task}"
    elif [ -z "$task" ] || [ "$task" = "$project" ]; then
        echo "squirrel://projects/${project}"
    else
        echo "squirrel://projects/${project}/${task}"
    fi
}

# Read a value from config.toml (simple key = "value" in any section)
read_config() {
    local key="$1" default="${2:-}"
    local val
    val=$(grep -E "^\s*${key}\s*=" "$CONFIG_FILE" 2>/dev/null \
        | head -1 | sed 's/.*=\s*//' | tr -d '"' | tr -d "'" | xargs) || true
    echo "${val:-$default}"
}

# ─── Read config ─────────────────────────────────────────────────────────────

if [ ! -f "$CONFIG_FILE" ]; then
    log "Config file not found: $CONFIG_FILE — exiting."
    exit 0
fi

VAULT_PATH=$(read_config "vault_path" "")
if [ -z "$VAULT_PATH" ]; then
    # Multi-vault schema: pick the [[vaults]] entry where default = true,
    # falling back to the first vault listed.
    VAULT_PATH=$(python3 - "$CONFIG_FILE" <<'PYEOF' 2>/dev/null
import sys, tomllib
try:
    with open(sys.argv[1], "rb") as f:
        cfg = tomllib.load(f)
    vaults = cfg.get("vaults", [])
    chosen = next((v for v in vaults if v.get("default")), vaults[0] if vaults else None)
    if chosen and chosen.get("path"):
        print(chosen["path"])
except Exception:
    pass
PYEOF
)
fi
[ -z "$VAULT_PATH" ] && die "vault_path not set in config.toml"
VAULT_PATH="${VAULT_PATH/#\~/$HOME}"

WORKDAY_START=$(read_config "workday_start" "$WORKDAY_START")
WORKDAY_END=$(read_config "workday_end" "$WORKDAY_END")
CADENCE_MINUTES=$(read_config "cadence_minutes" "$CADENCE_MINUTES")
MAX_DIALOGS_PER_DAY=$(read_config "max_dialogs_per_day" "$MAX_DIALOGS_PER_DAY")

STATE_FILE="${VAULT_PATH}/.squirrel/reminders-state.json"
mkdir -p "${VAULT_PATH}/.squirrel"

# ─── Locate deadline_scanner.py ──────────────────────────────────────────────

SCANNER=""
for candidate in \
    "${HOME}/.claude/plugins/squirrel/lib/deadline_scanner.py" \
    "$(find "${HOME}/.claude" -name deadline_scanner.py -path "*/squirrel/*" 2>/dev/null | head -1)" \
    "$(find "${HOME}/others" -name deadline_scanner.py -path "*/squirrel/*" 2>/dev/null | head -1)"; do
    [ -f "$candidate" ] && SCANNER="$candidate" && break
done

if [ -z "$SCANNER" ]; then
    log "deadline_scanner.py not found — skipping."
    exit 0
fi

# ─── Workday window check ────────────────────────────────────────────────────

is_within_workday() {
    local now_iso now_dow now_h now_m now_total start_total end_total
    now_h=$(date '+%H')
    now_m=$(date '+%M')
    now_dow=$(date '+%u')  # 1=Mon … 7=Sun (ISO 8601 weekday)
    now_total=$(( 10#$now_h * 60 + 10#$now_m ))

    local start_h start_m end_h end_m
    start_h=$(echo "$WORKDAY_START" | cut -d: -f1)
    start_m=$(echo "$WORKDAY_START" | cut -d: -f2)
    end_h=$(echo "$WORKDAY_END" | cut -d: -f1)
    end_m=$(echo "$WORKDAY_END" | cut -d: -f2)
    start_total=$(( 10#$start_h * 60 + 10#$start_m ))
    end_total=$(( 10#$end_h * 60 + 10#$end_m ))

    # Check workday
    echo "$WORKDAYS" | grep -wq "$now_dow" || return 1

    [ "$now_total" -ge "$start_total" ] && [ "$now_total" -lt "$end_total" ]
}

# ─── State read/write (via Python for JSON safety) ───────────────────────────

read_state() {
    python3 - "$STATE_FILE" <<'PYEOF'
import json, sys, pathlib
f = pathlib.Path(sys.argv[1])
if f.exists():
    try:
        print(f.read_text())
    except Exception:
        print("{}")
else:
    print("{}")
PYEOF
}

write_state() {
    local json_str="$1"
    python3 - "$STATE_FILE" "$json_str" <<'PYEOF'
import json, sys, pathlib
path = pathlib.Path(sys.argv[1])
data = json.loads(sys.argv[2])
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(data, indent=2) + "\n")
PYEOF
}

# ─── Dialog cap and cadence check ────────────────────────────────────────────

is_due() {
    local state_json="$1"
    python3 - "$state_json" "$CADENCE_MINUTES" "$MAX_DIALOGS_PER_DAY" <<'PYEOF'
import json, sys, datetime
state = json.loads(sys.argv[1])
cadence = int(sys.argv[2])
max_dialogs = int(sys.argv[3])
now = datetime.datetime.now()

# Snooze check
snoozed = state.get("snoozed_until")
if snoozed:
    try:
        if now < datetime.datetime.fromisoformat(snoozed):
            sys.exit(1)  # snoozed
    except Exception:
        pass

# Cadence check
last_shown = state.get("last_shown")
if last_shown:
    try:
        elapsed = (now - datetime.datetime.fromisoformat(last_shown)).total_seconds() / 60
        if elapsed < cadence:
            sys.exit(1)
    except Exception:
        pass

# Daily dialog cap
today = now.strftime("%Y-%m-%d")
dialogs_date = state.get("dialogs_date")
dialogs_today = state.get("dialogs_today", 0) if dialogs_date == today else 0
if dialogs_today >= max_dialogs:
    sys.exit(1)

sys.exit(0)
PYEOF
}

update_state_after_dialog() {
    local state_json="$1" choice="$2" snooze_minutes="${3:-60}"
    python3 - "$state_json" "$choice" "$snooze_minutes" <<'PYEOF'
import json, sys, datetime
state = json.loads(sys.argv[1])
choice = sys.argv[2]
snooze_min = int(sys.argv[3])
now = datetime.datetime.now()

state["last_shown"] = now.isoformat()
today = now.strftime("%Y-%m-%d")
if state.get("dialogs_date") == today:
    state["dialogs_today"] = state.get("dialogs_today", 0) + 1
else:
    state["dialogs_date"] = today
    state["dialogs_today"] = 1

if choice == "Snooze":
    state["snoozed_until"] = (now + datetime.timedelta(minutes=snooze_min)).isoformat()
elif choice in ("Open", "Dismiss"):
    state.pop("snoozed_until", None)

print(json.dumps(state))
PYEOF
}

# ─── Show notification ────────────────────────────────────────────────────────

# Emit a macOS Notification Center banner. Non-blocking; stacks in the
# Notification Center so multiple items can be reviewed later. Requires
# Script Editor to have notification permission (System Settings →
# Notifications → Script Editor → Allow notifications). If permission is
# denied, the call silently no-ops.
show_notification() {
    local ntitle="$1" subtitle="$2" body="$3"
    local esc_t esc_s esc_b
    esc_t=$(printf '%s' "$ntitle"   | python3 -c 'import sys; print(sys.stdin.read().replace("\\","\\\\").replace("\"","\\\""), end="")')
    esc_s=$(printf '%s' "$subtitle" | python3 -c 'import sys; print(sys.stdin.read().replace("\\","\\\\").replace("\"","\\\""), end="")')
    esc_b=$(printf '%s' "$body"     | python3 -c 'import sys; print(sys.stdin.read().replace("\\","\\\\").replace("\"","\\\""), end="")')

    osascript -e "display notification \"${esc_b}\" with title \"${esc_t}\" subtitle \"${esc_s}\" sound name \"Submarine\"" 2>/dev/null || true
}

# Open the project's page in the web UI. Uses macOS `open` so the user's
# default browser handles it. Silent failure (e.g., backend offline) is fine —
# the dialog choice is already recorded in state above.
open_in_web_ui() {
    local project="$1"
    [ -z "$project" ] && return 0
    open "http://localhost:3939/projects/${project}" 2>/dev/null || true
}

# ─── Main ────────────────────────────────────────────────────────────────────

main() {
    log "Daemon run started (force=${FORCE_MODE})"

    # Workday check
    if [ "$FORCE_MODE" = "false" ] && ! is_within_workday; then
        log "Outside workday window — skipping."
        exit 0
    fi

    # State and cadence check
    STATE_JSON=$(read_state)
    if [ "$FORCE_MODE" = "false" ] && ! is_due "$STATE_JSON"; then
        log "Not due yet (snooze or cadence or cap) — skipping."
        exit 0
    fi

    # Scan deadlines
    SCAN_OUTPUT=$(python3 "$SCANNER" --vault "$VAULT_PATH" --level "critical,urgent" --pretty 2>&1)
    if [ $? -ne 0 ]; then
        log "deadline_scanner error: $SCAN_OUTPUT"
        exit 0
    fi

    ITEM_COUNT=$(echo "$SCAN_OUTPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); by=d.get('by_urgency',{}); print(len(by.get('critical',[]))+len(by.get('urgent',[])))" 2>/dev/null || echo 0)
    if [ "$ITEM_COUNT" -eq 0 ]; then
        log "No critical/urgent items — skipping."
        exit 0
    fi

    log "Found $ITEM_COUNT critical/urgent item(s). Showing up to 3 dialogs."

    # Build rich, multi-line messages for up to 3 critical/urgent items.
    # Output format: PROJECT<US>MSG<RS> where US=\x1f, RS=\x1e — robust against
    # arbitrary text (including pipes and newlines) inside titles or next-action.
    RECORDS=$(echo "$SCAN_OUTPUT" | python3 - <<'PYEOF' 2>/dev/null
import json, sys

d = json.load(sys.stdin)
by = d.get("by_urgency", {})
items = (by.get("critical", []) + by.get("urgent", []))[:3]

def truncate(s, n):
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"

def due_line(it):
    if it.get("is_overdue"):
        n = it.get("days_overdue", 0)
        return f"⚠️  Overdue {n}d (was {it.get('deadline','?')})"
    h = it.get("hours_left")
    if h is not None:
        return f"⚠️  Due in {round(h)}h — today ({it.get('deadline','?')})"
    dl = it.get("days_left")
    if dl == 1:
        return f"Due tomorrow ({it.get('deadline','?')})"
    if dl is not None:
        return f"Due in {dl} days ({it.get('deadline','?')})"
    return f"Deadline: {it.get('deadline','?')}"

for it in items:
    proj = it.get("id", "") or ""
    lines = [truncate(it.get("title"), 80), "", due_line(it)]
    na = it.get("next_action")
    if na:
        lines.append(f"→ {truncate(na, 110)}")
    last = it.get("last_shutdown")
    if last:
        lines.append(f"Last worked: {last[:10]}")
    sys.stdout.write(f"{proj}\x1f" + "\n".join(lines) + "\x1e")
PYEOF
)

    # Show up to 3 dialogs per run (cap per-run storm).
    printf '%s' "$RECORDS" | while IFS= read -r -d $'\x1e' record; do
        [ -z "$record" ] && continue
        project="${record%%$'\x1f'*}"
        msg="${record#*$'\x1f'}"
        [ -z "$project" ] && continue

        choice=$(show_dialog "$project" "$msg")
        choice=${choice:-Dismiss}
        log "Dialog shown for '${project}': choice='${choice}'"

        [ "$choice" = "Open" ] && open_in_web_ui "$project"

        NEW_STATE=$(update_state_after_dialog "$STATE_JSON" "$choice")
        write_state "$NEW_STATE"
        STATE_JSON="$NEW_STATE"
    done

    log "Daemon run complete."
}

main
