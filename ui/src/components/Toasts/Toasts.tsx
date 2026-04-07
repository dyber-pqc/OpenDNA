import type { Toast } from "../../hooks/useToasts";
import "./Toasts.css";

interface ToastsProps {
  toasts: Toast[];
  onRemove: (id: string) => void;
}

const ICONS: Record<Toast["kind"], string> = {
  success: "✓",
  error: "✕",
  info: "ⓘ",
  warning: "⚠",
};

export default function Toasts({ toasts, onRemove }: ToastsProps) {
  return (
    <div className="toasts-container">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.kind}`}>
          <span className="toast-icon">{ICONS[t.kind]}</span>
          <div className="toast-body">
            {t.title && <div className="toast-title">{t.title}</div>}
            <div className="toast-message">{t.message}</div>
          </div>
          <button className="toast-close" onClick={() => onRemove(t.id)}>
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
