import { useCallback, useEffect, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { api, ApiError } from "../api/client";

export interface QuickTaskCaptureHook {
  /** Whether the capture modal is open. */
  open: boolean;
  /** Open the capture modal manually (e.g. from the widget's + button). */
  openCapture: () => void;
  /** Close the modal and clear any error. */
  close: () => void;
  /** Submit captured text. Resolves true on success, false otherwise. */
  submit: (text: string) => Promise<boolean>;
  /** Inline error to show inside the modal (e.g. stack-full message). */
  error: string | null;
  /** True while a create request is in flight. */
  busy: boolean;
}

const STACK_FULL_MESSAGE =
  "Stack is full — complete, delete, or snooze one first.";

/**
 * Capture-from-anywhere hook (R-1.1, R-1.3, R-2.4).
 *
 * Listens for the `quick-task-capture-open` event emitted by the global
 * shortcut (Ctrl+Cmd+Q) and the tray "Add Quick Task" item, and owns the
 * create flow including the hard-cap 409 handling that keeps the modal open.
 */
export function useQuickTaskCapture(onCreated?: () => void): QuickTaskCaptureHook {
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const mountedRef = useRef(true);
  const onCreatedRef = useRef(onCreated);
  onCreatedRef.current = onCreated;

  useEffect(() => {
    mountedRef.current = true;
    let unlisten: (() => void) | null = null;
    let cancelled = false;

    listen("quick-task-capture-open", () => {
      if (!mountedRef.current) return;
      setError(null);
      setOpen(true);
    }).then((fn) => {
      if (cancelled) fn();
      else unlisten = fn;
    });

    return () => {
      mountedRef.current = false;
      cancelled = true;
      if (unlisten) unlisten();
    };
  }, []);

  const openCapture = useCallback(() => {
    setError(null);
    setOpen(true);
  }, []);

  const close = useCallback(() => {
    setError(null);
    setOpen(false);
  }, []);

  const submit = useCallback(async (text: string): Promise<boolean> => {
    const trimmed = text.trim();
    if (!trimmed) {
      // R-1.3: reject empty text client-side, keep the box open.
      setError("Type a quick task first.");
      return false;
    }
    setBusy(true);
    try {
      await api.quickTaskCreate(trimmed);
      if (!mountedRef.current) return true;
      setError(null);
      setOpen(false);
      onCreatedRef.current?.();
      return true;
    } catch (e) {
      if (!mountedRef.current) return false;
      // R-2.4: at the hard cap, stay open and explain how to free a slot.
      if (e instanceof ApiError && e.status === 409) {
        setError(STACK_FULL_MESSAGE);
      } else {
        setError(e instanceof Error ? e.message : "Could not add the quick task.");
      }
      return false;
    } finally {
      if (mountedRef.current) setBusy(false);
    }
  }, []);

  return { open, openCapture, close, submit, error, busy };
}
