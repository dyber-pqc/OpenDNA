import { useMemo, useState } from "react";
import * as api from "../../api/client";
import "./MutationScanner.css";

interface Props {
  sequence: string;
  onCellClick?: (position: number, newAA: string) => void;
  onClose?: () => void;
}

// AAs sorted by chemistry class (matches SequenceRuler colors)
const AA_ORDER = [
  "A", "V", "L", "I", "M",   // hydrophobic  (green)
  "F", "Y", "W",              // aromatic     (purple)
  "S", "T", "N", "Q",         // polar        (blue)
  "K", "R", "H",              // basic        (red)
  "D", "E",                   // acidic       (yellow)
  "C", "G", "P",              // special
];

const AA_CLASS_COLOR: Record<string, string> = {
  A: "#c8e6c9", V: "#c8e6c9", L: "#c8e6c9", I: "#c8e6c9", M: "#c8e6c9",
  F: "#d1c4e9", Y: "#d1c4e9", W: "#d1c4e9",
  S: "#b3e5fc", T: "#b3e5fc", N: "#b3e5fc", Q: "#b3e5fc",
  K: "#ffcdd2", R: "#ffcdd2", H: "#ffcdd2",
  D: "#fff9c4", E: "#fff9c4",
  C: "#ffe0b2", G: "#eeeeee", P: "#e1bee7",
};

// BLOSUM62 substitution matrix. Higher = more similar.
// Source: standard NCBI BLOSUM62.
const BLOSUM62: Record<string, Record<string, number>> = {
  A: { A: 4, R:-1, N:-2, D:-2, C: 0, Q:-1, E:-1, G: 0, H:-2, I:-1, L:-1, K:-1, M:-1, F:-2, P:-1, S: 1, T: 0, W:-3, Y:-2, V: 0 },
  R: { A:-1, R: 5, N: 0, D:-2, C:-3, Q: 1, E: 0, G:-2, H: 0, I:-3, L:-2, K: 2, M:-1, F:-3, P:-2, S:-1, T:-1, W:-3, Y:-2, V:-3 },
  N: { A:-2, R: 0, N: 6, D: 1, C:-3, Q: 0, E: 0, G: 0, H: 1, I:-3, L:-3, K: 0, M:-2, F:-3, P:-2, S: 1, T: 0, W:-4, Y:-2, V:-3 },
  D: { A:-2, R:-2, N: 1, D: 6, C:-3, Q: 0, E: 2, G:-1, H:-1, I:-3, L:-4, K:-1, M:-3, F:-3, P:-1, S: 0, T:-1, W:-4, Y:-3, V:-3 },
  C: { A: 0, R:-3, N:-3, D:-3, C: 9, Q:-3, E:-4, G:-3, H:-3, I:-1, L:-1, K:-3, M:-1, F:-2, P:-3, S:-1, T:-1, W:-2, Y:-2, V:-1 },
  Q: { A:-1, R: 1, N: 0, D: 0, C:-3, Q: 5, E: 2, G:-2, H: 0, I:-3, L:-2, K: 1, M: 0, F:-3, P:-1, S: 0, T:-1, W:-2, Y:-1, V:-2 },
  E: { A:-1, R: 0, N: 0, D: 2, C:-4, Q: 2, E: 5, G:-2, H: 0, I:-3, L:-3, K: 1, M:-2, F:-3, P:-1, S: 0, T:-1, W:-3, Y:-2, V:-2 },
  G: { A: 0, R:-2, N: 0, D:-1, C:-3, Q:-2, E:-2, G: 6, H:-2, I:-4, L:-4, K:-2, M:-3, F:-3, P:-2, S: 0, T:-2, W:-2, Y:-3, V:-3 },
  H: { A:-2, R: 0, N: 1, D:-1, C:-3, Q: 0, E: 0, G:-2, H: 8, I:-3, L:-3, K:-1, M:-2, F:-1, P:-2, S:-1, T:-2, W:-2, Y: 2, V:-3 },
  I: { A:-1, R:-3, N:-3, D:-3, C:-1, Q:-3, E:-3, G:-4, H:-3, I: 4, L: 2, K:-3, M: 1, F: 0, P:-3, S:-2, T:-1, W:-3, Y:-1, V: 3 },
  L: { A:-1, R:-2, N:-3, D:-4, C:-1, Q:-2, E:-3, G:-4, H:-3, I: 2, L: 4, K:-2, M: 2, F: 0, P:-3, S:-2, T:-1, W:-2, Y:-1, V: 1 },
  K: { A:-1, R: 2, N: 0, D:-1, C:-3, Q: 1, E: 1, G:-2, H:-1, I:-3, L:-2, K: 5, M:-1, F:-3, P:-1, S: 0, T:-1, W:-3, Y:-2, V:-2 },
  M: { A:-1, R:-1, N:-2, D:-3, C:-1, Q: 0, E:-2, G:-3, H:-2, I: 1, L: 2, K:-1, M: 5, F: 0, P:-2, S:-1, T:-1, W:-1, Y:-1, V: 1 },
  F: { A:-2, R:-3, N:-3, D:-3, C:-2, Q:-3, E:-3, G:-3, H:-1, I: 0, L: 0, K:-3, M: 0, F: 6, P:-4, S:-2, T:-2, W: 1, Y: 3, V:-1 },
  P: { A:-1, R:-2, N:-2, D:-1, C:-3, Q:-1, E:-1, G:-2, H:-2, I:-3, L:-3, K:-1, M:-2, F:-4, P: 7, S:-1, T:-1, W:-4, Y:-3, V:-2 },
  S: { A: 1, R:-1, N: 1, D: 0, C:-1, Q: 0, E: 0, G: 0, H:-1, I:-2, L:-2, K: 0, M:-1, F:-2, P:-1, S: 4, T: 1, W:-3, Y:-2, V:-2 },
  T: { A: 0, R:-1, N: 0, D:-1, C:-1, Q:-1, E:-1, G:-2, H:-2, I:-1, L:-1, K:-1, M:-1, F:-2, P:-1, S: 1, T: 5, W:-2, Y:-2, V: 0 },
  W: { A:-3, R:-3, N:-4, D:-4, C:-2, Q:-2, E:-3, G:-2, H:-2, I:-3, L:-2, K:-3, M:-1, F: 1, P:-4, S:-3, T:-2, W:11, Y: 2, V:-3 },
  Y: { A:-2, R:-2, N:-2, D:-3, C:-2, Q:-1, E:-2, G:-3, H: 2, I:-1, L:-1, K:-2, M:-1, F: 3, P:-3, S:-2, T:-2, W: 2, Y: 7, V:-1 },
  V: { A: 0, R:-3, N:-3, D:-3, C:-1, Q:-2, E:-2, G:-3, H:-3, I: 3, L: 1, K:-2, M: 1, F:-1, P:-2, S:-2, T: 0, W:-3, Y:-1, V: 4 },
};

// Heuristic ddG from BLOSUM62: inverted score.
// Self-substitution = 0; large negative BLOSUM (dissimilar) => big positive ddG.
function heuristicDdg(wt: string, mut: string): number {
  if (wt === mut) return 0;
  const s = BLOSUM62[wt]?.[mut];
  if (s === undefined) return 0;
  // Self-score as baseline stability anchor
  const selfScore = BLOSUM62[wt]?.[wt] ?? 4;
  // ddG ~ (self - sub) * 0.5 gives a reasonable spread ~ -2..+5 kcal/mol
  return (selfScore - s) * 0.5;
}

const ROW_WIDTH = 60;

export default function MutationScanner({ sequence, onCellClick, onClose }: Props) {
  const seq = (sequence || "").toUpperCase().replace(/[^A-Z]/g, "");
  const [refined, setRefined] = useState<Record<string, number>>({});
  const [refining, setRefining] = useState(false);
  const [progress, setProgress] = useState(0);
  const [hover, setHover] = useState<{ pos: number; aa: string; ddg: number; x: number; y: number } | null>(null);

  // Precompute heuristic ddG for all (position, aa) pairs
  const heatmap = useMemo(() => {
    const m: number[][] = []; // [aaRowIdx][position]
    for (let i = 0; i < AA_ORDER.length; i++) {
      const row: number[] = [];
      const mutAA = AA_ORDER[i];
      for (let p = 0; p < seq.length; p++) {
        const wt = seq[p];
        const key = `${wt}${p + 1}${mutAA}`;
        const refinedVal = refined[key];
        row.push(refinedVal !== undefined ? refinedVal : heuristicDdg(wt, mutAA));
      }
      m.push(row);
    }
    return m;
  }, [seq, refined]);

  const ddgToColor = (ddg: number): string => {
    // Blue (stabilizing, negative) ... white (0) ... red (destabilizing, positive)
    const clamp = Math.max(-3, Math.min(3, ddg));
    const t = (clamp + 3) / 6; // 0..1
    if (clamp < 0) {
      // blue to white
      const g = Math.round(255 * (t / 0.5));
      return `rgb(${Math.round(100 + 155 * (t / 0.5))}, ${g}, 255)`;
    } else if (clamp > 0) {
      // white to red
      const g = Math.round(255 * (1 - (t - 0.5) / 0.5));
      return `rgb(255, ${g}, ${g})`;
    }
    return "rgb(255,255,255)";
  };

  // Split sequence into chunks of ROW_WIDTH for wrapping
  const chunks: { start: number; end: number }[] = [];
  for (let i = 0; i < seq.length; i += ROW_WIDTH) {
    chunks.push({ start: i, end: Math.min(i + ROW_WIDTH, seq.length) });
  }

  const refineWithEsm = async () => {
    if (refining || seq.length === 0) return;
    setRefining(true);
    setProgress(0);
    try {
      const updates: Record<string, number> = {};
      const total = seq.length * AA_ORDER.length;
      let done = 0;
      for (let p = 0; p < seq.length; p++) {
        const wt = seq[p];
        for (const mut of AA_ORDER) {
          if (mut === wt) { done++; continue; }
          const mutation = `${wt}${p + 1}${mut}`;
          try {
            const r = await api.predictDdg(seq, mutation);
            updates[mutation] = r.ddg_kcal_mol;
          } catch {
            // keep heuristic
          }
          done++;
          setProgress(done / total);
        }
        // Flush incrementally so user sees updates
        setRefined((old) => ({ ...old, ...updates }));
      }
    } finally {
      setRefining(false);
    }
  };

  if (!seq) {
    return (
      <div className="ms-empty">
        <p>No sequence loaded. Enter or import a protein sequence first.</p>
        {onClose && <button className="ms-btn" onClick={onClose}>Close</button>}
      </div>
    );
  }

  return (
    <div className="mutation-scanner">
      <div className="ms-header">
        <div>
          <h3>Saturation mutagenesis (heuristic)</h3>
          <p className="ms-sub">
            Heuristic ΔΔG from BLOSUM62 substitution scores · {seq.length} positions × 20 AAs
            = {seq.length * 20} mutants
          </p>
        </div>
        <div className="ms-header-actions">
          <button
            className="ms-btn primary"
            onClick={refineWithEsm}
            disabled={refining}
            title="POST each mutation to /v1/predict_ddg for ML-based ΔΔG"
          >
            {refining ? `Refining… ${(progress * 100).toFixed(0)}%` : "Refine with ESM"}
          </button>
          {onClose && <button className="ms-btn" onClick={onClose}>Close</button>}
        </div>
      </div>

      {refining && (
        <div className="ms-progress">
          <div className="ms-progress-bar" style={{ width: `${progress * 100}%` }} />
        </div>
      )}

      <div className="ms-legend">
        <span className="ms-legend-item"><span className="ms-swatch" style={{ background: "rgb(100,0,255)" }} />stabilizing (−)</span>
        <span className="ms-legend-item"><span className="ms-swatch" style={{ background: "white", border: "1px solid #999" }} />neutral</span>
        <span className="ms-legend-item"><span className="ms-swatch" style={{ background: "rgb(255,0,0)" }} />destabilizing (+)</span>
      </div>

      <div className="ms-grids">
        {chunks.map((chunk, ci) => (
          <div className="ms-grid" key={ci}>
            <div className="ms-axis-top">
              <div className="ms-corner" />
              {Array.from({ length: chunk.end - chunk.start }, (_, i) => {
                const pos = chunk.start + i + 1;
                return (
                  <div key={i} className="ms-col-label">
                    {pos % 10 === 0 || i === 0 ? pos : ""}
                  </div>
                );
              })}
            </div>
            {AA_ORDER.map((aa, rowIdx) => (
              <div className="ms-row" key={aa}>
                <div
                  className="ms-row-label"
                  style={{ background: AA_CLASS_COLOR[aa] }}
                  title={aa}
                >
                  {aa}
                </div>
                {Array.from({ length: chunk.end - chunk.start }, (_, i) => {
                  const posIdx = chunk.start + i;
                  const pos = posIdx + 1;
                  const wt = seq[posIdx];
                  const ddg = heatmap[rowIdx][posIdx];
                  const isWt = wt === aa;
                  return (
                    <div
                      key={i}
                      className={`ms-cell ${isWt ? "wt" : ""}`}
                      style={{ background: isWt ? "#222" : ddgToColor(ddg) }}
                      onMouseEnter={(e) => {
                        if (isWt) return;
                        const rect = (e.target as HTMLElement).getBoundingClientRect();
                        setHover({
                          pos, aa, ddg,
                          x: rect.left + rect.width / 2,
                          y: rect.top,
                        });
                      }}
                      onMouseLeave={() => setHover(null)}
                      onClick={() => {
                        if (isWt) return;
                        onCellClick?.(pos, aa);
                      }}
                    >
                      {isWt ? "·" : ""}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        ))}
      </div>

      {hover && (
        <div
          className="ms-tooltip"
          style={{ left: hover.x, top: hover.y - 8 }}
        >
          {seq[hover.pos - 1]}{hover.pos}{hover.aa}: predicted ΔΔG ={" "}
          {hover.ddg >= 0 ? "+" : ""}{hover.ddg.toFixed(2)} kcal/mol
        </div>
      )}
    </div>
  );
}
