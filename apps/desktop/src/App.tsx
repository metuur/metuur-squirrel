// Phase 2 popup root. Partial mount — banner + 3 widgets.
// CaptureButton (story 3.1) and OpenWebUIButton (story 4.2) land separately.

import { useBackend } from "./hooks/useBackend";
import { useHome } from "./hooks/useHome";
import { BackendStatusBanner } from "./components/BackendStatusBanner";
import { FocusWidget } from "./components/FocusWidget";
import { DeadlinesWidget } from "./components/DeadlinesWidget";
import { ParakeetWidget } from "./components/ParakeetWidget";

export default function App() {
  const status = useBackend();
  // R-1.6: re-fetch widgets each time backend transitions to online.
  // lastOnlineAt changes on every successful probe; widgets re-render
  // on that, but only re-fetch when the key actually changes.
  const triggerKey = status.lastOnlineAt ?? 0;
  const home = useHome(triggerKey);

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#0f172a",
        color: "#f1f5f9",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <BackendStatusBanner status={status} />
      <FocusWidget home={home} online={status.online} />
      <DeadlinesWidget home={home} online={status.online} />
      <ParakeetWidget triggerKey={triggerKey} online={status.online} />
    </main>
  );
}
