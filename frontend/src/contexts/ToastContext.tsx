import { createContext, useContext, useMemo, useState } from "react";

type Toast = { id: number; type: "success" | "error" | "info"; message: string };

const ToastContext = createContext<{ notify: (message: string, type?: Toast["type"]) => void } | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const value = useMemo(
    () => ({
      notify(message: string, type: Toast["type"] = "info") {
        const id = Date.now();
        setToasts((current) => [...current, { id, type, message }]);
        window.setTimeout(() => setToasts((current) => current.filter((toast) => toast.id !== id)), 4200);
      },
    }),
    [],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-region" aria-live="polite">
        {toasts.map((toast) => <div className={`toast ${toast.type}`} key={toast.id}>{toast.message}</div>)}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used within ToastProvider");
  return context;
}
