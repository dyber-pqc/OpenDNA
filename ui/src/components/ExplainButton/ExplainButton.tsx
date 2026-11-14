import { useState, useRef, useEffect } from "react";
import "./ExplainButton.css";

interface ExplainButtonProps {
  context: string;
  prompt?: string;
  label?: string;
  title?: string;
  className?: string;
}

const API_BASE = "http://localhost:8765";

export default function ExplainButton({
  context,
  prompt,
  label,
  title,
  className,
}: ExplainButtonProps) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const run = async () => {
    setOpen(true);
    setText("");
    setError(null);
    setLoading(true);
    const ctrl = new AbortController();
    abortRef.current?.abort();
    abortRef.current = ctrl;
    try {
      const sessionId = `explain-${Math.random().toString(36).slice(2)}`;
      const message = `${prompt || "Explain this concisely:"}\n\n${context}`;
      const res = await fetch(`${API_BASE}/v1/llm/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: ctrl.signal,
        body: JSON.stringify({
          session_id: sessionId,
          message,
          system:
            "You are a protein science expert. Give concise, accurate, jargon-aware explanations. Keep responses under 120 words.",
        }),
      });
      if (!res.ok || !res.body) {
        throw new Error(`HTTP ${res.status}`);
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        setText((t) => t + chunk);
      }
    } catch (e: any) {
      if (e.name !== "AbortError") {
        setError(e.message || String(e));
      }
    } finally {
      setLoading(false);
    }
  };

  const close = () => {
    abortRef.current?.abort();
    setOpen(false);
  };

  return (
    <span className={`explain-btn-wrap ${className || ""}`}>
      <button
        type="button"
        className="explain-btn"
        title={title || "Explain with AI"}
        onClick={(e) => {
          e.stopPropagation();
          run();
        }}
      >
        <span className="explain-spark">✨</span>
        {label && <span className="explain-label">{label}</span>}
      </button>
      {open && (
        <div className="explain-pop" onClick={(e) => e.stopPropagation()}>
          <div className="explain-pop-head">
            <span className="explain-pop-title">✨ AI Explanation</span>
            <button
              className="explain-pop-close"
              onClick={close}
              title="Close"
            >
              ×
            </button>
          </div>
          <div className="explain-pop-body">
            {error ? (
              <div className="explain-pop-error">Error: {error}</div>
            ) : text ? (
              <div className="explain-pop-text">{text}</div>
            ) : loading ? (
              <div className="explain-pop-loading">Thinking…</div>
            ) : (
              <div className="explain-pop-loading">…</div>
            )}
            {loading && text && <span className="explain-pop-cursor">▍</span>}
          </div>
        </div>
      )}
    </span>
  );
}
