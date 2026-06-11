import { useCallback, useEffect, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { api } from "../api/client";

export interface PostItCaptureHook {
  /** Whether the capture modal is open. */
  open: boolean;
  /** Open the capture modal manually (e.g. from a button). */
  openCapture: () => void;
  /** Close the modal and clear any error. */
  close: () => void;
  /** Submit captured text + color. Resolves true on success, false otherwise. */
  submit: (text: string, color: string) => Promise<boolean>;
  /** Inline error to show inside the modal. */
  error: string | null;
  /** True while a create request is in flight. */
  busy: boolean;
}

/**
 * Post-it capture hook (R-4.3, R-4.4).
 *
 * Listens for the `post-it-capture-open` event emitted by the tray
 * "Add Post-it" item, and owns the create flow.
 */
export function usePostItCapture(onCreated?: () => void): PostItCaptureHook {
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

    listen("post-it-capture-open", () => {
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

  const submit = useCallback(async (text: string, color: string): Promise<boolean> => {
    const trimmed = text.trim();
    if (!trimmed) {
      setError("Type a Post-it first.");
      return false;
    }
    setBusy(true);
    try {
      await api.postItCreate(trimmed, color);
      if (!mountedRef.current) return true;
      setError(null);
      setOpen(false);
      onCreatedRef.current?.();
      return true;
    } catch (e) {
      if (!mountedRef.current) return false;
      setError(e instanceof Error ? e.message : "Could not save the Post-it.");
      return false;
    } finally {
      if (mountedRef.current) setBusy(false);
    }
  }, []);

  return { open, openCapture, close, submit, error, busy };
}
