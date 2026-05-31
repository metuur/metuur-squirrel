# Installing Squirrel on macOS

Squirrel is currently distributed **unsigned**. That means macOS will block
the first launch with a Gatekeeper warning until you tell it once that you
trust the app. This is a one-time bypass per machine — after that the app
launches normally forever.

## Step 1 — Drag to Applications

1. Open the downloaded `.dmg` file.
2. Drag `Squirrel.app` to your `Applications` folder.
3. Eject the DMG.

## Step 2 — First launch (the "I trust this app" bypass)

When you double-click `Squirrel.app` the first time, macOS will show:

> **"Squirrel" cannot be opened because Apple cannot check it for malicious software.**
> [Move to Trash] [Done]

Click **Done**. Then choose **one** of the two bypass paths below.

### Option A — Right-click → Open  (fastest)

1. In Finder, find `Squirrel.app` in `/Applications`.
2. **Right-click** (or Control-click) the app → **Open**.
3. A new dialog appears with an **Open** button (note: this dialog does NOT
   appear if you double-click — it only appears via the right-click path).
4. Click **Open**.

Squirrel launches. You will never see the warning again on this machine.

### Option B — System Settings → Privacy & Security

1. Open **System Settings** → **Privacy & Security**.
2. Scroll down to the **Security** section.
3. You'll see: *"Squirrel" was blocked from use because it is not from an
   identified developer.*
4. Click **Open Anyway** next to that message.
5. Confirm with your password / Touch ID.

Squirrel launches. You will never see the warning again on this machine.

## Why does this happen?

macOS Gatekeeper requires apps distributed outside the App Store to be
signed by a registered Apple developer and notarized by Apple. Squirrel is
not signed today — see [`docs/release.md`](release.md) for the path to
adding signing in a future release. The bypass above is the standard macOS
mechanism for trusting an unsigned app you obtained from a source you trust.

## Where Squirrel lives after install

| Path | What it is |
|---|---|
| `/Applications/Squirrel.app` | The app itself |
| `~/.squirrel/config.toml` | Your vault configuration |
| `~/.squirrel/squirrel.log` | Tauri-side log (tray, supervisor, deep links) |
| `~/.squirrel/web-ui.log` | Backend HTTP request log (rotates at 10MB) |
| `~/.squirrel/state/squirrel.db` | Notifications database |

If the tray icon goes red and the menu says **"Backend unavailable — see
~/.squirrel/squirrel.log"**, that log file is the first place to look.

## Uninstall

```bash
# Quit Squirrel from the tray menu first, then:
rm -rf /Applications/Squirrel.app
rm -rf ~/.squirrel
```
