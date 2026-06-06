// Gentle credit + shortcut strip pinned under the action footer. Surfaces the
// app version (read from the Tauri config via getVersion) and the two global
// hotkeys so they stay discoverable without opening the How-to guide.

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { getVersion } from "@tauri-apps/api/app";
import { openUrl } from "@tauri-apps/plugin-opener";

const COFFEE_URL = "https://buymeacoffee.com/javierhbr";

function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd
      className="tabular"
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: "10px",
        lineHeight: 1.1,
        padding: "2px 5px",
        borderRadius: 5,
        color: "var(--color-ink-3)",
        background: "var(--color-surface)",
        border: "1px solid var(--color-hairline)",
      }}
    >
      {children}
    </kbd>
  );
}

export function AppCredit() {
  const [version, setVersion] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    getVersion()
      .then((v) => {
        if (alive) setVersion(v);
      })
      .catch(() => {
        // Non-Tauri host (e.g. plain browser dev) or denied — just omit it.
      });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div
      className="flex items-center justify-between gap-3 flex-wrap px-4 py-1.5 bg-surface-2 border-t border-hairline-2 shrink-0"
      style={{ fontSize: "10.5px", color: "var(--color-ink-4)" }}
    >
      <span className="flex items-center gap-2 min-w-0" style={{ letterSpacing: "-0.005em" }}>
        <span className="truncate">
          © 2026 Squirrel {version ? ` v${version}` : ""}. Made with ❤️ by @javierhbr.
        </span>
        <button
          type="button"
          onClick={() => void openUrl(COFFEE_URL)}
          title="Buy me a coffee"
          className="shrink-0 hover:underline"
          style={{ color: "var(--color-accent)" }}
        >
          ☕ Buy me a coffee
        </button>
      </span>
      <span className="flex items-center gap-2.5 shrink-0">
        <span
          className="flex items-center gap-1"
          title="Open Squirrel from anywhere"
        >
          <span className="eyebrow" style={{ fontSize: "8.5px" }}>
            Open
          </span>
          <Kbd>⌃⌘S</Kbd>
        </span>
        <span
          className="flex items-center gap-1"
          title="Capture a quick task from anywhere"
        >
          <span className="eyebrow" style={{ fontSize: "8.5px" }}>
            Quick task
          </span>
          <Kbd>⌃⌘Q</Kbd>
        </span>
      </span>
    </div>
  );
}
