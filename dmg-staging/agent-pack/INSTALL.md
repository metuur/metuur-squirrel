# 📥 Installing squirrel

Step-by-step guide to install and configure the plugin across different agents.

---

## 📋 Prerequisites

1. **Python 3.9+** (for the package protocol script)
   ```bash
   python3 --version  # must be 3.9 or later
   ```

2. **An Obsidian vault** (or any Markdown folder) with the ADHD system structure. If you do not have one, unzip `vault-tdah-obsidian.zip` first.

3. **A compatible coding agent**: Claude Code, Codex CLI, Cursor, GitHub Copilot, or equivalent.

---

## 🚀 Installing in Claude Code

### Step 1: Copy the plugin

```bash
# Clone or copy the plugin directory
cp -r squirrel ~/.claude/plugins/

# Or symlink it if you want it to stay updated from the repo
ln -s /path/to/repo/squirrel ~/.claude/plugins/squirrel
```

### Step 2: Restart Claude Code

```bash
# Close active sessions
# Open a new session
claude
```

The slash commands `/sq-*` should appear when you type `/`.

### Step 3: Verify installation

Inside Claude Code:

```
/plugin list
```

`squirrel v0.5.0` should appear.

### Step 4: Configure

```
/sq-init
```

It will ask for:
- `vault_path`: absolute path to your vault (example: `/home/user/vault-tdah`)
- `environment_name`: `personal` or `work`
- `default_email`: your email for drafts
- `active_projects`: list of WIP tags (example: `TRABAJO-PROYECTO-A,SIDEPROJECT-FOYER-FAMILY,VISA-FAMILIA`)

This creates `~/.squirrel/config.toml`.

#### Multi-vault schema (v0.6+)

Starting in v0.6, `config.toml` uses an `[[vaults]]` array to support multiple
vaults in the same environment (for example personal + work + client-A). The
default is marked with `default = true` (exactly one):

```toml
machine_environment = "personal"   # before: environment_name
default_email = "you@example.com"

[[vaults]]
name = "personal"
path = "~/vault-tdah"
default = true

[[vaults]]
name = "work"
path = "~/work-vault"
default = false

[projects]
active = ["TRABAJO-PROYECTO-A", "SIDEPROJECT-FOYER-FAMILY"]
```

**Automatic migration (lazy + idempotent)**: if your `config.toml` is still in
the old format (`vault_path = ...` and `environment_name = ...`), squirrel
migrates it to the new schema the first time any command reads it. You will see
a `# Auto-migrated <date>` line at the top of the file — that is the only
observable signal; there is no extra output and no manual command to run.
Running it twice is a no-op.

**Manage vaults from the CLI**: add/list/remove/set default with
`squirrel vaults add NAME PATH`, `squirrel vaults list`,
`squirrel vaults remove NAME`, `squirrel vaults default NAME`. To add a vault
interactively from Claude Code: `/sq-init --add-vault`.

**Target a specific vault from a command**: pass `--vault NAME` to commands
that touch the vault (`squirrel status`, `squirrel deadlines`,
`squirrel recover`, `squirrel dashboard`, and the equivalent `/sq-*`
slash commands). Without the flag, they operate on the default vault.

### Step 5: Test

```
/sq-where-am-i
```

It should show the state of your WIP projects. If you just installed the vault,
it will tell you there is no previous activity.

---

## 🚀 Installing in Codex CLI

Codex handles skills and commands similarly, but with different paths.

### Step 1: Copy skills

```bash
mkdir -p ~/.codex/skills
cp -r squirrel/skills/* ~/.codex/skills/
```

### Step 2: Copy slash commands

```bash
mkdir -p ~/.codex/commands
cp squirrel/commands/*.md ~/.codex/commands/
```

### Step 3: Reference them from AGENTS.md

Add this to the global `~/.codex/AGENTS.md`:

```markdown
# Context Bridge

When the user mentions managing context across sessions or environments, use the
squirrel skills installed at ~/.codex/skills/. The main entry points are:

- /sq-start [PROJECT-TAG] — load project context
- /sq-end — save shutdown notes
- /sq-brief — generate structured status
- /sq-sync-out — export package for another environment
- /sq-sync-in — apply pasted package

Configuration lives at ~/.squirrel/config.toml.
```

### Step 4: Configure

Codex does not have an interactive `/sq-init` command, but you can create the
config manually:

```bash
mkdir -p ~/.squirrel
cat > ~/.squirrel/config.toml << 'EOF'
vault_path = "/home/user/vault-tdah"
environment_name = "personal"
default_email = "your-email@example.com"

[projects]
active = ["TRABAJO-PROYECTO-A", "SIDEPROJECT-FOYER-FAMILY", "VISA-FAMILIA"]

[compliance]
strict = false
allowed_inbound_tags = ["*"]

[encryption]
enabled = false
EOF
```

### Step 5: Test

```bash
codex
> /sq-where-am-i
```

---

## 🚀 Installing for GitHub Copilot

Squirrel integrates with Copilot by placing files on disk. Supported surfaces: VS Code Copilot Chat, JetBrains Copilot, and the Copilot CLI.

### One-command install (user-level — applies to all workspaces)

```bash
cd <squirrel-repo>
./scripts/install-copilot.sh --yes
```

| Component | Destination |
|-----------|-------------|
| Skill agents | `~/.copilot/agents/squirrel-<name>.agent.md` |
| Slash-command prompts | `~/.copilot/prompts/sq-<cmd>.prompt.md` |
| Manifest | `~/.copilot/copilot-instructions.md` (block appended) |
| Hooks | `~/.copilot/hooks/squirrel.json` |

Override the destination with the `COPILOT_HOME` environment variable.

### Workspace-level install (files tracked in Git)

```bash
./scripts/install-copilot.sh --workspace --yes
```

Files land under `.github/` in the current git repository. **Commit them** so teammates pick up the Squirrel integration automatically. The installer prints a reminder.

### Flag reference

| Flag | Effect |
|------|--------|
| `--workspace` | Write to `<repo-root>/.github/` instead of `~/.copilot/` |
| `--link` | Create symlinks (auto-update on `git pull`) |
| `--dry-run` | Preview without writing |
| `--yes` / `-y` | Non-interactive |
| `--no-config` | Skip `~/.squirrel/config.toml` seed |
| `--no-cli` | Skip `squirrel` CLI symlink |
| `--no-reminders` | Skip macOS launchd daemon |
| `--prefix=PATH` | CLI symlink destination (default `~/.local/bin`) |

### After install

1. Restart VS Code (or reload the Copilot extension).
2. Set your vault path: `$EDITOR ~/.squirrel/config.toml`
3. In Copilot Chat: `/sq-where-am-i`

---

## 🚀 Installing in Cursor / VSCode

Cursor uses `.cursor/rules/` to load rules and skills.

### Step 1: Copy skills as rules

```bash
mkdir -p ~/.cursor/rules/squirrel
cp -r squirrel/skills/* ~/.cursor/rules/squirrel/
```

### Step 2: Reference them in Cursor settings

In `Settings → Rules for AI`:

```
Use ~/.cursor/rules/squirrel/ for managing project context, shutdown notes,
and cross-environment transfers. See SKILL.md files in each subdirectory.
```

### Step 3: Commands via VSCode tasks

Cursor does not have native slash commands, but you can create tasks in `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "cb-sync-out",
      "type": "shell",
      "command": "python3 ~/.claude/plugins/squirrel/lib/package_protocol.py generate --vault ${input:vault} --scope ${input:scope}",
      "inputs": [...]
    }
  ]
}
```

---

## 🚀 Standalone installation (no agent)

The Python script works completely on its own:

```bash
# Generate package
python3 squirrel/lib/package_protocol.py generate \
  --vault ~/vault-tdah \
  --scope TRABAJO-PROYECTO-A:research \
  --from-env personal \
  --to-env work \
  --output /tmp/package.md

# Validate
python3 squirrel/lib/package_protocol.py validate --input /tmp/package.md

# Apply
python3 squirrel/lib/package_protocol.py apply \
  --input /tmp/package.md \
  --vault ~/work-vault
```

Useful for automation (cron, scripts) or if you want to use the protocol without an LLM agent.

---

## 🛡️ Manual install from DMG (Gatekeeper blocked)

Use this path when macOS blocks the `Install Squirrel` script with a "can't be opened because it is from an unidentified developer" error, or when you need a quick install during development without waiting for a signed build.

### Why the normal installer fails

macOS attaches a `com.apple.quarantine` flag to every file downloaded from the internet (including DMG contents). The `Install Squirrel` script is a shell script, not a notarized binary, so Gatekeeper refuses to run it. Additionally, the installer runs `codesign --verify --strict --deep` on the binaries before copying them — this also fails on unsigned dev builds.

### Step-by-step manual install

**1. Mount the DMG**

Double-click the `.dmg` file in Finder, or from the terminal:

```bash
hdiutil attach ~/Downloads/Squirrel.dmg
# Note the mount path printed — usually /Volumes/Squirrel
```

**2. Strip the quarantine flag from all DMG contents**

```bash
xattr -cr /Volumes/Squirrel/
```

This removes `com.apple.quarantine` recursively so macOS stops blocking the files.

**3. Copy the binaries** (skipping the codesign check)

```bash
mkdir -p ~/.local/bin

cp /Volumes/Squirrel/bin/squirrel           ~/.local/bin/squirrel
cp /Volumes/Squirrel/bin/squirrel-backend   ~/.local/bin/squirrel-backend
chmod +x ~/.local/bin/squirrel ~/.local/bin/squirrel-backend

# Remove quarantine from the copied binaries too
xattr -d com.apple.quarantine ~/.local/bin/squirrel          2>/dev/null || true
xattr -d com.apple.quarantine ~/.local/bin/squirrel-backend  2>/dev/null || true
```

**4. Ensure `~/.local/bin` is on your PATH**

```bash
echo $PATH | grep -q "$HOME/.local/bin" || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**5. Install the agent-pack**

```bash
mkdir -p ~/.claude/plugins/squirrel
rsync -a --delete /Volumes/Squirrel/agent-pack/ ~/.claude/plugins/squirrel/
```

**6. Seed the config** (skip if `~/.squirrel/config.toml` already exists)

```bash
mkdir -p ~/.squirrel
cp /Volumes/Squirrel/resources/squirrel.toml.example ~/.squirrel/config.toml
$EDITOR ~/.squirrel/config.toml   # set vault path
```

**7. Install and start the background service**

```bash
BACKEND_BIN="$HOME/.local/bin/squirrel-backend"
PLIST_PATH="$HOME/Library/LaunchAgents/org.squirrel.web-ui.plist"
mkdir -p "$HOME/Library/LaunchAgents"

plist="$(cat /Volumes/Squirrel/resources/plist.template)"
plist="${plist//__BINARY__/$BACKEND_BIN}"
plist="${plist//__PORT__/3939}"
plist="${plist//__HOME__/$HOME}"
printf '%s\n' "$plist" > "$PLIST_PATH"

launchctl load "$PLIST_PATH"
```

**8. Verify**

```bash
squirrel --help
curl -s http://127.0.0.1:3939/health   # should return {"status":"ok"}
```

Then inside Claude Code:

```
/sq-status
```

### Potential issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `zsh: killed squirrel` or binary crashes silently | macOS Gatekeeper killed the unsigned binary | `xattr -d com.apple.quarantine ~/.local/bin/squirrel` |
| `command not found: squirrel` | `~/.local/bin` not on PATH | Add `export PATH="$HOME/.local/bin:$PATH"` to `~/.zshrc` and re-open the terminal |
| `launchctl: service already loaded` | Previous install left the plist registered | `launchctl unload "$PLIST_PATH" && launchctl load "$PLIST_PATH"` |
| `curl` to port 3939 times out | Backend plist still points to old binary path | Check the plist: `cat ~/Library/LaunchAgents/org.squirrel.web-ui.plist` — rerun step 7 if the `__BINARY__` placeholder was not replaced |
| `/sq-*` commands missing in Claude Code | agent-pack not installed or wrong destination | Verify `~/.claude/plugins/squirrel/` exists and contains `SKILL.md` files; re-run step 5 |
| `rsync: No such file or directory` | DMG not mounted | Run `hdiutil attach ~/Downloads/Squirrel.dmg` first |

### Uninstalling

```bash
launchctl unload ~/Library/LaunchAgents/org.squirrel.web-ui.plist 2>/dev/null || true
rm -f ~/Library/LaunchAgents/org.squirrel.web-ui.plist
rm -f ~/.local/bin/squirrel ~/.local/bin/squirrel-backend
rm -rf ~/.claude/plugins/squirrel
# Optionally remove config and vault:
# rm -rf ~/.squirrel
```

---

## 🔧 Advanced configuration

### Multiple environments (more than 2)

If you have more than two environments (for example personal + work + client A), create one config per environment:

```bash
# Personal environment
mkdir -p ~/.squirrel.personal
cp ~/.squirrel/config.toml ~/.squirrel.personal/

# Client A environment
mkdir -p ~/.squirrel.client-a
# edit config with environment_name = "client-a", different vault_path

# Switch between environments
export CONTEXT_BRIDGE_HOME=~/.squirrel.client-a
```

### Strict mode (corporate compliance)

In `~/.squirrel/config.toml`:

```toml
[compliance]
strict = true
allowed_inbound_tags = ["TRABAJO-*", "OPENSOURCE-*"]
allowed_inbound_environments = ["personal"]
corporate_domains = ["mycompany.com"]
```

This blocks packages that:
- Come from an environment that is not listed
- Contain files with tags outside the allowed set
- Mention emails from corporate domains (to avoid leaks)

### GPG encryption

```toml
[encryption]
enabled = true
gpg_recipient = "your-email@example.com"
```

Prerequisite: have your GPG key generated and `gpg` on your PATH.

Generate a key if you do not already have one:
```bash
gpg --gen-key  # follow the prompts
```

After that, packages generated with `/sq-sync-out` are encrypted automatically.
The other side decrypts with `/sq-sync-in` if it has the private key.

---

## ❓ Troubleshooting

### "`Install Squirrel` is blocked by macOS / codesign error"

macOS quarantines every file from the internet, including DMG contents. The installer also runs `codesign --verify --strict --deep` on the binaries — this fails on unsigned dev builds.

**Quick fix** — strip the quarantine flag before running the installer:

```bash
xattr -cr /Volumes/Squirrel/
"/Volumes/Squirrel/Install Squirrel"
```

If that still fails (e.g. the binaries are unsigned), follow the **Manual install from DMG** section above — it skips the codesign check entirely.

### "Slash commands do not appear in Claude Code"
- Verify the directory is at `~/.claude/plugins/squirrel/`
- Verify `.claude-plugin/plugin.json` exists and is valid JSON
- Restart Claude Code completely (close all sessions)

### "The skill is not invoked automatically"
- The frontmatter `description` must match the context
- Try an explicit slash command invocation first
- Verify the agent loads skills from the correct directory

### "Hash mismatch during sync-in"
- The package was truncated in the clipboard/email
- Verify you copied everything from `<!-- CONTEXT-BRIDGE-PACKAGE` to `END-CONTEXT-BRIDGE-PACKAGE -->`
- If you pasted from email, watch out for line wrapping — some clients insert forced line breaks

### "Compliance scan blocks legitimate content"
- The scan is conservative. If you get a false positive:
  - Option 1: redact the pattern in the original note (best)
  - Option 2: `--force-include` (NOT recommended for repeated use)

### "The vault does not have the expected structure"
- The skills assume `01-Proyectos-Activos/`, `02-Parking-Lot/`, etc.
- If your vault uses a different structure, edit the relevant skills (for example `session-start/SKILL.md` line X)
- Or migrate your vault to the ADHD system (unzip `vault-tdah-obsidian.zip` as a reference)

---

## 🆘 Support

To report issues or suggestions:
- Issues in the plugin repo
- Or write feedback in `99-Resources/squirrel-feedback.md` in your vault

---

## 🔄 Updating

```bash
cd ~/.claude/plugins/squirrel
git pull  # if it is a git repo

# Or overwrite it by copying a new version
```

The settings in `~/.squirrel/` are preserved between updates.
