import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';

interface ToastMsg { id: number; text: string; kind: 'info' | 'success' | 'error' }
interface Ctx { show: (text: string, kind?: ToastMsg['kind']) => void }

const Toast = createContext<Ctx>({ show: () => {} });
export const useToast = () => useContext(Toast);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [msgs, setMsgs] = useState<ToastMsg[]>([]);
  const seq = useRef(0);

  const show = useCallback((text: string, kind: ToastMsg['kind'] = 'info') => {
    const id = ++seq.current;
    setMsgs((cur) => [...cur, { id, text, kind }]);
    setTimeout(() => setMsgs((cur) => cur.filter((m) => m.id !== id)), 3000);
  }, []);

  return (
    <Toast.Provider value={{ show }}>
      {children}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[300] flex flex-col gap-2 items-center pointer-events-none">
        {msgs.map((m) => (
          <div
            key={m.id}
            className={
              'sq-pop pointer-events-auto px-4 py-2.5 rounded-full shadow-xl text-sm font-medium border inline-flex items-center gap-2 ' +
              (m.kind === 'error'
                ? 'bg-rose-500 text-white border-rose-600'
                : m.kind === 'success'
                ? 'bg-emerald-500 text-white border-emerald-600'
                : 'bg-slate-900 text-white border-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:border-slate-200')
            }
          >
            <span className="material-icons text-base">
              {m.kind === 'error' ? 'error_outline' : m.kind === 'success' ? 'check_circle' : 'info'}
            </span>
            {m.text}
          </div>
        ))}
      </div>
    </Toast.Provider>
  );
}
