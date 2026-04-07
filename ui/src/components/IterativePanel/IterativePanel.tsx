import "./IterativePanel.css";

interface IterationRound {
  round: number;
  sequence: string;
  score: number;
  confidence: number;
  pdb: string;
}

interface IterativePanelProps {
  result: {
    initial_sequence: string;
    final_sequence: string;
    initial_score: number;
    final_score: number;
    improvement: number;
    history: any[];
    rounds: IterationRound[];
  };
  onUseRound: (round: IterationRound) => void;
  onClose: () => void;
}

export default function IterativePanel({ result, onUseRound, onClose }: IterativePanelProps) {
  const improvementPct = result.improvement * 100;
  return (
    <div className="iter-panel">
      <div className="iter-header">
        <h3>Iterative Design Result</h3>
        <button className="iter-close" onClick={onClose}>×</button>
      </div>

      <div className="iter-summary">
        <div className="iter-stat">
          <div className="iter-stat-label">Initial Score</div>
          <div className="iter-stat-value">{(result.initial_score * 100).toFixed(0)}</div>
        </div>
        <div className="iter-arrow">→</div>
        <div className="iter-stat">
          <div className="iter-stat-label">Final Score</div>
          <div className="iter-stat-value">{(result.final_score * 100).toFixed(0)}</div>
        </div>
        <div className="iter-improvement">
          {improvementPct >= 0 ? "+" : ""}{improvementPct.toFixed(1)}%
        </div>
      </div>

      <div className="iter-history">
        <h4>Optimization History</h4>
        <ScoreChart history={result.history} />
      </div>

      <div className="iter-rounds">
        <h4>Best Per Round</h4>
        {result.rounds.map((r) => (
          <div key={r.round} className="iter-round">
            <div className="iter-round-num">#{r.round}</div>
            <div className="iter-round-info">
              <div className="iter-round-seq">{r.sequence.slice(0, 40)}...</div>
              <div className="iter-round-meta">
                Score: {(r.score * 100).toFixed(0)} | Confidence: {(r.confidence * 100).toFixed(0)}%
              </div>
            </div>
            <button className="iter-use" onClick={() => onUseRound(r)}>
              View
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

function ScoreChart({ history }: { history: any[] }) {
  if (!history?.length) return null;
  const w = 300;
  const h = 80;
  const max = Math.max(...history.map((h) => h.best_score));
  const min = Math.min(...history.map((h) => h.best_score));
  const range = (max - min) || 1;
  const points = history
    .map((h, i) => {
      const x = (i / (history.length - 1)) * w;
      const y = h - ((h.best_score - min) / range) * (h - 10) - 5;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} className="iter-chart">
      <polyline points={points} fill="none" stroke="#00b4d8" strokeWidth="2" />
      {history.map((h, i) => (
        <circle
          key={i}
          cx={(i / (history.length - 1)) * w}
          cy={h.best_score}
          r="3"
          fill="#00b4d8"
        />
      ))}
    </svg>
  );
}
