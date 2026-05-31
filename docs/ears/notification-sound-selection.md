# Notification Sound Selection — EARS Specifications

## Unit 1: Sound options & persistence

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | THE SYSTEM SHALL support exactly three notification sound options: `Glass` (default), `Funk`, and `Silent`. |
| R-1.2 | THE SYSTEM SHALL persist the user's selected sound in `~/.squirrel/config.toml` under the existing `[notifications]` section as `sound = "<name>"`. |
| R-1.3 | WHEN the `[notifications] sound` key is missing, unreadable, or contains an unknown value, THE SYSTEM SHALL treat the selection as `Glass` and continue without error. |
| R-1.4 | THE SYSTEM SHALL NOT modify the existing `in_app` or `os_popups` keys when persisting a sound change. |

## Unit 2: Playback across notification surfaces

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | WHEN `tray_alerts::update_badge_and_emit` completes with `count > 0` (tray flips to Notification + `squirrel:notif-updated` emitted), THE SYSTEM SHALL play the configured notification sound exactly once via `afplay`. |
| R-2.2 | WHEN the launchd reminders daemon emits a banner via `terminal-notifier` or `osascript`, THE SYSTEM SHALL pass the configured sound name to the underlying notification API, replacing the previously hardcoded `Submarine`. |
| R-2.3 | WHEN the configured sound is `Silent`, THE SYSTEM SHALL produce no audio in response to R-2.1 or R-2.2, while leaving all visual cues (tray icon, banner) unchanged. |
| R-2.4 | WHEN audio playback fails (missing `afplay`, missing sound file, HTTP error fetching settings, or any other error), THE SYSTEM SHALL log a warning and continue notification delivery without blocking or surfacing the failure to the user. |

## Unit 3: Settings UI

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | THE SYSTEM SHALL extend the existing Notifications section of the settings page with a control listing the three sound options, with the current selection visibly indicated. |
| R-3.2 | WHEN the user activates a preview affordance for an option, THE SYSTEM SHALL play that sound immediately via `POST /api/notifications/preview` without modifying the persisted selection. |
| R-3.3 | WHEN the user confirms a new selection, THE SYSTEM SHALL persist it via the existing `POST /api/settings/notifications` endpoint within 1 second of confirmation. |
| R-3.4 | WHEN a new selection has been persisted, THE SYSTEM SHALL use the new sound for the next R-2.1 event without requiring an app restart, and for the next R-2.2 event without requiring a `launchctl unload/load` (the daemon re-reads config on every run). |

## Unit 4: API contract & backward compatibility

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | THE SYSTEM SHALL accept an optional `sound` field in the `POST /api/settings/notifications` JSON payload alongside the existing required `in_app` and `os_popups` fields. |
| R-4.2 | WHEN a `POST /api/settings/notifications` request omits the `sound` field, THE SYSTEM SHALL preserve the previously persisted sound value rather than overwriting it with the default. |
| R-4.3 | WHEN a `POST /api/settings/notifications` request contains a `sound` value not in {`Glass`, `Funk`, `Silent`}, THE SYSTEM SHALL return HTTP 400 without persisting any change. |
| R-4.4 | THE SYSTEM SHALL include the `sound` value in the `notifications` object returned by `GET /api/me`. |
| R-4.5 | THE SYSTEM SHALL accept `POST /api/notifications/preview` with a required `sound` field; values in {`Glass`, `Funk`} trigger an immediate detached `afplay` call, `Silent` returns 200 without playback, and any other value returns HTTP 400. The endpoint SHALL NOT modify `~/.squirrel/config.toml`. |
