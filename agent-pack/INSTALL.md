# 📥 Installing squirrel

Step-by-step guide to install and configure the plugin across different agents.

---

## 📋 Prerequisites

1. **Python 3.9+** (for the package protocol script)
   ```bash
   python3 --version  # must be 3.9 or later
   ```

2. **An Obsidian vault** (or any Markdown folder) with the ADHD system structure. If you do not have one, unzip `vault-tdah-obsidian.zip` first.

3. **A compatible coding agent**: Claude Code, Codex CLI, Cursor, or equivalent.

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
