#!/usr/bin/env bash
#
# uninstall-claude-manual.sh — reverse a manual (no-plugin) Squirrel install.
#
# Reads ~/.claude/squirrel/.install-manifest.json (written by
# install-claude-manual.sh) and removes exactly what was installed:
#   • the squirrel-* skills from ~/.claude/skills/
#   • the sq-*.md commands from ~/.claude/commands/
#   • the support dir ~/.claude/squirrel/
#   • the CLI symlink (if it points into the support dir)
#   • only Squirrel's hook entries from ~/.claude/settings.json
#
# Leaves ~/.squirrel/config.toml (your vault config) untouched unless --purge.
#
# Usage:
#   ./scripts/uninstall-claude-manual.sh            # remove (keeps config)
#   ./scripts/uninstall-claude-manual.sh --dry-run  # preview
#   ./scripts/uninstall-claude-manual.sh --yes      # no confirmation prompt
#   ./scripts/uninstall-claude-manual.sh --purge    # also delete ~/.squirrel/
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "$SCRIPT_DIR/_lib.sh"

print_help_and_exit() {
  awk 'NR>1 && /^#/ {sub(/^# ?/,""); print; next} NR>1 {exit}' "${BASH_SOURCE[0]}"
  exit 0
}

PURGE=0
RAW_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --purge) PURGE=1 ;;
    *)       RAW_ARGS+=("$arg") ;;
  esac
done
parse_common_args "${RAW_ARGS[@]+"${RAW_ARGS[@]}"}"
[[ ${#LEFTOVER_ARGS[@]} -eq 0 ]] || die "Unknown argument(s): ${LEFTOVER_ARGS[*]} (try --help)"

DRY_TAG=""; (( DRY_RUN )) && DRY_TAG="  [dry run]"
DRY_DONE=""; (( DRY_RUN )) && DRY_DONE="  (dry run — nothing was written)"

SKILLS_DST="$HOME/.claude/skills"
CMDS_DST="$HOME/.claude/commands"
SUPPORT="$HOME/.claude/squirrel"
SETTINGS="$HOME/.claude/settings.json"
MANIFEST="$SUPPORT/.install-manifest.json"

hdr "Uninstalling Squirrel — Claude Code (manual)${DRY_TAG}"
require_python

[[ -f "$MANIFEST" ]] || die "No install manifest at $MANIFEST — was this installed with install-claude-manual.sh? Nothing removed."

if (( ! ASSUME_YES )) && (( ! DRY_RUN )); then
  if [[ -t 0 ]]; then
    read -r -p "Remove the manual Squirrel install? [y/N] " reply
    case "${reply,,}" in y|yes) ;; *) info "Aborted."; exit 0 ;; esac
  fi
fi

# ─── Remove skills + commands (names from the manifest) ──────────────────────
step "Removing skills and commands"
while IFS= read -r name; do
  [[ -n "$name" ]] || continue
  target="$SKILLS_DST/$name"
  if [[ -d "$target" ]]; then
    if (( DRY_RUN )); then info "[dry-run] rm -rf $target"; else rm -rf "$target"; ok "removed skill: $name"; fi
  fi
done < <(python3 -c 'import json,sys;[print(s) for s in json.load(open(sys.argv[1])).get("skills",[])]' "$MANIFEST")

while IFS= read -r name; do
  [[ -n "$name" ]] || continue
  target="$CMDS_DST/$name"
  if [[ -f "$target" ]]; then
    if (( DRY_RUN )); then info "[dry-run] rm $target"; else rm -f "$target"; ok "removed command: ${name%.md}"; fi
  fi
done < <(python3 -c 'import json,sys;[print(c) for c in json.load(open(sys.argv[1])).get("commands",[])]' "$MANIFEST")

# ─── Strip only Squirrel's hooks from settings.json ──────────────────────────
step "Removing Squirrel hooks from $SETTINGS"
if [[ -f "$SETTINGS" ]]; then
  SQ_SETTINGS="$SETTINGS" SQ_MANIFEST="$MANIFEST" SQ_DRY="$DRY_RUN" python3 - <<'PY'
import json, os, sys

settings_path = os.path.expanduser(os.environ["SQ_SETTINGS"])
manifest = json.load(open(os.environ["SQ_MANIFEST"]))
dry = os.environ.get("SQ_DRY", "0") == "1"
remove = set(manifest.get("hooks_added", []))

if not remove:
    print("  (no hooks recorded in manifest)")
    sys.exit(0)

try:
    settings = json.load(open(settings_path))
except (json.JSONDecodeError, FileNotFoundError):
    sys.stderr.write("settings.json missing or malformed — leaving hooks alone.\n")
    sys.exit(0)

hooks = settings.get("hooks", {})
removed = 0
for event in list(hooks.keys()):
    new_groups = []
    for g in hooks[event]:
        kept = [h for h in g.get("hooks", [])
                if not (h.get("type") == "command" and h.get("command") in remove)]
        removed += len(g.get("hooks", [])) - len(kept)
        if kept:
            ng = dict(g); ng["hooks"] = kept
            new_groups.append(ng)
    if new_groups:
        hooks[event] = new_groups
    else:
        del hooks[event]
if not hooks:
    settings.pop("hooks", None)

if dry:
    print(f"  [dry-run] would remove {removed} hook command(s)")
else:
    with open(settings_path, "w") as fh:
        json.dump(settings, fh, indent=4)
    print(f"  removed {removed} hook command(s)")
PY
else
  info "No settings.json — nothing to clean."
fi

# ─── Remove CLI symlink + support dir ────────────────────────────────────────
step "Removing CLI symlink and support files"
CLI_LINK="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("cli_symlink") or "")' "$MANIFEST")"
if [[ -n "$CLI_LINK" && -L "$CLI_LINK" ]]; then
  link_target="$(readlink "$CLI_LINK" || true)"
  if [[ "$link_target" == "$SUPPORT/"* ]]; then
    if (( DRY_RUN )); then info "[dry-run] rm $CLI_LINK"; else rm -f "$CLI_LINK"; ok "removed CLI symlink: $CLI_LINK"; fi
  else
    warn "$CLI_LINK does not point into $SUPPORT — leaving it."
  fi
fi

if [[ -d "$SUPPORT" ]]; then
  if (( DRY_RUN )); then info "[dry-run] rm -rf $SUPPORT"; else rm -rf "$SUPPORT"; ok "removed support dir: $SUPPORT"; fi
fi

# ─── Optional: purge user config ─────────────────────────────────────────────
if (( PURGE )); then
  step "Purging ~/.squirrel/ (--purge)"
  if [[ -d "$HOME/.squirrel" ]]; then
    if (( DRY_RUN )); then info "[dry-run] rm -rf $HOME/.squirrel"; else rm -rf "$HOME/.squirrel"; ok "removed $HOME/.squirrel"; fi
  fi
else
  say ""
  info "Kept ~/.squirrel/ (your vault config). Use --purge to remove it too."
fi

hdr "Uninstall complete${DRY_DONE}"
say "Restart Claude Code to drop the removed skills, commands, and hooks."
