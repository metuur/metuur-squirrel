---
description: Uninstalls the macOS reminders daemon. Usage: /sq-reminders-uninstall
allowed-tools: [Bash]
---

# /sq-reminders-uninstall

Stops and uninstalls the squirrel reminders daemon.

## Step 1: Locate the install script

```bash
INSTALL_SCRIPT=$(find "${HOME}/.claude" "${HOME}/others" \
    -name install.sh -path "*/squirrel/companions/macos-reminders/*" \
    2>/dev/null | head -1)
[ -z "$INSTALL_SCRIPT" ] && echo "❌ install.sh not found. Check the plugin installation." && exit 1
```

<!-- @spec INT-011 -->
## Step 2: Run the uninstall

```bash
bash "$INSTALL_SCRIPT" --uninstall
```

Show the full output to the user.

If the exit code is != 0, show the error and suggest checking whether the daemon was installed with `/sq-reminders-install`.
