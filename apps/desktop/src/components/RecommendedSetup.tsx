// Recommended OS-setup card: notification permission + launch-at-login.
// Shared by the first-run OnboardingWizard (done step) and the post-update
// SetupNudge. Self-contained: probes both on mount and degrades to rendering
// nothing outside a Tauri host (tests / plain-browser dev).

import { useEffect, useState } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import { isPermissionGranted, requestPermission } from "@tauri-apps/plugin-notification";
import {
  isEnabled as autostartIsEnabled,
  enable as autostartEnable,
  disable as autostartDisable,
} from "@tauri-apps/plugin-autostart";

// Deep link to the macOS Notifications settings pane (Ventura+; older versions
// fall back to opening System Settings). The OS can't deep-link to a specific
// app row, so the on-screen copy also spells out the path.
const NOTIFICATIONS_SETTINGS_URL =
  "x-apple.systempreferences:com.apple.Notifications-Settings.extension";

export function RecommendedSetup() {
  // null = unknown / not a Tauri host → that control is hidden.
  const [notifGranted, setNotifGranted] = useState<boolean | null>(null);
  const [autostartReady, setAutostartReady] = useState(false);
  const [autostartOn, setAutostartOn] = useState(false);

  useEffect(() => {
    let alive = true;
    isPermissionGranted()
      .then((g) => alive && setNotifGranted(g))
      .catch(() => alive && setNotifGranted(null));
    autostartIsEnabled()
      .then((on) => {
        if (!alive) return;
        setAutostartReady(true);
        setAutostartOn(on);
      })
      .catch(() => alive && setAutostartReady(false));
    return () => {
      alive = false;
    };
  }, []);

  const enableNotifications = async () => {
    try {
      const res = await requestPermission();
      if (res === "granted") setNotifGranted(true);
      // Already decided (denied/default): the prompt won't reappear, so the only
      // way to enable is System Settings — take the user straight there.
      else await openUrl(NOTIFICATIONS_SETTINGS_URL);
    } catch {
      // Non-Tauri host — nothing to do.
    }
  };

  const toggleAutostart = async (on: boolean) => {
    try {
      if (on) await autostartEnable();
      else await autostartDisable();
      setAutostartOn(on);
    } catch {
      // Leave the checkbox as-is if the plugin call fails.
    }
  };

  // Nothing to surface (non-Tauri host, or both probes failed).
  if (notifGranted === null && !autostartReady) return null;

  return (
    <div className="flex flex-col gap-3 rounded border border-hairline bg-surface-2 px-3 py-3">
      <span className="title text-[13px]">Recommended setup</span>

      {notifGranted === true && <span className="text-[13px]">✓ Notifications enabled</span>}
      {notifGranted === false && (
        <div className="flex flex-col gap-2 text-[13px]">
          <span>
            ⚠ Notifications are off — Squirrel’s reminders won’t appear until you
            allow them.
          </span>
          <div className="flex gap-2">
            <button type="button" className="btn" onClick={() => void enableNotifications()}>
              Turn on notifications
            </button>
            <button
              type="button"
              className="btn"
              onClick={() => void openUrl(NOTIFICATIONS_SETTINGS_URL).catch(() => {})}
            >
              Open System Settings
            </button>
          </div>
          <span className="text-ink-4 text-[11px]">
            System Settings → Notifications → Squirrel → Allow Notifications
            (style: Banners or Alerts).
          </span>
        </div>
      )}

      {autostartReady && (
        <label className="flex items-center gap-2 text-[13px]">
          <input
            type="checkbox"
            checked={autostartOn}
            onChange={(e) => void toggleAutostart(e.target.checked)}
          />
          <span>Launch Squirrel at login</span>
        </label>
      )}
    </div>
  );
}
