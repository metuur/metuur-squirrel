# Copilot Agent Integration — Verified 2026-06-01

macOS 25.5.0 Darwin (arm64). Copilot CLI not installed on dev machine; full
live session test (criteria 4–6) deferred until VS Code + Copilot Chat is
active. Static criteria verified below.

## Success criteria status

1. **CLI fourth-branch test** ✅
   - `python3 apps/cli/squirrel install --agent copilot --dry-run` exits 0.
   - `python3 apps/cli/squirrel install --help` lists `copilot` in `--agent` choices.

2. **User-level install test** ✅ (dry-run only; no live Copilot install on machine)
   - Dry-run outputs `~/.copilot/agents`, `~/.copilot/prompts`,
     `~/.copilot/copilot-instructions.md`, `~/.copilot/hooks/squirrel.json`.
   - Claude/Codex/Cursor branches unmodified (pre-existing behaviour unchanged;
     all 533 passing tests still pass after change).

3. **Workspace-level install test** ✅
   - `--workspace` inside git repo → `.github/` destinations.
   - `--workspace` outside git repo → exits non-zero with clear message.
   - Idempotency: dry-run is safe to re-run (no state to double-apply).

4. **Manifest write through Copilot test** — DEFERRED
   Not verifiable without a live Copilot Chat session. Requires running
   `install-copilot.sh --yes` on a machine with VS Code + Copilot Chat installed.

5. **Recovery test** — DEFERRED
   Requires live Copilot session state files.

6. **User-prompt pattern detection** — DEFERRED
   Requires live Copilot Chat + hooks loaded.

7. **Idempotency test** ✅ (static)
   - `_patch_copilot_instructions_md`: marker check prevents duplicate blocks.
   - `_emit_copilot_hooks_json`: full overwrite semantics (generated content).
   - Both checked in code; live verification deferred to #4–6 above.

8. **Existing agents untouched** ✅
   - All 533 pre-existing tests pass after change; 3 pre-existing failures
     unrelated to this feature.

9. **Docs parity test** ✅
   - `grep -c "Copilot" README.md` → 12 (≥ 5 required).
   - `agent-pack/INSTALL.md` has a full Copilot install section.
   - `agent-pack/INSTALL-README.md` lists `install-copilot.sh` and maps Copilot
     to its destination dirs.

## Open uncertainty resolved (partially)

The Copilot hook delivery shape (env vars vs stdin JSON) was unconfirmed at
spec time. Both adapters (`hook-adapter.sh`, `hook-adapter-stdin.sh`) are
shipped. `squirrel.json` wires `hook-adapter.sh` (env-vars delivery) by default.
Outcome: **unresolved empirically** — no live Copilot session on this machine.
Switch hooks to stdin variant if `$EVENT` / `$USER_PROMPT` are empty in a real
run (edit `_cmd()` in `_emit_copilot_hooks_json` and re-run the installer).
