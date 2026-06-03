// Runtime Trust Handshake refusal banner (Unit 6, R-6.1/R-6.2).
//
// When the Tauri backend supervisor refuses to adopt the process already bound
// to port 3939, it emits a typed `handshake-refused` event. This component
// listens for it and renders a window-blocking overlay above ALL routed
// content: the rest of the dashboard is visually inaccessible until the user
// quits Squirrel (the primary recovery action) and resolves the conflict.
//
// The refusal is terminal for the lifetime of the process (LLD D5) — there is
// no "dismiss"; the only ways out are Quit or relaunching after fixing the
// underlying cause. The tray "Why?" item re-emits the event so the banner
// shows even if this listener mounted after the original startup emit.

import { useEffect, useState } from "react";
import { listen } from "@tauri-apps/api/event";

// Mirrors the Rust `handshake_refusal_cause` strings. Any unknown value falls
// back to the generic message so a future cause never renders an empty banner.
export type RefusalCause =
  | "DevModeDetected"
  | "UnknownProcess"
  | "NotResponding"
  | "LaunchdTokenInvalid";

interface RefusalPayload {
  cause: RefusalCause;
}

function isTauriContext(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

// Inline shell-command chip — copy-pasteable, monospace.
function Cmd({ children }: { children: string }) {
  return (
    <code className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[12px] text-ink-1 select-all">
      {children}
    </code>
  );
}

// Per-cause title + recovery instructions (R-6.3..R-6.6). Single locale.
function CauseBody({ cause }: { cause: RefusalCause }) {
  switch (cause) {
    case "DevModeDetected":
      // R-6.3
      return (
        <div className="space-y-2.5">
          <h3 className="text-[13px] font-semibold text-ink-1">
            A development backend is running
          </h3>
          <p className="text-[13px] leading-relaxed text-ink-2">
            Squirrel found an <strong>unauthenticated</strong> backend on port
            3939 — most likely one you started with <Cmd>make backend-start</Cmd>.
            Squirrel won’t connect to an unauthenticated backend. You can either:
          </p>
          <ul className="list-disc pl-5 text-[13px] leading-relaxed text-ink-2 space-y-1">
            <li>Quit that dev backend, then relaunch Squirrel, or</li>
            <li>Quit Squirrel and keep using the CLI.</li>
          </ul>
        </div>
      );
    case "UnknownProcess":
      // R-6.4
      return (
        <div className="space-y-2.5">
          <h3 className="text-[13px] font-semibold text-ink-1">
            Another program is using port 3939
          </h3>
          <p className="text-[13px] leading-relaxed text-ink-2">
            Squirrel found a program on port 3939 that it can’t verify, so it
            won’t connect. To see what it is, run <Cmd>lsof -i :3939</Cmd> in a
            terminal, then quit that program (or quit Squirrel).
          </p>
        </div>
      );
    case "NotResponding":
      // R-6.5
      return (
        <div className="space-y-2.5">
          <h3 className="text-[13px] font-semibold text-ink-1">
            The backend isn’t responding
          </h3>
          <p className="text-[13px] leading-relaxed text-ink-2">
            The program on port 3939 didn’t answer in time. Wait about 30
            seconds and relaunch Squirrel. If it keeps happening, check{" "}
            <Cmd>~/.squirrel/web-ui.stderr.log</Cmd>.
          </p>
        </div>
      );
    case "LaunchdTokenInvalid":
      // R-6.6
      return (
        <div className="space-y-2.5">
          <h3 className="text-[13px] font-semibold text-ink-1">
            The launch token is invalid
          </h3>
          <p className="text-[13px] leading-relaxed text-ink-2">
            Squirrel’s stored launch token (<Cmd>~/.squirrel/launchd-token</Cmd>)
            is missing, has the wrong permissions, or is malformed. Re-provision
            it by running <Cmd>install.sh --reinstall</Cmd>, then relaunch
            Squirrel.
          </p>
        </div>
      );
    default:
      return (
        <p className="text-[13px] leading-relaxed text-ink-2">
          Squirrel found another program using port 3939 and could not verify
          it, so it won’t connect. Quit Squirrel and resolve the conflict.
        </p>
      );
  }
}

export function HandshakeBanner() {
  const [cause, setCause] = useState<RefusalCause | null>(null);

  useEffect(() => {
    let unlisten: (() => void) | null = null;
    let cancelled = false;

    listen<RefusalPayload>("handshake-refused", (event) => {
      setCause(event.payload.cause);
    }).then((fn) => {
      if (cancelled) fn();
      else unlisten = fn;
    });

    return () => {
      cancelled = true;
      if (unlisten) unlisten();
    };
  }, []);

  if (!cause) return null;

  return (
    <div
      role="alertdialog"
      aria-modal="true"
      aria-label="Squirrel cannot start safely"
      className="fixed inset-0 z-50 flex flex-col items-stretch bg-surface"
    >
      <div
        className="flex items-start gap-3 bg-critical-bg text-critical px-4 py-3"
        style={{ borderBottom: "1px solid rgba(200, 54, 42, 0.25)" }}
      >
        <span aria-hidden className="text-critical text-[18px] leading-none mt-0.5">
          ⚠
        </span>
        <div className="min-w-0">
          <h2 className="text-[14px] font-semibold">Squirrel can’t start safely</h2>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        <CauseBody cause={cause} />
      </div>

      <footer className="shrink-0 flex justify-end px-4 py-3 border-t border-hairline bg-surface-2">
        <button
          type="button"
          onClick={() => setCause(null)}
          className="btn"
          style={{
            padding: "4px 12px",
            fontSize: 12,
          }}
        >
          Close
        </button>
      </footer>
    </div>
  );
}
