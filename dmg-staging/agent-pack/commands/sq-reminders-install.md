---
description: Installs the macOS reminders daemon (launchd). macOS only. Usage: /sq-reminders-install
allowed-tools: [Bash]
---

# /sq-reminders-install

Installs and activates the squirrel reminders daemon on macOS.

## Step 1: Verify the OS

```bash
uname
```

If it's not `Darwin`, show: "ℹ️  The reminders daemon is only available on macOS." and stop.

## Step 2: Locate the install script

```bash
INSTALL_SCRIPT=$(find "${HOME}/.claude" "${HOME}/others" \
    -name install.sh -path "*/squirrel/companions/macos-reminders/*" \
    2>/dev/null | head -1)
[ -z "$INSTALL_SCRIPT" ] && echo "❌ install.sh not found. Check the plugin installation." && exit 1
```

<!-- @spec INT-010 -->
## Step 3: Run the installer

```bash
bash "$INSTALL_SCRIPT"
```

Show the installer's full output to the user.

If the exit code is != 0, show the error and suggest checking `~/.squirrel/reminders-daemon.log`.
