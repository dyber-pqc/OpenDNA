import { useEffect, useRef, useState, useCallback } from "react";
import "./VoiceControl.css";

const API_BASE = "http://localhost:8765";
const WAKE_WORD = "opendna";

interface Props {
  onClose: () => void;
}

type RecState = "idle" | "listening" | "waking" | "processing";

export default function VoiceControl({ onClose }: Props) {
  const [supported, setSupported] = useState<boolean>(true);
  const [state, setState] = useState<RecState>("idle");
  const [transcript, setTranscript] = useState<string>("");
  const [reply, setReply] = useState<string>("");
  const [alwaysOn, setAlwaysOn] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    const SR: any =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) {
      setSupported(false);
      return;
    }
    const rec = new SR();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = "en-US";
    rec.onresult = (event: any) => {
      let final = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const res = event.results[i];
        if (res.isFinal) final += res[0].transcript;
        else setTranscript(res[0].transcript);
      }
      if (final) {
        const lowered = final.toLowerCase();
        if (alwaysOn) {
          const idx = lowered.indexOf(WAKE_WORD);
          if (idx >= 0) {
            const after = final.slice(idx + WAKE_WORD.length).trim();
            if (after) {
              setTranscript(after);
              sendToBackend(after);
            } else {
              setState("waking");
            }
          } else if (state === "waking") {
            setTranscript(final);
            sendToBackend(final);
          }
        } else {
          setTranscript(final);
          sendToBackend(final);
        }
      }
    };
    rec.onerror = (e: any) => {
      setError(e.error || "speech recognition error");
    };
    rec.onend = () => {
      if (alwaysOn && recognitionRef.current) {
        try { recognitionRef.current.start(); } catch { /* already started */ }
      } else {
        setState("idle");
      }
    };
    recognitionRef.current = rec;
    return () => {
      try { rec.stop(); } catch { /* ignore */ }
      recognitionRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alwaysOn]);

  const sendToBackend = useCallback(async (text: string) => {
    setState("processing");
    setError(null);
    try {
      const r = await fetch(`${API_BASE}/v1/smart_chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message:
            `The user said: ${text}. If this is a protein engineering command, ` +
            "call the appropriate tool. If it's a question, answer it briefly.",
        }),
      });
      if (!r.ok) throw new Error(`smart_chat failed: ${r.status}`);
      const j = await r.json();
      setReply(j.text || JSON.stringify(j));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setState(alwaysOn ? "listening" : "idle");
    }
  }, [alwaysOn]);

  const startListening = () => {
    if (!recognitionRef.current) return;
    setError(null);
    setTranscript("");
    setReply("");
    try {
      recognitionRef.current.start();
      setState(alwaysOn ? "listening" : "listening");
    } catch (e: any) {
      setError(e.message);
    }
  };

  const stopListening = () => {
    if (!recognitionRef.current) return;
    try { recognitionRef.current.stop(); } catch { /* ignore */ }
    setState("idle");
  };

  if (!supported) {
    return (
      <div className="modal-backdrop" onClick={onClose}>
        <div className="voice-panel" onClick={(e) => e.stopPropagation()}>
          <div className="voice-header">
            <h2>🎤 Voice Control</h2>
            <button onClick={onClose}>×</button>
          </div>
          <div className="voice-unsupported">
            Voice not supported in this browser. Try Chrome or Edge for the Web Speech API.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="voice-panel" onClick={(e) => e.stopPropagation()}>
        <div className="voice-header">
          <h2>🎤 Voice Control</h2>
          <button onClick={onClose}>×</button>
        </div>
        <div className="voice-body">
          <button
            className={`mic-btn ${state === "listening" ? "ma-pulse" : ""}`}
            onClick={state === "idle" ? startListening : stopListening}
          >
            {state === "idle" ? "🎤 Start listening" : "⏹ Stop"}
          </button>
          <label className="always-on">
            <input
              type="checkbox"
              checked={alwaysOn}
              onChange={(e) => setAlwaysOn(e.target.checked)}
            />
            Always-on (wake word: "Hey OpenDNA")
          </label>
          <div className="voice-state">State: <strong>{state}</strong></div>
          <div className="voice-transcript">
            <h4>Transcript</h4>
            <div className="transcript-box">{transcript || <em>(nothing yet)</em>}</div>
          </div>
          <div className="voice-reply">
            <h4>Reply</h4>
            <div className="reply-box">{reply || <em>(nothing yet)</em>}</div>
          </div>
          {error && <div className="voice-error">{error}</div>}
        </div>
      </div>
    </div>
  );
}
