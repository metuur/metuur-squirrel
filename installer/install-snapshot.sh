#!/usr/bin/env bash
# installer/install-snapshot.sh — capture Squirrel install state for troubleshooting.
#
# Usage:
#   install-snapshot.sh <before|after> <logfile> <installer-id> <version>
#
# Appends one snapshot section to <logfile>: a header (phase, UTC timestamp,
# installer id/version, macOS version) plus per-path metadata for every Squirrel
# footprint path and environment diagnostics. It records metadata only —
# existence, type, size, perms, owner, mtime, and a short sha256 prefix — and
# NEVER the contents of any file, so the launchd token and anything inside
# squirrel.log / config.toml can never leak into the log.
#
# This script must never fail an installation: every probe is fault-tolerant and
# the script always exits 0.
#
# System binaries are addressed absolutely (/usr/bin, /bin) so the output is
# deterministic even when coreutils shadows stat/du/date on the user's PATH or
# when run under the minimal-PATH .pkg root context.

# Deliberately NOT `set -e`: a snapshot must degrade, never abort.
set -u

PHASE="${1:-}"
LOGFILE="${2:-}"
INSTALLER_ID="${3:-unknown}"
VERSION="${4:-unknown}"

# ─── System binaries (absolute, coreutils-proof) ─────────────────────────────
STAT=/usr/bin/stat
SHASUM=/usr/bin/shasum
DU=/usr/bin/du
DATE=/bin/date
FIND=/usr/bin/find

MAX_HASH_BYTES=$((10 * 1024 * 1024))   # skip hashing files larger than 10 MB

now_utc()    { "$DATE" -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "unknown"; }
epoch_utc()  { "$DATE" -u -r "$1" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "unknown"; }

# ─── Footprint path inventory ────────────────────────────────────────────────
# The block between the two SQUIRREL-FOOTPRINT-SYNC markers is the shared
# removable footprint. It is duplicated verbatim in installer/uninstall.sh; an
# automated check (tests/installer/test_footprint_sync.sh) asserts the two copies
# stay identical. Edit BOTH copies together, keeping the markers and order.
footprint_paths() {
  # >>> SQUIRREL-FOOTPRINT-SYNC >>>
  cat <<EOF
/Applications/Squirrel.app
/usr/local/bin/squirrel
/usr/local/bin/squirrel-backend
/usr/local/share/squirrel
$HOME/.local/bin/squirrel
$HOME/.local/bin/squirrel-backend
$HOME/Library/LaunchAgents/org.squirrel.web-ui.plist
$HOME/.squirrel
$HOME/.claude/plugins/squirrel
$HOME/.codex/squirrel
$HOME/.cursor/rules/squirrel
$HOME/.windsurf/rules/squirrel
$HOME/Library/Application Support/com.metuur.squirrel
$HOME/Library/Application Support/com.metuur.squirrel.dev
$HOME/Library/Caches/com.metuur.squirrel
$HOME/Library/Caches/com.metuur.squirrel.dev
$HOME/Library/WebKit/com.metuur.squirrel
$HOME/Library/WebKit/com.metuur.squirrel.dev
$HOME/Library/HTTPStorages/com.metuur.squirrel
$HOME/Library/HTTPStorages/com.metuur.squirrel.dev
$HOME/Library/Preferences/com.metuur.squirrel.plist
$HOME/Library/Preferences/com.metuur.squirrel.dev.plist
$HOME/Library/Saved Application State/com.metuur.squirrel.savedState
$HOME/Library/Saved Application State/com.metuur.squirrel.dev.savedState
EOF
  # <<< SQUIRREL-FOOTPRINT-SYNC <<<
}

# Snapshot-only children of ~/.squirrel: extra per-file metadata for diagnosis.
# These live INSIDE $HOME/.squirrel (already in footprint_paths) so they are not
# separate removal targets — they are inspected here only for troubleshooting
# detail. db and *.log files are never hashed (live files; also see audit H1).
snapshot_detail_paths() {
  cat <<EOF
$HOME/.squirrel/config.toml
$HOME/.squirrel/version
$HOME/.squirrel/launchd-token
$HOME/.squirrel/web-ui.pid
$HOME/.squirrel/state/squirrel.db
$HOME/.squirrel/logs/squirrel.log
$HOME/.squirrel/web-ui.log
EOF
}

# Should this regular file be hashed? No for live db/log files or >10 MB.
should_hash() {
  local path="$1" size="$2"
  case "$path" in
    *.log|*.db|*.db-wal|*.db-shm) return 1 ;;
  esac
  [ "$size" -le "$MAX_HASH_BYTES" ] 2>/dev/null
}

# Emit one metadata line for a path. Never reads file contents (only hashes).
inspect_path() {
  local path="$1" kind meta size owner perms mtime hash entries bytes
  if [ ! -e "$path" ] && [ ! -L "$path" ]; then
    printf '  MISSING            %s\n' "$path"
    return
  fi
  kind="$("$STAT" -f '%HT' "$path" 2>/dev/null || echo '?')"
  perms="$("$STAT" -f '%Sp' "$path" 2>/dev/null || echo '?')"
  owner="$("$STAT" -f '%Su' "$path" 2>/dev/null || echo '?')"
  mtime="$(epoch_utc "$("$STAT" -f '%m' "$path" 2>/dev/null || echo 0)")"
  case "$kind" in
    Directory)
      entries="$("$FIND" "$path" -type f 2>/dev/null | /usr/bin/wc -l | /usr/bin/tr -d ' ')"
      bytes="$(( $("$DU" -sk "$path" 2>/dev/null | /usr/bin/cut -f1 || echo 0) * 1024 ))"
      printf '  DIR    perms=%s owner=%s mtime=%s entries=%s bytes=%s  %s\n' \
        "$perms" "$owner" "$mtime" "${entries:-?}" "${bytes:-?}" "$path"
      ;;
    "Symbolic Link")
      printf '  LINK   perms=%s owner=%s mtime=%s  %s\n' "$perms" "$owner" "$mtime" "$path"
      ;;
    *)
      size="$("$STAT" -f '%z' "$path" 2>/dev/null || echo '?')"
      if should_hash "$path" "$size"; then
        hash="$("$SHASUM" -a 256 "$path" 2>/dev/null | /usr/bin/cut -c1-8 || echo '?')"
      else
        hash="skipped"
      fi
      printf '  FILE   perms=%s owner=%s size=%s mtime=%s sha256=%s  %s\n' \
        "$perms" "$owner" "${size:-?}" "$mtime" "$hash" "$path"
      ;;
  esac
}

# ─── Environment diagnostics ─────────────────────────────────────────────────
LAUNCHCTL=/bin/launchctl
LSOF=/usr/sbin/lsof
CODESIGN=/usr/bin/codesign
XATTR=/usr/bin/xattr
PGREP=/usr/bin/pgrep
PS=/bin/ps
ID=/usr/bin/id

# Binaries whose signing/quarantine state we report.
codesign_targets() {
  cat <<EOF
/Applications/Squirrel.app
/usr/local/bin/squirrel
/usr/local/bin/squirrel-backend
$HOME/.local/bin/squirrel
$HOME/.local/bin/squirrel-backend
EOF
}

# launchd state of org.squirrel.web-ui (the legacy/DMG/manual backend service).
probe_launchd() {
  local uid out state
  [ -x "$LAUNCHCTL" ] || { printf '  launchd org.squirrel.web-ui: unavailable\n'; return; }
  uid="$("$ID" -u 2>/dev/null)" || { printf '  launchd: unavailable\n'; return; }
  out="$("$LAUNCHCTL" print "gui/${uid}/org.squirrel.web-ui" 2>/dev/null)" || {
    printf '  launchd org.squirrel.web-ui: not loaded\n'; return; }
  state="$(printf '%s\n' "$out" | /usr/bin/grep -iE '^[[:space:]]*state[[:space:]]*=' | head -1 | /usr/bin/sed 's/^[[:space:]]*//')"
  printf '  launchd org.squirrel.web-ui: %s\n' "${state:-loaded (state unknown)}"
}

# Who, if anyone, is listening on the backend port.
probe_port() {
  local out pid exe
  out="$("$LSOF" -nP -iTCP:3939 -sTCP:LISTEN 2>/dev/null)" || { printf '  port 3939: unavailable\n'; return; }
  if [ -z "$out" ]; then printf '  port 3939: free\n'; return; fi
  pid="$(printf '%s\n' "$out" | /usr/bin/awk 'NR==2{print $2}')"
  exe="$("$PS" -p "${pid:-0}" -o comm= 2>/dev/null || echo '?')"
  printf '  port 3939: LISTEN pid=%s exe=%s\n' "${pid:-?}" "${exe:-?}"
}

# codesign identity + quarantine xattr for one path.
probe_codesign() {
  local path="$1" auth quar
  if [ ! -e "$path" ]; then printf '  codesign %s: MISSING\n' "$path"; return; fi
  auth="$("$CODESIGN" -dvv "$path" 2>&1 | /usr/bin/grep -E '^(Authority|Identifier)=' | head -2 | /usr/bin/tr '\n' ' ')"
  [ -n "$auth" ] || auth="unsigned-or-unavailable"
  if quar="$("$XATTR" -p com.apple.quarantine "$path" 2>/dev/null)"; then
    quar="quarantined($quar)"
  else
    quar="no-quarantine"
  fi
  printf '  codesign %s: %s| %s\n' "$path" "$auth" "$quar"
}

# Strip any auth token that appears in process argv. The app-managed backend
# receives its per-launch token via `--token <64-hex>` on the command line, so
# `pgrep -fl` would otherwise expose it in the log — defeating the whole
# metadata-only / no-secrets design. Redact before anything reaches the file.
redact_secrets() {
  /usr/bin/sed -E 's/(--token[=[:space:]]+)[0-9A-Fa-f]{16,}/\1REDACTED/g'
}

# Running Squirrel processes (token-redacted).
probe_processes() {
  local app bk
  app="$("$PGREP" -xl Squirrel 2>/dev/null | /usr/bin/tr '\n' ';')"
  bk="$("$PGREP" -fl squirrel-backend 2>/dev/null | /usr/bin/grep -v install-snapshot | /usr/bin/tr '\n' ';')"
  printf '  proc Squirrel: %s\n' "${app:-none}"
  printf '  proc squirrel-backend: %s\n' "${bk:-none}"
}

write_env_section() {
  # Whole section is piped through redact_secrets as a defense-in-depth net so
  # no probe can ever emit a raw token, regardless of which one surfaces it.
  {
    printf '\n[environment]\n'
    probe_launchd
    probe_port
    codesign_targets | while IFS= read -r p; do
      [ -n "$p" ] && probe_codesign "$p"
    done
    printf '  command -v squirrel: %s\n' "$(command -v squirrel 2>/dev/null || echo not-found)"
    printf '  PATH: %s\n' "${PATH:-unavailable}"
    probe_processes
  } | redact_secrets
}

# ─── Retention ───────────────────────────────────────────────────────────────
ensure_log_dir() {
  /bin/mkdir -p "$(/usr/bin/dirname "$LOGFILE")" 2>/dev/null || true
}

# Keep only the 10 newest *.log files in the install-logs dir. /bin/ls (BSD,
# absolute) lists newest-first; everything past the 10th is removed. The current
# run's log is explicitly skipped so a clock skew can never delete it.
prune_logs() {
  local dir f
  dir="$(/usr/bin/dirname "$LOGFILE")"
  [ -d "$dir" ] || return
  /bin/ls -t "$dir"/*.log 2>/dev/null | /usr/bin/tail -n +11 | while IFS= read -r f; do
    [ "$f" = "$LOGFILE" ] && continue
    /bin/rm -f "$f" 2>/dev/null || true
  done
}

# ─── Main ────────────────────────────────────────────────────────────────────
main() {
  case "$PHASE" in
    before|after) ;;
    *) printf 'usage: install-snapshot.sh <before|after> <logfile> <installer-id> <version>\n' >&2
       exit 0 ;;
  esac
  [ -n "$LOGFILE" ] || { printf 'install-snapshot: no logfile given\n' >&2; exit 0; }

  ensure_log_dir

  {
    printf '\n'
    printf '════════════════════════════════════════════════════════════════════\n'
    printf 'SNAPSHOT  phase=%s  ts=%s\n' "$PHASE" "$(now_utc)"
    printf 'installer=%s  version=%s  macos=%s\n' \
      "$INSTALLER_ID" "$VERSION" "$(/usr/bin/sw_vers -productVersion 2>/dev/null || echo unknown)"
    printf '════════════════════════════════════════════════════════════════════\n'

    printf '\n[footprint]\n'
    footprint_paths | while IFS= read -r p; do
      [ -n "$p" ] && inspect_path "$p"
    done

    printf '\n[squirrel-home detail]\n'
    snapshot_detail_paths | while IFS= read -r p; do
      [ -n "$p" ] && inspect_path "$p"
    done

    write_env_section
  } >>"$LOGFILE" 2>/dev/null

  # Retention runs after the AFTER snapshot is fully written, so the current
  # run's log already exists and counts toward (and survives) the keep-10 set.
  [ "$PHASE" = "after" ] && prune_logs

  exit 0
}

main
