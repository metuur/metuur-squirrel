# Global Shortcut & Window Activation — EARS Specifications

## Unit 1: Global Shortcut Registration

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | THE SYSTEM SHALL register `CommandOrControl+Shift+S` as a system-wide global shortcut on desktop platforms at application startup. |
| R-1.2 | WHEN the global shortcut registration fails, THE SYSTEM SHALL log a warning and continue startup without crashing. |
| R-1.3 | THE SYSTEM SHALL unregister the global shortcut automatically when the application process exits. |

## Unit 2: Shortcut-Triggered Window Show

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | WHEN the user presses `Cmd+Shift+S` (macOS) while the Squirrel window is hidden, THE SYSTEM SHALL show the main window and bring it to the foreground. |
| R-2.2 | WHEN the user presses `Cmd+Shift+S` (macOS) while the Squirrel window is already visible, THE SYSTEM SHALL set focus to the window (no-op on visibility). |
| R-2.3 | WHEN the shortcut triggers a window show, THE SYSTEM SHALL set the macOS activation policy to `Regular` so the app appears in Cmd+Tab and the Dock. |

## Unit 3: Window Hide & Background Mode

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | WHEN the user closes the main window (red button or Cmd+W), THE SYSTEM SHALL hide the window without quitting the process. |
| R-3.2 | WHEN the main window is hidden, THE SYSTEM SHALL set the macOS activation policy to `Accessory` so the app is absent from Cmd+Tab and the Dock. |
| R-3.3 | WHILE the main window is hidden, THE SYSTEM SHALL continue tray icon polling and remain fully operational in the background. |

## Unit 4: Tray Menu Consistency

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | WHEN the user selects "Open Squirrel" from the tray menu, THE SYSTEM SHALL show and focus the main window using the same code path as the global shortcut (R-2.1, R-2.3). |
| R-4.2 | THE SYSTEM SHALL reset the tray icon to Normal state whenever the main window is shown, whether via shortcut or tray menu. |
