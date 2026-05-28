// Phase 2 minimal toast primitive. Single-toast queue, 3s auto-dismiss,
// manual dismiss button. Used by CaptureButton on save success (R-3.5).
// Provider mounts once at the App root; consumers call useToast().

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
          style={{
            position: "fixed",
            bottom: 16,
            left: "50%",
            transform: "translateX(-50%)",
            background: "#1f2937",
            color: "#f1f5f9",
            padding: "8px 14px",
            borderRadius: 6,
            fontSize: 13,
            fontFamily: "system-ui, sans-serif",
            display: "flex",
            alignItems: "center",
            gap: 12,
            boxShadow: "0 4px 12px rgba(0,0,0,0.4)",
            zIndex: 100,
          }}
        >
          <span>{toast.message}</span>
          <button
            type="button"
            onClick={() => setToast(null)}
            style={{
              background: "transparent",
              border: "none",
              color: "#94a3b8",
              cursor: "pointer",
              fontSize: 16,
              padding: 0,
              lineHeight: 1,
            }}
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
