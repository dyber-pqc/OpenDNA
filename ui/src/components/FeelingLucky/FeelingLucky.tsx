import { useEffect, useRef, useState } from "react";
import "./FeelingLucky.css";

const API_BASE = "http://localhost:8765";
const WS_BASE = API_BASE.replace(/^http/, "ws");

interface Props {
  initialSequence: string;
  userId?: string;
  onClose: () => void;
}

interface ProgressEvt {
  stage?: string;
  progress?: number;
  message?: string;
}

export default function FeelingLucky({ initialSequence, userId, onClose }: Props) {
  const [sequence, setSequence] = useState(initialSequence || "");
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("idle");
  const [progress, setProgress] = useState(0);
  const [log, setLog] = useState<ProgressEvt[]>([]);
  const [result, setResult] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    return () => {
      try {
        wsRef.current?.close();
      } catch {}
    };
  }, []);

  const start = async () => {
    setErr(null);
    setResult(null);
    setLog([]);
    setProgress(0);
    const seq = sequence.trim().toUpperCase();
    if (!seq) {
      setErr("Sequence is required");
      return;
    }
    try {
      setStatus("submitting");
      const r = await fetch(`${API_BASE}/v1/feeling_lucky`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sequence: seq, user_id: userId }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      const id = data.job_id;
      setJobId(id);
      setStatus("running");

      const ws = new WebSocket(`${WS_BASE}/v1/ws/jobs/${id}`);
      wsRef.current = ws;
      ws.onmessage = (m) => {
        try {
          const evt = JSON.parse(m.data);
          if (evt.event === "progress") {
            setProgress(Number(evt.progress) || 0);
            setLog((l) => [...l.slice(-200), { stage: evt.stage, progress: evt.progress, message: evt.message }]);
          } else if (evt.event === "snapshot" || evt.event === "started") {
            if (evt.job?.progress) setProgress(evt.job.progress);
          } else if (evt.event === "final" || evt.event === "finished") {
            const job = evt.job || {};
            setStatus(job.status || "completed");
            setProgress(1);
            if (job.status === "failed") {
              setErr(job.error || "Job failed");
            } else {
              setResult(job.result || null);
            }
            try {
              ws.close();
            } catch {}
          }
        } catch {}
      };
      ws.onerror = () => setErr("WebSocket error");
    } catch (e: any) {
      setErr(String(e?.message || e));
      setStatus("error");
    }
  };

  return (
    <div className="lucky-backdrop" onClick={onClose}>
      <div className="lucky-modal" onClick={(e) => e.stopPropagation()}>
        <header className="lucky-header">
          <h2>🍀 I'm Feeling Lucky</h2>
          <button className="lucky-close" onClick={onClose} title="Close">✕</button>
        </header>
        <p className="lucky-sub">
          One click runs the full pipeline: evaluate → fold → analyze → design 10 →
          score → MD stability → cost → LLM summary.
        </p>

        {!jobId && (
          <div className="lucky-input-row">
            <textarea
              className="lucky-textarea"
              rows={3}
              placeholder="Paste or type an amino acid sequence (ACDEFGHIKLMNPQRSTVWY)..."
              value={sequence}
              onChange={(e) => setSequence(e.target.value)}
            />
            <button className="lucky-go" onClick={start} disabled={!sequence.trim()}>
              🍀 Go
            </button>
          </div>
        )}

        {jobId && (
          <div className="lucky-progress">
            <div className="lucky-bar">
              <div className="lucky-bar-fill" style={{ width: `${Math.round(progress * 100)}%` }} />
            </div>
            <div className="lucky-status">
              Status: <b>{status}</b> &middot; {Math.round(progress * 100)}% &middot; job <code>{jobId}</code>
            </div>
            <div className="lucky-log">
              {log.slice(-12).map((l, i) => (
                <div key={i} className="lucky-log-line">
                  <span className="lucky-log-stage">{l.stage}</span>
                  {l.message && <span className="lucky-log-msg"> — {l.message}</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {err && <div className="lucky-err">Error: {err}</div>}

        {result && (
          <div className="lucky-result">
            <h3>Result</h3>

            <section className="lucky-section">
              <h4>Quality score</h4>
              <pre>{JSON.stringify(result.score, null, 2)}</pre>
            </section>

            <section className="lucky-section">
              <h4>Folded structure</h4>
              <div className="lucky-muted">
                {result.pdb ? `${String(result.pdb).length} chars of PDB data` : "(not available)"}
              </div>
            </section>

            <section className="lucky-section">
              <h4>Analysis metrics</h4>
              <pre>{JSON.stringify(result.analysis, null, 2)}</pre>
            </section>

            <section className="lucky-section">
              <h4>Top 3 candidates</h4>
              <table className="lucky-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Score</th>
                    <th>Sequence</th>
                  </tr>
                </thead>
                <tbody>
                  {(result.top_candidates || []).map((c: any, i: number) => (
                    <tr key={i}>
                      <td>{i + 1}</td>
                      <td>{Number(c.overall_score || c.score || 0).toFixed(3)}</td>
                      <td className="lucky-seq-cell">{c.sequence}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section className="lucky-section">
              <h4>MD stability (100 ps, implicit)</h4>
              <pre>{JSON.stringify(result.md_summary, null, 2)}</pre>
            </section>

            <section className="lucky-section">
              <h4>Synthesis cost</h4>
              <pre>{JSON.stringify(result.cost, null, 2)}</pre>
            </section>

            <section className="lucky-section">
              <h4>LLM summary</h4>
              <div className="lucky-llm">{result.llm_summary || "(unavailable)"}</div>
            </section>

            <section className="lucky-section">
              <h4>Provenance</h4>
              <div className="lucky-muted">
                {result.provenance_node_ids?.length || 0} nodes &middot; notebook entry{" "}
                <code>{result.notebook_entry_id || "(none)"}</code>
              </div>
            </section>

            {result.errors && Object.keys(result.errors).length > 0 && (
              <section className="lucky-section lucky-errs">
                <h4>Step errors</h4>
                <pre>{JSON.stringify(result.errors, null, 2)}</pre>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
