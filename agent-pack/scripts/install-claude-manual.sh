#!/usr/bin/env bash
#
# install-claude-manual.sh — install Squirrel for Claude Code WITHOUT the plugin
# marketplace. For locked-down / corporate environments where org policy blocks
# installing plugins from outside the organization.
#
# Instead of registering a plugin under ~/.claude/plugins/ (which a managed org
# can block), this drops everything into Claude Code's NATIVE personal locations,
# which load independently of the marketplace:
#
#   • Skills    → ~/.claude/skills/<squirrel-*>/SKILL.md
#   • Commands  → ~/.claude/commands/sq-*.md   (the /sq-* slash commands)
#   • Hooks     → merged into ~/.claude/settings.json  ("hooks" key)
#   • Support   → ~/.claude/squirrel/  (Python lib/, wrapper scripts, templates,
#                 and the `squirrel` CLI) — a plain folder, NOT under plugins/
#   • Config    → ~/.squirrel/config.toml  (seeded from template if missing)
#   • CLI       → optional symlink at ~/.local/bin/squirrel
#
# Hardcoded `~/.claude/plugins/squirrel/...` paths inside the copied skills,
# commands, and wrapper scripts are rewritten to `~/.claude/squirrel/...` so they
# resolve against the support folder above.
#
# Usage:
#   ./scripts/install-claude-manual.sh            # install (copy + rewrite)
#   ./scripts/install-claude-manual.sh --dry-run  # preview, no writes
#   ./scripts/install-claude-manual.sh --yes      # non-interactive
#
# Opt-out flags:
#   --no-config      do not create ~/.squirrel/config.toml
#   --no-cli         do not symlink `squirrel` into ~/.local/bin
#   --no-hooks       do not merge hooks into ~/.claude/settings.json
#   --prefix=PATH    install the CLI symlink here (default: ~/.local/bin)
#
# Uninstall with: ./scripts/uninstall-claude-manual.sh
#
# NOTE: if your org sets "disableAllHooks": true in managed settings, the merged
# hooks will not fire — the skills and slash commands still work.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "$SCRIPT_DIR/_lib.sh"

print_help_and_exit() {
  awk 'NR>1 && /^#/ {sub(/^# ?/,""); print; next} NR>1 {exit}' "${BASH_SOURCE[0]}"
  exit 0
}

# ─── Argument parsing (--no-hooks on top of the shared flags) ─────────────────
SKIP_HOOKS=0
REPO=""          # optional explicit path to the squirrel repo (holds apps/cli/lib)
RAW_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --no-hooks) SKIP_HOOKS=1 ;;
    --repo=*)   REPO="${arg#--repo=}" ;;
    --repo)     die "Use --repo=PATH (with =, no space)" ;;
    *)          RAW_ARGS+=("$arg") ;;
  esac
done
parse_common_args "${RAW_ARGS[@]+"${RAW_ARGS[@]}"}"
[[ ${#LEFTOVER_ARGS[@]} -eq 0 ]] || die "Unknown argument(s): ${LEFTOVER_ARGS[*]} (try --help)"
(( USE_LINK )) && die "--link is not supported for a manual install: files must be copied so their paths can be rewritten."

# Human-readable "[dry run]" suffix (DRY_RUN holds "0"/"1", so :+ won't work).
DRY_TAG=""; (( DRY_RUN )) && DRY_TAG="  [dry run]"
DRY_DONE=""; (( DRY_RUN )) && DRY_DONE="  (dry run — nothing was written)"

# ─── Resolve source directories (works from the repo, a packaged build, OR the
#     installed plugin dir) ──────────────────────────────────────────────────
# PACK holds skills/commands/scripts/hooks/templates/config. In the repo this is
# agent-pack/; in a flattened package (or the installed ~/.claude/plugins/squirrel)
# it is the same dir as this script's parent.
PACK="$(cd "$SCRIPT_DIR/.." && pwd)"

# Find lib/where_am_i_formatter.py + a sibling `squirrel`. A correctly built
# package/plugin bundles lib/ at the pack root ($PACK/lib), so that resolves
# immediately. The repo and $HOME-search cases are dev-only fallbacks.
LIB_SRC=""
CLI_SRC=""
try_lib_base() {
  # $1 = base dir expected to contain lib/where_am_i_formatter.py
  [[ -n "$LIB_SRC" ]] && return 0
  if [[ -f "$1/lib/where_am_i_formatter.py" ]]; then
    LIB_SRC="$(cd "$1/lib" && pwd)"
    CLI_SRC="$(cd "$1" && pwd)/squirrel"
  fi
}

# 1. cheap, exact candidates — no filesystem scan.
[[ -n "$REPO" ]] && { try_lib_base "$REPO/apps/cli"; try_lib_base "$REPO"; }
try_lib_base "$PACK"            # built package / installed plugin (lib bundled here)
try_lib_base "$PACK/../apps/cli" # running from the repo's agent-pack/

# 2. dev-only fallback: locate a squirrel repo checkout (mirrors the wrapper
#    scripts' search). Only runs if the cheap candidates all missed.
if [[ -z "$LIB_SRC" ]]; then
  while IFS= read -r d; do
    try_lib_base "$d/apps/cli"; try_lib_base "$d"
    [[ -n "$LIB_SRC" ]] && break
  done < <(find "$HOME/others" "$HOME/dev" "$HOME/code" "$HOME/src" "$HOME/projects" "$HOME/repos" \
                -maxdepth 5 -type d -name squirrel 2>/dev/null | grep -v '/.claude/' | head -20)
fi

if [[ -z "$LIB_SRC" ]]; then
  die "Cannot find the Python lib/ (where_am_i_formatter.py).
      This package looks incomplete — a built install bundles it at
      '$PACK/lib'. Run from the squirrel repo, or point at one explicitly:
        $SCRIPT_DIR/install-claude-manual.sh --repo=/path/to/squirrel"
fi
[[ -f "$CLI_SRC" ]] || warn "CLI binary not found next to lib/ ($CLI_SRC) — skipping CLI install."
info "Using Python lib/ from: $LIB_SRC"

SKILLS_SRC="$PACK/skills"
CMDS_SRC="$PACK/commands"
WRAP_SRC="$PACK/scripts"
HOOKS_JSON="$PACK/hooks/hooks.json"
TEMPLATES_SRC="$PACK/templates"

[[ -d "$SKILLS_SRC" ]] || die "Skills source not found: $SKILLS_SRC"
[[ -d "$CMDS_SRC"   ]] || die "Commands source not found: $CMDS_SRC"

# ─── Destinations ────────────────────────────────────────────────────────────
SKILLS_DST="$HOME/.claude/skills"
CMDS_DST="$HOME/.claude/commands"
SUPPORT="$HOME/.claude/squirrel"
SETTINGS="$HOME/.claude/settings.json"
MANIFEST="$SUPPORT/.install-manifest.json"

# Track what we install (for the manifest / uninstaller).
INSTALLED_SKILLS=()
INSTALLED_CMDS=()
REWRITE_FILES=()   # copied files that need the path rewrite

# ─── Helpers ─────────────────────────────────────────────────────────────────
rewrite_paths() {
  # Re-point hardcoded ~/.claude/plugins/squirrel/... at ~/.claude/squirrel/...
  local f="$1"
  (( DRY_RUN )) && return 0
  perl -i -pe 's{\.claude/plugins/squirrel}{.claude/squirrel}g' "$f"
}

hdr "Installing Squirrel — Claude Code (manual, no-plugin)${DRY_TAG}"
require_python
command -v perl >/dev/null 2>&1 || die "perl not found on PATH (needed to rewrite plugin paths)."

# ─── Step 1: support directory (lib, scripts, templates, CLI) ────────────────
step "Support files → $SUPPORT/"
if (( DRY_RUN )); then
  info "[dry-run] would copy lib/ → $SUPPORT/lib/"
  [[ -f "$CLI_SRC" ]] && info "[dry-run] would copy squirrel CLI → $SUPPORT/squirrel"
  info "[dry-run] would copy sq-*.sh wrappers → $SUPPORT/scripts/"
  [[ -d "$TEMPLATES_SRC" ]] && info "[dry-run] would copy templates/ → $SUPPORT/templates/"
else
  mkdir -p "$SUPPORT/scripts"
  rm -rf "$SUPPORT/lib"
  cp -R "$LIB_SRC" "$SUPPORT/lib"
  if [[ -f "$CLI_SRC" ]]; then
    cp "$CLI_SRC" "$SUPPORT/squirrel"
    chmod +x "$SUPPORT/squirrel"
  fi
  for w in "$WRAP_SRC"/sq-*.sh; do
    [[ -f "$w" ]] || continue
    cp "$w" "$SUPPORT/scripts/"
    REWRITE_FILES+=("$SUPPORT/scripts/$(basename "$w")")
  done
  if [[ -d "$TEMPLATES_SRC" ]]; then
    rm -rf "$SUPPORT/templates"
    cp -R "$TEMPLATES_SRC" "$SUPPORT/templates"
  fi
  ok "Support files installed → $SUPPORT/"
fi

# ─── Step 2: skills → ~/.claude/skills/ ──────────────────────────────────────
step "Skills → $SKILLS_DST/"
for skill_dir in "$SKILLS_SRC"/*/; do
  [[ -d "$skill_dir" ]] || continue
  name="$(basename "$skill_dir")"
  case "$name" in '{'*|.*) continue ;; esac   # skip template placeholders / hidden
  INSTALLED_SKILLS+=("$name")
  if (( DRY_RUN )); then
    info "[dry-run] would install skill: $name"
  else
    rm -rf "${SKILLS_DST:?}/$name"
    mkdir -p "$SKILLS_DST"
    cp -R "$skill_dir" "$SKILLS_DST/$name"
    while IFS= read -r f; do REWRITE_FILES+=("$f"); done \
      < <(grep -rl '.claude/plugins/squirrel' "$SKILLS_DST/$name" 2>/dev/null || true)
  fi
done
(( DRY_RUN )) || ok "${#INSTALLED_SKILLS[@]} skills installed → $SKILLS_DST/"

# ─── Step 3: commands → ~/.claude/commands/ ──────────────────────────────────
step "Slash commands → $CMDS_DST/"
for cmd_file in "$CMDS_SRC"/*.md; do
  [[ -f "$cmd_file" ]] || continue
  name="$(basename "$cmd_file")"
  INSTALLED_CMDS+=("$name")
  if (( DRY_RUN )); then
    info "[dry-run] would install command: /${name%.md}"
  else
    mkdir -p "$CMDS_DST"
    cp "$cmd_file" "$CMDS_DST/$name"
    if grep -q '.claude/plugins/squirrel' "$CMDS_DST/$name" 2>/dev/null; then
      REWRITE_FILES+=("$CMDS_DST/$name")
    fi
  fi
done
(( DRY_RUN )) || ok "${#INSTALLED_CMDS[@]} commands installed → $CMDS_DST/"

# ─── Step 4: rewrite hardcoded plugin paths in everything we copied ──────────
step "Rewriting plugin paths → ~/.claude/squirrel/"
if (( DRY_RUN )); then
  info "[dry-run] would rewrite '.claude/plugins/squirrel' → '.claude/squirrel' in copied skills, commands, and wrappers"
else
  for f in "${REWRITE_FILES[@]}"; do rewrite_paths "$f"; done
  ok "Rewrote ${#REWRITE_FILES[@]} file(s)"
fi

# ─── Step 5: hooks → ~/.claude/settings.json ─────────────────────────────────
HOOKS_ADDED=""
if (( SKIP_HOOKS )); then
  step "Hooks"
  info "Skipping hook merge (--no-hooks)"
elif [[ ! -f "$HOOKS_JSON" ]]; then
  step "Hooks"
  warn "hooks.json not found ($HOOKS_JSON) — skipping hook merge."
else
  step "Hooks → $SETTINGS"
  HOOKS_ADDED="$(SQ_HOOKS_SRC="$HOOKS_JSON" SQ_SETTINGS="$SETTINGS" SQ_DRY="$DRY_RUN" python3 - <<'PY'
import json, os, re, sys

src_path = os.environ["SQ_HOOKS_SRC"]
settings_path = os.path.expanduser(os.environ["SQ_SETTINGS"])
dry = os.environ.get("SQ_DRY", "0") == "1"

src = json.load(open(src_path)).get("hooks", {})

settings = {}
if os.path.isfile(settings_path):
    try:
        settings = json.load(open(settings_path))
    except json.JSONDecodeError:
        sys.stderr.write(f"settings.json is malformed: {settings_path} — not modifying.\n")
        sys.exit(3)

# A command is "squirrel-owned" if it lives in squirrel's namespace. Matching on
# these stable tokens — NOT the exact command text — is what makes a re-install
# REPLACE our hooks instead of appending a near-duplicate every time the command
# string changes (version bump, bugfix, copy edit). The user's own hooks, which
# carry none of these tokens, are left untouched.
SQ_MARKER = re.compile(r"squirrel|/sq-|SQUIRREL-", re.IGNORECASE)
def is_sq(h):
    return h.get("type") == "command" and bool(SQ_MARKER.search(h.get("command", "")))

dst = settings.setdefault("hooks", {})

# 1) Strip every previously-installed squirrel hook (from any version), keeping
#    the user's own hooks and dropping groups that were entirely ours.
removed = []
for event in list(dst.keys()):
    groups = []
    for g in dst[event]:
        ours = [h for h in g.get("hooks", []) if is_sq(h)]
        removed += [h.get("command") for h in ours]
        if not ours:
            groups.append(g)
            continue
        keep = [h for h in g.get("hooks", []) if not is_sq(h)]
        if keep:
            ng = dict(g)
            ng["hooks"] = keep
            groups.append(ng)
    if groups:
        dst[event] = groups
    else:
        del dst[event]

# 2) Add the current source hooks fresh — exactly one copy of each.
added = []
for event, src_groups in src.items():
    existing = dst.setdefault(event, [])
    for g in src_groups:
        cmds = [h for h in g.get("hooks", []) if h.get("type") == "command"]
        if not cmds:
            continue
        existing.append(dict(g))
        added += [h["command"] for h in cmds]

if not dry:
    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    with open(settings_path, "w") as fh:
        json.dump(settings, fh, indent=4)

if removed:
    sys.stderr.write(f"{'Would replace' if dry else 'Replaced'} {len(removed)} pre-existing squirrel hook(s).\n")

print("\n".join(added))
PY
)" || die "Hook merge failed (see message above)."
  added_count="$(printf '%s' "$HOOKS_ADDED" | grep -c . || true)"
  if (( DRY_RUN )); then
    info "[dry-run] would install $added_count squirrel hook command(s) into $SETTINGS (replacing any prior version)"
  else
    ok "Installed $added_count squirrel hook command(s) → $SETTINGS (replaced any prior version)"
  fi
fi

# ─── Step 6: config seed (reuses _lib.sh; looks in $PACK/config) ─────────────
install_config "$PACK"

# ─── Step 7: CLI symlink → ~/.local/bin/squirrel ─────────────────────────────
CLI_LINK=""
if (( SKIP_CLI )) || [[ ! -f "$CLI_SRC" ]]; then
  (( SKIP_CLI )) && { step "CLI"; info "Skipping CLI install (--no-cli)"; }
else
  step "CLI → $CLI_PREFIX/squirrel"
  CLI_LINK="$CLI_PREFIX/squirrel"
  if (( DRY_RUN )); then
    info "[dry-run] would symlink $CLI_LINK -> $SUPPORT/squirrel"
  else
    mkdir -p "$CLI_PREFIX"
    [[ -e "$CLI_LINK" || -L "$CLI_LINK" ]] && rm -f "$CLI_LINK"
    ln -s "$SUPPORT/squirrel" "$CLI_LINK"
    ok "CLI symlinked: $CLI_LINK -> $SUPPORT/squirrel"
    echo ":$PATH:" | grep -q ":$CLI_PREFIX:" || warn "$CLI_PREFIX is not on your PATH — add it to your shell rc."
  fi
fi

# ─── Step 8: install manifest (drives the uninstaller) ───────────────────────
if (( ! DRY_RUN )); then
  SQ_SKILLS="$(printf '%s\n' "${INSTALLED_SKILLS[@]+"${INSTALLED_SKILLS[@]}"}")" \
  SQ_CMDS="$(printf '%s\n' "${INSTALLED_CMDS[@]+"${INSTALLED_CMDS[@]}"}")" \
  SQ_HOOKS_JSON="$HOOKS_JSON" \
  SQ_SKIP_HOOKS="$SKIP_HOOKS" \
  SQ_SUPPORT="$SUPPORT" \
  SQ_CLI_LINK="$CLI_LINK" \
  SQ_MANIFEST="$MANIFEST" \
  python3 - <<'PY'
import json, os

def lines(env):
    return [x for x in os.environ.get(env, "").splitlines() if x.strip()]

# Record the COMPLETE set of squirrel hook commands (not just the ones newly
# merged this run) so the uninstaller can always remove them — even when this
# install was an idempotent re-run that added zero new hooks.
hook_cmds = []
if os.environ.get("SQ_SKIP_HOOKS", "0") != "1":
    hj = os.environ.get("SQ_HOOKS_JSON", "")
    if hj and os.path.isfile(hj):
        for groups in json.load(open(hj)).get("hooks", {}).values():
            for g in groups:
                for h in g.get("hooks", []):
                    if h.get("type") == "command":
                        hook_cmds.append(h["command"])

manifest = {
    "installer": "install-claude-manual.sh",
    "support_dir": os.environ["SQ_SUPPORT"],
    "skills": lines("SQ_SKILLS"),
    "commands": lines("SQ_CMDS"),
    "cli_symlink": os.environ.get("SQ_CLI_LINK") or None,
    "hooks_added": hook_cmds,
}
path = os.environ["SQ_MANIFEST"]
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w") as fh:
    json.dump(manifest, fh, indent=2)
PY
fi

# ─── Done ────────────────────────────────────────────────────────────────────
hdr "All done${DRY_DONE}"
say ""
say "Installed (native, no plugin registration):"
say "  ✓ ${#INSTALLED_SKILLS[@]} skills   → $SKILLS_DST/"
say "  ✓ ${#INSTALLED_CMDS[@]} commands → $CMDS_DST/"
say "  ✓ support files     → $SUPPORT/"
(( SKIP_HOOKS )) || say "  ✓ hooks merged      → $SETTINGS"
(( SKIP_CONFIG )) || say "  ✓ config seed       → ~/.squirrel/config.toml"
[[ -n "$CLI_LINK" ]] && say "  ✓ CLI on PATH       → $CLI_LINK"
say ""
say "Next steps:"
say "  1. Close ALL Claude Code windows, then reopen (loads native skills/commands/hooks)."
say "  2. /sq-init          # configure your vault"
say "  3. /sq-where-am-i    # try it"
say ""
say "Uninstall:  $SCRIPT_DIR/uninstall-claude-manual.sh"
if (( ! SKIP_HOOKS )); then
  say ""
  warn "If your org sets \"disableAllHooks\": true in managed settings, the hooks"
  say  "      won't fire — skills and /sq-* commands still work."
fi
