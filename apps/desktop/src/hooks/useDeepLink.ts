import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

interface DeepLinkPayload {
  projectId: string;
  taskId: string | null;
}

export interface DeepLinkTarget {
  projectId: string;
  taskId: string | null;
  /** Monotonically increasing; bumped on every event, even for repeated payloads. */
  key: number;
}

export function useDeepLink(): DeepLinkTarget | null {
  const [target, setTarget] = useState<DeepLinkTarget | null>(null);
  const keyRef = useRef(0);

  useEffect(() => {
    let unlisten: (() => void) | null = null;
    let cancelled = false;

    // Drain any URL that arrived before this listener registered (cold launch).
    invoke<DeepLinkPayload | null>("drain_pending_deep_link").then((pending) => {
      if (pending && !cancelled) {
        keyRef.current += 1;
        setTarget({ projectId: pending.projectId, taskId: pending.taskId, key: keyRef.current });
      }
    });

    listen<DeepLinkPayload>("deep-link://focus-project", (event) => {
      keyRef.current += 1;
      setTarget({
        projectId: event.payload.projectId,
        taskId: event.payload.taskId,
        key: keyRef.current,
      });
    }).then((fn) => {
      if (cancelled) {
        fn();
      } else {
        unlisten = fn;
      }
    });

    return () => {
      cancelled = true;
      if (unlisten) unlisten();
    };
  }, []);

  return target;
}
