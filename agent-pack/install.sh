#!/usr/bin/env bash
#
# install.sh — Squirrel interactive installer (top-level TUI).
#
# Keyboard navigation:
#   ↑/↓        move cursor
#   space      toggle selection (multi-select screens)
#   enter      confirm / next screen
#   b or ←     previous screen
#   q or Esc   quit
#
# Usage:
#   ./install.sh                # interactive TUI
#   ./install.sh --dry-run      # interactive, but preview only (no writes)
#   ./install.sh --help         # this help
#   ./install.sh --auto         # non-interactive: install for all detected agents
#                                 with defaults; pass --yes too if you want the
#                                 macOS daemon installed silently.
#   ./install.sh --with-web-ui  # also install the local browser companion
#                                 (default = NO in interactive mode; default = NO
#                                 in --auto unless this flag is passed).
#   ./install.sh --with-menubar # also install the macOS menu bar companion
#                                 (SwiftBar plugin; implies --with-web-ui).
#   ./install.sh --no-plugin    # install Claude Code natively (skills/commands/
#                                 hooks) instead of as a plugin — for orgs that
#                                 block plugin installs. Affects Claude only.
#
# Other flags (mirror the per-agent installers):
#   --no-config / --no-cli / --no-reminders / --link / --prefix=PATH / --yes
#
# For per-agent scripted installs (no TUI), use:
#   ./scripts/install-claude.sh / install-codex.sh / install-cursor.sh /
#   install-standalone.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/_lib.sh
source "$ROOT/scripts/_lib.sh"

# ─── Help ────────────────────────────────────────────────────────────────────
print_help_and_exit() {
  awk 'NR>1 && /^#/ {sub(/^# ?/,""); print; next} NR>1 {exit}' "${BASH_SOURCE[0]}"
  exit 0
}

# ─── State ───────────────────────────────────────────────────────────────────
AUTO_MODE=0
WANT_CLAUDE=0
WANT_CODEX=0
WANT_CURSOR=0
WANT_STANDALONE=0
WANT_WEB_UI=0   # opt-in: --with-web-ui (interactive default is No — R-11.1)
WANT_MENUBAR=0  # opt-in: --with-menubar (macOS only; implies WANT_WEB_UI)
NO_PLUGIN=0     # opt-in: --no-plugin (Claude Code native install, no marketplace)
HAS_CLAUDE=0
HAS_CODEX=0
HAS_CURSOR=0
PROCEED=0   # set by the summary screen

# ─── Argument parsing ────────────────────────────────────────────────────────
RAW_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --auto)              AUTO_MODE=1 ;;
    --with-web-ui)       WANT_WEB_UI=1 ;;
    --with-menubar)      WANT_MENUBAR=1; WANT_WEB_UI=1 ;;
    --no-plugin|--manual) NO_PLUGIN=1 ;;
    -h|--help)           print_help_and_exit ;;
    *)              RAW_ARGS+=("$arg") ;;
  esac
done
parse_common_args "${RAW_ARGS[@]+"${RAW_ARGS[@]}"}"
[[ ${#LEFTOVER_ARGS[@]} -eq 0 ]] || die "Unknown argument(s): ${LEFTOVER_ARGS[*]} (try --help)"

# ─── Terminal control codes (only when stdout is a TTY) ──────────────────────
if [[ -t 1 ]]; then
  TERM_CLEAR=$'\033[2J\033[H'
  TERM_HIDE_CURSOR=$'\033[?25l'
  TERM_SHOW_CURSOR=$'\033[?25h'
  TERM_DIM=$'\033[2m'
else
  TERM_CLEAR=''
  TERM_HIDE_CURSOR=''
  TERM_SHOW_CURSOR=''
  TERM_DIM=''
fi

cleanup_term() { printf '%s' "$TERM_SHOW_CURSOR"; }
trap cleanup_term EXIT INT TERM

# ─── Banner ──────────────────────────────────────────────────────────────────
banner() {
  printf '%s' "$C_BOLD"
  cat <<'EOF'

  ╔══════════════════════════════════════════════════════════════╗
  ║                                                              ║
  ║       🐿   Squirrel  —  Interactive Installer                ║
  ║                                                              ║
  ║       Focus-friendly context management for AI agents        ║
  ║                                                              ║
  ╚══════════════════════════════════════════════════════════════╝

EOF
  printf '%s' "$C_RESET"
}

# ─── Detect installed AI agents ──────────────────────────────────────────────
detect_agents() {
  [[ -d "$HOME/.claude" ]] && HAS_CLAUDE=1
  [[ -d "$HOME/.codex"  ]] && HAS_CODEX=1
  [[ -d "$HOME/.cursor" ]] && HAS_CURSOR=1
  return 0   # detection never fails the install (set -e safe)
}

# ─── Key reader ──────────────────────────────────────────────────────────────
# Returns one of: UP DOWN LEFT RIGHT SPACE ENTER ESC BACK QUIT CHAR:<c>
read_key() {
  local key rest
  IFS= read -rsn1 key 2>/dev/null || { echo "QUIT"; return; }
  case "$key" in
    "")        echo "ENTER" ;;
    " ")       echo "SPACE" ;;
    q|Q)       echo "QUIT" ;;
    b|B|h|H)   echo "BACK" ;;
    j|J)       echo "DOWN" ;;
    k|K)       echo "UP" ;;
    $'\033')
      # Escape sequence — read up to 2 more chars.
      # Use integer timeout for bash 3.2 (macOS default) compatibility.
      # Bare ESC will take 1s to register as quit; q is the recommended quit key.
      IFS= read -rsn2 -t 1 rest 2>/dev/null || rest=""
      case "$rest" in
        "[A") echo "UP" ;;
        "[B") echo "DOWN" ;;
        "[C") echo "RIGHT" ;;
        "[D") echo "LEFT" ;;
        "")   echo "ESC" ;;
        *)    echo "CHAR:$key$rest" ;;
      esac
      ;;
    *) echo "CHAR:$key" ;;
  esac
}

# ─── Render helpers ──────────────────────────────────────────────────────────
clear_screen() { printf '%s' "$TERM_CLEAR"; }

render_header() {
  local step_num="$1" step_total="$2" title="$3"
  clear_screen
  banner
  printf '%s── Step %s/%s — %s ──%s\n\n' "$C_BOLD" "$step_num" "$step_total" "$title" "$C_RESET"
}

render_footer() {
  local show_space="${1:-0}"
  printf '\n%s  ' "$TERM_DIM"
  (( show_space )) && printf "${C_RESET}${C_BOLD}SPACE${C_RESET}${TERM_DIM} toggle  ·  "
  printf "${C_RESET}${C_BOLD}↑/↓${C_RESET}${TERM_DIM} move  ·  ${C_RESET}${C_BOLD}ENTER${C_RESET}${TERM_DIM} continue  ·  ${C_RESET}${C_BOLD}b${C_RESET}${TERM_DIM} back  ·  ${C_RESET}${C_BOLD}q${C_RESET}${TERM_DIM} quit${C_RESET}\n"
}

# ─── Multi-select menu ───────────────────────────────────────────────────────
# Args: title, then alternating label/initial_state pairs.
# Sets MULTI_RESULT (array of 0/1) on ENTER.
# Returns: 0 = next, 1 = back, 2 = quit
multi_select() {
  local title="$1"; shift
  local labels=() states=()
  while (( $# >= 2 )); do
    labels+=("$1"); states+=("$2"); shift 2
  done
  local n=${#labels[@]} cursor=0 key

  printf '%s' "$TERM_HIDE_CURSOR"
  while true; do
    render_header "$SCREEN_NUM" "$SCREEN_TOTAL" "$title"
    say "  Pick one or more options. Press SPACE to toggle."
    say ""
    local i
    for (( i = 0; i < n; i++ )); do
      local mark=' '
      (( ${states[i]} )) && mark="${C_GREEN}✓${C_RESET}"
      if (( i == cursor )); then
        printf '  %s▶%s [%s] %s%s%s\n' "$C_BOLD" "$C_RESET" "$mark" "$C_BOLD" "${labels[i]}" "$C_RESET"
      else
        printf '    [%s] %s\n' "$mark" "${labels[i]}"
      fi
    done
    render_footer 1
    key=$(read_key)
    case "$key" in
      UP)    (( cursor = (cursor - 1 + n) % n )) ;;
      DOWN)  (( cursor = (cursor + 1) % n )) ;;
      SPACE) states[cursor]=$((1 - states[cursor])) ;;
      ENTER)
        # Validate: at least one must be selected
        local any=0 j
        for (( j = 0; j < n; j++ )); do (( states[j] )) && any=1; done
        if (( any )); then
          MULTI_RESULT=("${states[@]}")
          printf '%s' "$TERM_SHOW_CURSOR"
          return 0
        fi
        # Briefly flash a warning at the bottom
        printf '\n  %s⚠  Select at least one option.%s' "$C_YELLOW" "$C_RESET"
        sleep 0.8
        ;;
      BACK|LEFT) printf '%s' "$TERM_SHOW_CURSOR"; return 1 ;;
      QUIT|ESC)  printf '%s' "$TERM_SHOW_CURSOR"; return 2 ;;
    esac
  done
}

# ─── Single-select menu ──────────────────────────────────────────────────────
# Args: title, default_index, then labels.
# Sets SINGLE_RESULT (index of chosen) on ENTER.
# Returns: 0 = next, 1 = back, 2 = quit
single_select() {
  local title="$1" default_index="$2"; shift 2
  local labels=("$@") n=$# cursor=$default_index key

  printf '%s' "$TERM_HIDE_CURSOR"
  while true; do
    render_header "$SCREEN_NUM" "$SCREEN_TOTAL" "$title"
    if [[ -n "${SCREEN_DESC:-}" ]]; then
      say "  $SCREEN_DESC"
      say ""
    fi
    local i
    for (( i = 0; i < n; i++ )); do
      if (( i == cursor )); then
        printf '  %s▶%s %s%s%s\n' "$C_BOLD" "$C_RESET" "$C_BOLD" "${labels[i]}" "$C_RESET"
      else
        printf '    %s\n' "${labels[i]}"
      fi
    done
    render_footer 0
    key=$(read_key)
    case "$key" in
      UP)    (( cursor = (cursor - 1 + n) % n )) ;;
      DOWN)  (( cursor = (cursor + 1) % n )) ;;
      ENTER) SINGLE_RESULT=$cursor; printf '%s' "$TERM_SHOW_CURSOR"; return 0 ;;
      BACK|LEFT) printf '%s' "$TERM_SHOW_CURSOR"; return 1 ;;
      QUIT|ESC)  printf '%s' "$TERM_SHOW_CURSOR"; return 2 ;;
    esac
  done
}

# ─── Screen functions (each returns 0=next, 1=back, 2=quit) ──────────────────

screen_agents() {
  SCREEN_NUM=1
  # Pre-fill defaults the first time this screen renders
  if (( ! AGENTS_INITIALIZED )); then
    WANT_CLAUDE=$HAS_CLAUDE
    WANT_CODEX=$HAS_CODEX
    WANT_CURSOR=$HAS_CURSOR
    WANT_STANDALONE=0
    if (( ! WANT_CLAUDE && ! WANT_CODEX && ! WANT_CURSOR )); then
      WANT_CLAUDE=1
    fi
    AGENTS_INITIALIZED=1
  fi
  local label_claude="Claude Code"
  local label_codex="Codex CLI"
  local label_cursor="Cursor"
  (( HAS_CLAUDE )) || label_claude+="    ${TERM_DIM}(not detected — will still install)${C_RESET}"
  (( HAS_CODEX ))  || label_codex+="    ${TERM_DIM}(not detected — will still install)${C_RESET}"
  (( HAS_CURSOR )) || label_cursor+="    ${TERM_DIM}(not detected — will still install)${C_RESET}"
  multi_select "Which agents do you want to install Squirrel for?" \
    "$label_claude" "$WANT_CLAUDE" \
    "$label_codex"  "$WANT_CODEX" \
    "$label_cursor" "$WANT_CURSOR" \
    "Standalone CLI only (no AI agent)" "$WANT_STANDALONE"
  local rc=$?
  if (( rc == 0 )); then
    WANT_CLAUDE=${MULTI_RESULT[0]}
    WANT_CODEX=${MULTI_RESULT[1]}
    WANT_CURSOR=${MULTI_RESULT[2]}
    WANT_STANDALONE=${MULTI_RESULT[3]}
  fi
  return $rc
}

screen_method() {
  SCREEN_NUM=2
  SCREEN_DESC="How should the files be installed on disk?"
  single_select "Install method" "$USE_LINK" \
    "Copy   — stable, won't change if you edit the repo (recommended)" \
    "Symlink — auto-updates from repo on git pull (best for developers)"
  local rc=$?
  if (( rc == 0 )); then
    USE_LINK=$SINGLE_RESULT
    # Reset EXTRA_ARGS and add --link if needed
    local new_args=()
    local a
    for a in "${EXTRA_ARGS[@]:-}"; do
      [[ -n "$a" && "$a" != "--link" ]] && new_args+=("$a")
    done
    (( USE_LINK )) && new_args+=("--link")
    EXTRA_ARGS=("${new_args[@]}")
  fi
  return $rc
}

screen_cli() {
  SCREEN_NUM=3
  SCREEN_DESC="The 'squirrel' CLI lets you run 'squirrel status', 'squirrel deadlines', etc. from any terminal — symlinked into $CLI_PREFIX/squirrel."
  local default=$(( SKIP_CLI ? 1 : 0 ))
  single_select "Install the 'squirrel' CLI on your PATH?" "$default" \
    "Yes — install CLI symlink at $CLI_PREFIX/squirrel" \
    "No  — skip the CLI symlink"
  local rc=$?
  (( rc == 0 )) && SKIP_CLI=$SINGLE_RESULT
  return $rc
}

screen_config() {
  SCREEN_NUM=4
  SCREEN_DESC="Seeds ~/.squirrel/config.toml from the template. Existing config is preserved — only fills it in if missing."
  local default=$(( SKIP_CONFIG ? 1 : 0 ))
  single_select "Create config file?" "$default" \
    "Yes — seed ~/.squirrel/config.toml from template" \
    "No  — skip (you'll create it manually later)"
  local rc=$?
  (( rc == 0 )) && SKIP_CONFIG=$SINGLE_RESULT
  return $rc
}

screen_daemon() {
  SCREEN_NUM=5
  if [[ "$(uname)" != "Darwin" ]]; then
    SKIP_REMINDERS=1
    SCREEN_DESC="The reminder daemon is macOS-only (launchd). On your platform it's automatically skipped."
    single_select "macOS reminder daemon" 0 \
      "Continue (nothing to install on this platform)"
    return $?
  fi
  SCREEN_DESC="Polls your vault every 2 hours during your workday window and notifies about critical deadlines. Installs a LaunchAgent."
  local default=$(( SKIP_REMINDERS ? 1 : 0 ))
  single_select "Install macOS reminder daemon (launchd)?" "$default" \
    "Yes — install and start the launchd daemon" \
    "No  — skip the daemon"
  local rc=$?
  if (( rc == 0 )); then
    SKIP_REMINDERS=$SINGLE_RESULT
    (( SKIP_REMINDERS )) || ASSUME_YES=1
  fi
  return $rc
}

screen_summary() {
  SCREEN_NUM=6
  SCREEN_DESC=""
  clear_screen
  banner
  printf '%s── Step %s/%s — Summary ──%s\n\n' "$C_BOLD" "$SCREEN_NUM" "$SCREEN_TOTAL" "$C_RESET"
  printf '  Agents:           %s\n' "$(list_agents)"
  printf '  Method:           %s\n' "$( ((USE_LINK)) && echo 'symlink (auto-update)' || echo 'copy' )"
  printf '  CLI on PATH:      %s\n' "$( ((SKIP_CLI)) && echo 'no' || echo "yes → $CLI_PREFIX/squirrel" )"
  printf '  Config seed:      %s\n' "$( ((SKIP_CONFIG)) && echo 'no' || echo 'yes → ~/.squirrel/config.toml' )"
  if [[ "$(uname)" == "Darwin" ]]; then
    printf '  macOS daemon:     %s\n' "$( ((SKIP_REMINDERS)) && echo 'no' || echo 'yes (launchd)' )"
    printf '  Menu bar:         %s\n' "$( ((WANT_MENUBAR)) && echo 'yes (SwiftBar plugin)' || echo "${TERM_DIM}prompt after summary${C_RESET}" )"
  else
    printf '  macOS daemon:     %sn/a (not macOS)%s\n' "$TERM_DIM" "$C_RESET"
  fi
  printf '  Dry run:          %s\n' "$( ((DRY_RUN)) && echo "${C_YELLOW}YES — no writes will happen${C_RESET}" || echo 'no' )"
  printf '\n'
  single_select "Proceed?" 0 \
    "Yes — install now" \
    "No  — go back and change something"
  local rc=$?
  if (( rc == 0 )); then
    if (( SINGLE_RESULT == 0 )); then
      PROCEED=1
      return 0
    else
      return 1
    fi
  fi
  return $rc
}

# ─── Screen navigation ───────────────────────────────────────────────────────
# Total visible screens
SCREEN_TOTAL=6
AGENTS_INITIALIZED=0

run_tui() {
  local screens=(screen_agents screen_method screen_cli screen_config screen_daemon screen_summary)
  local idx=0
  local total=${#screens[@]}
  while (( idx >= 0 && idx < total )); do
    "${screens[$idx]}"
    case $? in
      0) ((idx++)) ;;
      1) if (( idx > 0 )); then ((idx--)); fi ;;
      2) clear_screen; warn "Aborted by user."; exit 1 ;;
    esac
  done
  (( PROCEED )) || { warn "Aborted."; exit 1; }
}

# ─── Helpers used in summary ─────────────────────────────────────────────────
list_agents() {
  local out=()
  (( WANT_CLAUDE ))     && out+=("Claude Code")
  (( WANT_CODEX ))      && out+=("Codex CLI")
  (( WANT_CURSOR ))     && out+=("Cursor")
  (( WANT_STANDALONE )) && out+=("Standalone")
  ( IFS=', '; echo "${out[*]}" )
}

# ─── Execute the install (delegates to _lib.sh helpers) ──────────────────────
do_install() {
  if [[ -t 1 ]]; then
    clear_screen
    banner
  fi
  hdr "Installing"
  if (( NO_PLUGIN )); then
    # Native, no-marketplace install for Claude Code (skills/commands/hooks/lib/
    # config/CLI). install-claude-manual.sh handles config + CLI itself, so we
    # skip install_post_steps below for the Claude target.
    hdr "Claude Code — manual (no-plugin) install"
    local margs=()
    (( DRY_RUN ))     && margs+=(--dry-run)
    (( SKIP_CONFIG )) && margs+=(--no-config)
    (( SKIP_CLI ))    && margs+=(--no-cli)
    (( ASSUME_YES ))  && margs+=(--yes)
    margs+=(--prefix="$CLI_PREFIX")
    bash "$ROOT/scripts/install-claude-manual.sh" "${margs[@]}"
  else
    install_canonical "$ROOT"
  fi
  (( WANT_CODEX ))  && install_agent_integration "$ROOT" "codex"
  (( WANT_CURSOR )) && install_agent_integration "$ROOT" "cursor"
  (( NO_PLUGIN ))   || install_post_steps "$ROOT"
  if (( WANT_WEB_UI )); then
    hdr "Web UI (browser interface)"
    bash "$ROOT/scripts/install-web-ui.sh" || true
  fi
  if (( WANT_MENUBAR )); then
    hdr "Menu bar companion (native macOS app)"
    make -C "$ROOT/companions/menubar-app" install || true
  fi
}

# ─── Final report ────────────────────────────────────────────────────────────
show_done() {
  hdr "All done"
  say ""
  say "Installed for:    $(list_agents)"
  say ""
  say "Next steps:"
  if (( WANT_CLAUDE )); then
    say ""
    say "  Claude Code:"
    say "    1. Close ALL Claude Code windows, then reopen."
    say "    2. /plugin list           # confirm 'squirrel v0.7.0' appears"
    say "    3. /sq-init               # configure your vault"
    say "    4. /sq-where-am-i         # try it"
  fi
  if (( WANT_CODEX )); then
    say ""
    say "  Codex CLI:"
    say "    1. codex                  # fresh session"
    say "    2. \$EDITOR ~/.squirrel/config.toml   # set vault_path"
    say "    3. /sq-where-am-i"
  fi
  if (( WANT_CURSOR )); then
    say ""
    say "  Cursor:"
    say "    1. Open Cursor → Settings → Rules for AI."
    say "    2. Paste:"
    say "         Use ~/.cursor/rules/squirrel/ for managing project context,"
    say "         shutdown notes, and cross-environment transfers."
    say "    3. Restart Cursor."
  fi
  if (( WANT_STANDALONE )) || (( ! SKIP_CLI )); then
    say ""
    say "  Terminal:"
    say "    squirrel --help           # confirm CLI on PATH"
    say "    squirrel status"
    say "    squirrel deadlines"
  fi
  if (( WANT_MENUBAR )); then
    say ""
    say "  Menu bar:"
    say "    Look for the 🐿 in your macOS top bar (refreshes every 5 min)."
    say "    Optional config: ~/.squirrel/menubar.env (SQUIRREL_API_BASE / SQUIRREL_UI_BASE)."
  fi
  say ""
}

# ─── Detection screen (info only, enter to continue) ─────────────────────────
show_detection() {
  clear_screen
  banner
  step "Pre-flight"
  ok "Python $(python3 -c 'import sys;print(f"{sys.version_info[0]}.{sys.version_info[1]}")') detected"
  say ""
  say "  Agents found on this machine:"
  printf '    %s Claude Code   %s\n' "$( ((HAS_CLAUDE)) && echo "${C_GREEN}✓${C_RESET}" || echo "${C_YELLOW}—${C_RESET}")" \
         "$( ((HAS_CLAUDE)) && echo "(found ~/.claude/)" || echo "${TERM_DIM}(not detected)${C_RESET}")"
  printf '    %s Codex CLI     %s\n' "$( ((HAS_CODEX)) && echo "${C_GREEN}✓${C_RESET}" || echo "${C_YELLOW}—${C_RESET}")" \
         "$( ((HAS_CODEX)) && echo "(found ~/.codex/)" || echo "${TERM_DIM}(not detected)${C_RESET}")"
  printf '    %s Cursor        %s\n' "$( ((HAS_CURSOR)) && echo "${C_GREEN}✓${C_RESET}" || echo "${C_YELLOW}—${C_RESET}")" \
         "$( ((HAS_CURSOR)) && echo "(found ~/.cursor/)" || echo "${TERM_DIM}(not detected)${C_RESET}")"
  say ""
  printf '%s  Press ENTER to start setup  ·  q to quit%s\n' "$TERM_DIM" "$C_RESET"
  printf '%s' "$TERM_HIDE_CURSOR"
  while true; do
    local key
    key=$(read_key)
    case "$key" in
      ENTER) printf '%s' "$TERM_SHOW_CURSOR"; return 0 ;;
      QUIT|ESC) printf '%s' "$TERM_SHOW_CURSOR"; clear_screen; warn "Aborted."; exit 1 ;;
    esac
  done
}

# ─── Main flow ───────────────────────────────────────────────────────────────
main() {
  require_python
  # The no-plugin installer resolves its own sources (incl. the CLI under
  # apps/cli/), so it doesn't require a co-located ./squirrel binary.
  (( NO_PLUGIN )) || require_squirrel_cli "$ROOT"
  detect_agents

  if (( AUTO_MODE )); then
    banner
    WANT_CLAUDE=$HAS_CLAUDE
    WANT_CODEX=$HAS_CODEX
    WANT_CURSOR=$HAS_CURSOR
    (( WANT_CLAUDE || WANT_CODEX || WANT_CURSOR )) || WANT_CLAUDE=1
    info "Auto mode — installing for: $(list_agents)"
    do_install
    show_done
    return 0
  fi

  if [[ ! -t 0 || ! -t 1 ]]; then
    die "Interactive mode requires a TTY. Use --auto for non-interactive install, or use the per-agent scripts in scripts/."
  fi

  show_detection
  run_tui
  # Ask about the web UI as a final yes/no step (R-11.1, default No).
  if (( WANT_WEB_UI == 0 )); then
    say ""
    say "Web UI (browser interface) — optional companion that runs locally."
    read -r -p "Install the Web UI now? [y/N] " _ans || true
    case "$_ans" in
      y|Y|yes|YES) WANT_WEB_UI=1 ;;
      *)           WANT_WEB_UI=0 ;;
    esac
  fi
  # Menu bar companion (macOS only, requires the Web UI server).
  if (( WANT_WEB_UI )) && (( WANT_MENUBAR == 0 )) && [[ "$(uname)" == "Darwin" ]]; then
    say ""
    say "Menu bar companion — native macOS app (~170KB) showing your Deadlines."
    say "(Pre-built binary, no Homebrew or third-party dependencies.)"
    read -r -p "Install the menu bar companion now? [y/N] " _ans || true
    case "$_ans" in
      y|Y|yes|YES) WANT_MENUBAR=1 ;;
      *)           WANT_MENUBAR=0 ;;
    esac
  fi
  do_install
  show_done
}

main "$@"
