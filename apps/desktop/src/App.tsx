// Phase 2 popup root. Full mount per EARS R-2.1:
// BackendStatusBanner, FocusWidget, DeadlinesWidget, ParakeetWidget,
// CaptureButton, OpenWebUIButton.

import { useBackend } from "./hooks/useBackend";
import { useHome } from "./hooks/useHome";
import { BackendStatusBanner } from "./components/BackendStatusBanner";
import { FocusWidget } from "./components/FocusWidget";
import { DeadlinesWidget } from "./components/DeadlinesWidget";
import { ParakeetWidget } from "./components/ParakeetWidget";
import { CaptureButton } from "./components/CaptureButton";
import { OpenWebUIButton } from "./components/OpenWebUIButton";

export default function App() {
  const status = useBackend();
  // R-1.6: re-fetch widgets each time backend transitions to online.
  // lastOnlineAt changes on every successful probe; useHome only re-fetches
  // when the key passed to it actually changes.
  const triggerKey = status.lastOnlineAt ?? 0;
  const home = useHome(triggerKey);

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#0f172a",
        color: "#f1f5f9",
        fontFamily: "system-ui, sans-serif",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <BackendStatusBanner status={status} />
      <FocusWidget home={home} online={status.online} />
      <DeadlinesWidget home={home} online={status.online} />
      <ParakeetWidget triggerKey={triggerKey} online={status.online} />
      <div style={{ flex: 1 }} />
      <CaptureButton online={status.online} />
      <OpenWebUIButton />
    </main>
  );
}
