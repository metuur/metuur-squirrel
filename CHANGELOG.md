# Changelog

All notable, user-facing changes to Squirrel are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

Entries describe what changed for **you** — the person using the menu-bar app,
the CLI, or the Web UI — not code-level changes. Generated and maintained with
the `squirrel:changelog` skill.

## [Unreleased]

_Nothing yet._

## [0.7.26] — 2026-06-11

### 🖥 Desktop app
- Menu-bar notifications are more reliable and carry Squirrel's branded sender
  identity and icon.
- Focus check-in/out tracks elapsed time with a live HH:MM timer.
- Reminder banners that occasionally failed to appear now emit reliably.
- **Security:** runtime tokens are no longer written to log files.

### ⌨️ CLI
- Reminders now fire at the correct local time across timezones.
- Vault paths containing spaces install correctly, and the installer warns you
  about unsigned binaries.
- Note writes are atomic and safer; skipped files are now logged.
- Import an existing Obsidian vault into Squirrel format with `migrate-vault`.

### 🌐 Web UI
- **Added:** an in-app Guide covering the desktop app and the menu-bar icon,
  now with an FAQ section.
- Slow background responses can no longer overwrite newer data on screen.
- Reminder errors are surfaced instead of failing silently; external links are
  protocol-filtered for safety.
- **Security:** note saves are locked against races and output is fully
  HTML-escaped.

### ✨ General
- Onboarding now shows a real `migrate-vault` example on the final step.

[Unreleased]: https://github.com/metuur/metuur-squirrel/compare/v0.7.26...HEAD
[0.7.26]: https://github.com/metuur/metuur-squirrel/releases/tag/v0.7.26
