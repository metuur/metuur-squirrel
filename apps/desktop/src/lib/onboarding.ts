// First-run onboarding flag, persisted via tauri-plugin-store.
// Shared by the App.tsx gate (read) and OnboardingWizard (write) so both agree
// on the same store file + key. See docs/ears/in-app-vault-onboarding.md R-1.x.

import { load } from "@tauri-apps/plugin-store";

const STORE_FILE = "onboarding.json";
const DONE_KEY = "done";

/** True only when onboarding has been explicitly completed.
 *  R-1.6: if the flag cannot be read (no store / corrupt / non-Tauri context),
 *  treat onboarding as NOT done so the wizard is shown — never skip setup. */
export async function isOnboardingDone(): Promise<boolean> {
  try {
    const store = await load(STORE_FILE);
    return (await store.get<boolean>(DONE_KEY)) === true;
  } catch {
    return false;
  }
}

/** R-1.4: mark onboarding complete and persist it. */
export async function markOnboardingDone(): Promise<void> {
  const store = await load(STORE_FILE);
  await store.set(DONE_KEY, true);
  await store.save();
}
