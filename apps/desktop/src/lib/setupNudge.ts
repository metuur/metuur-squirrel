// Post-install/update setup nudge, persisted via tauri-plugin-store.
// Tracks the app version the user last acknowledged the recommended-setup card
// for, so the card re-appears once after each install or update (version change)
// without nagging on every launch within the same version.

import { load } from "@tauri-apps/plugin-store";
import { getVersion } from "@tauri-apps/api/app";

const STORE_FILE = "setup.json";
const SEEN_KEY = "seenVersion";

/** True when the running version differs from the last acknowledged one — i.e.
 *  a fresh install (nothing stored) or an update. Any failure (non-Tauri host,
 *  no store) returns false so we never nag in dev/tests. */
export async function shouldShowSetupNudge(): Promise<boolean> {
  try {
    const [version, store] = await Promise.all([getVersion(), load(STORE_FILE)]);
    const seen = await store.get<string>(SEEN_KEY);
    return seen !== version;
  } catch {
    return false;
  }
}

/** Record the running version as acknowledged so the nudge stays hidden until
 *  the next update. Also called when onboarding completes (first run). */
export async function ackSetupNudge(): Promise<void> {
  try {
    const [version, store] = await Promise.all([getVersion(), load(STORE_FILE)]);
    await store.set(SEEN_KEY, version);
    await store.save();
  } catch {
    // Non-Tauri host — nothing to persist.
  }
}
