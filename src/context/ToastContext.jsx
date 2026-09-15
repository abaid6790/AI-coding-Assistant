import { createContext, useCallback, useContext, useState } from "react";
import Toast from "../components/common/Toast.jsx";

const ToastContext = createContext(null);

let idCounter = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback((message, kind = "info", duration = 3500) => {
    const id = ++idCounter;
    setToasts((prev) => [...prev, { id, message, kind }]);
    if (duration) {
      setTimeout(() => dismiss(id), duration);
    }
    return id;
  }, [dismiss]);

  const toast = {
    success: (message) => push(message, "success"),
    error: (message) => push(message, "error", 5000),
    info: (message) => push(message, "info"),
    dismiss,
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <Toast toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
