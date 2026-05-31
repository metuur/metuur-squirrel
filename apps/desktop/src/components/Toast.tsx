// Phase 2 minimal toast primitive. Dark pill on the warm-paper field,
// with paper-tan text — inverts the main palette for the duration of the
// toast so it reads "system message" rather than "content". R-3.5.

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";

interface ToastState {
  id: number;
  message: string;
}

interface ToastApi {
  show: (message: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<ToastState | null>(null);
  const nextIdRef = useRef(1);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = useCallback((message: string) => {
    const id = nextIdRef.current++;
    setToast({ id, message });
  }, []);

  useEffect(() => {
    if (toast === null) return;
    if (timerRef.current !== null) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setToast(null), 3000);
    return () => {
      if (timerRef.current !== null) clearTimeout(timerRef.current);
    };
  }, [toast]);

  return (
    <ToastContext.Provider value={{ show }}>
      {children}
      {toast && (
        <div
          role="status"
          className="fixed bottom-4 left-1/2 -translate-x-1/2 z-[100] inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium shadow-xl"
          style={{
            background: "var(--color-ink)",
            color: "var(--color-bg)",
            border: "1px solid var(--color-ink-2)",
          }}
        >
          <span>{toast.message}</span>
          <button
            type="button"
            onClick={() => setToast(null)}
            className="leading-none text-base"
            style={{ color: "var(--color-ink-4)" }}
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>
      )}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (ctx === null) throw new Error("useToast must be used inside ToastProvider");
  return ctx;
}
