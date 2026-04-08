import { useEffect, useState } from "react";
import "./OnboardingTour.css";

interface Step {
  title: string;
  body: string;
  emoji: string;
}

const STEPS: Step[] = [
  { emoji: "👋", title: "Welcome to OpenDNA", body: "The People's Protein Engineering Platform. This 60-second tour shows you the big features." },
  { emoji: "🧬", title: "Score a protein instantly", body: "Paste a sequence in the sidebar and click 'Score' — no model downloads needed." },
  { emoji: "📦", title: "Install heavy models on demand", body: "Open the Component Manager (📦 Components) to install ESMFold, Boltz, DiffDock, xTB, and more." },
  { emoji: "🧩", title: "Build visual workflows", body: "Click 🧩 Workflow to drag and drop fold → design → analyze pipelines." },
  { emoji: "🤝", title: "Collaborate in real time", body: "🤝 Collab gives you shared notes that sync keystroke-by-keystroke via Yjs CRDT." },
  { emoji: "🛡️", title: "Post-quantum by default", body: "Authentication uses ML-KEM-768 + ML-DSA-65 when liboqs is installed. No tracking, no telemetry." },
  { emoji: "📚", title: "Learn as you go", body: "Open Academy to work through 7 levels, badges, and daily challenges." },
];

interface Props {
  onFinish: () => void;
}

export default function OnboardingTour({ onFinish }: Props) {
  const [i, setI] = useState(0);
  const step = STEPS[i];
  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if (e.key === "Escape") onFinish();
      else if (e.key === "ArrowRight") setI(x => Math.min(STEPS.length - 1, x + 1));
      else if (e.key === "ArrowLeft") setI(x => Math.max(0, x - 1));
    };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onFinish]);
  return (
    <div className="ot-backdrop" onClick={onFinish}>
      <div className="ot-card" onClick={e => e.stopPropagation()}>
        <div className="ot-emoji">{step.emoji}</div>
        <h2>{step.title}</h2>
        <p>{step.body}</p>
        <div className="ot-dots">
          {STEPS.map((_, k) => (
            <span key={k} className={`ot-dot ${k === i ? "active" : ""}`} onClick={() => setI(k)} />
          ))}
        </div>
        <div className="ot-actions">
          <button onClick={() => setI(x => Math.max(0, x - 1))} disabled={i === 0}>Back</button>
          {i < STEPS.length - 1 ? (
            <button className="primary" onClick={() => setI(x => x + 1)}>Next →</button>
          ) : (
            <button className="primary" onClick={onFinish}>Start exploring</button>
          )}
        </div>
        <button className="ot-skip" onClick={onFinish}>Skip tour</button>
      </div>
    </div>
  );
}
