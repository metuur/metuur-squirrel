# Highlights examples (tone reference)

Good highlights lead with a bold title summarizing the change, then one plain
sentence of outcome. Features first, fixes grouped. No PR numbers, no author
names, no audit IDs. Aim for 3–5 standout points per release.

## Example — feature-led release

- **Focus check-in/out:** Start a focus session from the desktop app and track
  elapsed time with a live HH:MM timer.
- **In-app Guide:** A new Guide page walks you through the desktop app and the
  menu-bar icon — no need to leave the app to learn it.
- **Vault migration:** Import an existing Obsidian vault into Squirrel format
  with a single command.
- **More reliable notifications:** Menu-bar banners now fire consistently and
  carry Squirrel's branded sender identity.

## Example — hardening / stability release

- **Reminders on time, everywhere:** Reminders now fire at the correct local
  time regardless of your timezone.
- **Safer logs:** Runtime tokens are no longer written to log files.
- **Sturdier installs:** Vault paths containing spaces install correctly, and
  the installer warns you about unsigned binaries.
- **No stale data:** Slow background responses can no longer overwrite newer
  data in the Web UI.

## Example — small patch

- **Fixed:** Notification banners that occasionally failed to appear now emit
  reliably.
- **Fixed:** The footer no longer shows an outdated macOS beta note.

## Anti-examples (don't do this)

- ❌ `fix(cli): timezone-aware datetimes across scanners and writers (M6, M7)`
  — raw commit, scope prefix, audit IDs, mechanism not outcome.
- ❌ "Refactored the status aggregator for readability." — no user impact.
- ❌ "Bumped version to 0.7.26." — mechanism, belongs nowhere.
