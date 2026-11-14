import { useEffect, useState, useCallback } from "react";
import "./Competitions.css";

const API_BASE = "http://localhost:8765";

interface Competition {
  id: string;
  title: string;
  description: string;
  starts_at: string;
  ends_at: string;
  scoring_metric: string;
  prize: string;
}

interface Entry {
  entry_id: number;
  user_id: string;
  sequence: string;
  score: number;
  rank: number;
}

interface Props {
  onClose: () => void;
  defaultSequence?: string;
}

export default function Competitions({ onClose, defaultSequence = "" }: Props) {
  const [comps, setComps] = useState<Competition[]>([]);
  const [leaderboards, setLeaderboards] = useState<Record<string, Entry[]>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadBoard = useCallback(async (id: string) => {
    try {
      const r = await fetch(`${API_BASE}/v1/competitions/${id}/leaderboard`);
      const j = await r.json();
      setLeaderboards((p) => ({ ...p, [id]: j.leaderboard || [] }));
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API_BASE}/v1/competitions`);
        const j = await r.json();
        setComps(j.competitions || []);
        for (const c of j.competitions || []) loadBoard(c.id);
      } catch (e: any) {
        setError(e.message);
      }
    })();
  }, [loadBoard]);

  const submit = async (comp: Competition) => {
    const seq =
      window.prompt(`Submit your sequence for "${comp.title}":`, defaultSequence) || "";
    if (!seq.trim()) return;
    const user = window.prompt("Your display name:", "anon") || "anon";
    setBusy(true);
    try {
      const r = await fetch(
        `${API_BASE}/v1/competitions/${comp.id}/submit`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: user, sequence: seq }),
        }
      );
      if (!r.ok) throw new Error(`Submit failed: ${r.status}`);
      const j = await r.json();
      await loadBoard(comp.id);
      alert(`Submitted! Score: ${j.score.toFixed(3)}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="competitions-panel" onClick={(e) => e.stopPropagation()}>
        <div className="competitions-header">
          <h2>🏆 Competitions</h2>
          <button onClick={onClose}>×</button>
        </div>
        {error && <div className="competitions-error">{error}</div>}
        <div className="competitions-grid">
          {comps.map((c) => (
            <div key={c.id} className="competition-card">
              <h3>{c.title}</h3>
              <p className="comp-desc">{c.description}</p>
              <div className="comp-meta">
                <span>Metric: <strong>{c.scoring_metric}</strong></span>
                <span>Prize: <strong>{c.prize}</strong></span>
              </div>
              <button
                className="submit-btn"
                disabled={busy}
                onClick={() => submit(c)}
              >
                Submit your design
              </button>
              <div className="leaderboard">
                <h4>Leaderboard</h4>
                {(leaderboards[c.id] || []).length === 0 && (
                  <div className="lb-empty">No entries yet — be first!</div>
                )}
                {(leaderboards[c.id] || []).slice(0, 5).map((e) => (
                  <div key={e.entry_id} className="lb-row">
                    <span className="lb-rank">#{e.rank}</span>
                    <span className="lb-user">{e.user_id}</span>
                    <span className="lb-score">{e.score.toFixed(3)}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
