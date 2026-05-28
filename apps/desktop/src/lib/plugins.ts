// Plugin binding smoke imports.
//
// This file exists to prove the four Tauri plugin JS bindings resolve at
// type-check time. It is imported nowhere; tsc walks all `.ts/.tsx` files in
// the project and will surface a missing-module error if any binding becomes
// uninstalled or moved upstream.
//
// Wired in Story 0.2; the bindings will be used directly from feature code
// (notifications, store, autostart) starting in Unit 4 / Unit 6.

import { isPermissionGranted } from "@tauri-apps/plugin-notification";
import { load } from "@tauri-apps/plugin-store";
import { isEnabled } from "@tauri-apps/plugin-autostart";

export const __pluginBindings = {
  notification: { isPermissionGranted },
  store: { load },
  autostart: { isEnabled },
};
