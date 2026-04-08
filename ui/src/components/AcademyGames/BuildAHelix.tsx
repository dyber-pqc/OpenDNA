import { useMemo, useState } from "react";
import "./BuildAHelix.css";

const PALETTE = [
  "A", "V", "L", "I", "M", "F", "W", "Y", // hydrophobic
  "S", "T", "N", "Q", // polar
  "K", "R", "D", "E", // charged
  "G", "P", "C", "H",
];
const HYDROPHOBIC = new Set(["A", "V", "L", "I", "M", "F", "W", "Y"]);
const SLOTS = 10;

interface Props {
  onAwardXp?: (amt: number) => void;
}

export default function BuildAHelix({ onAwardXp }: Props) {
  const [slots, setSlots] = useState<(string | null)[]>(() => Array(SLOTS).fill(null));
  const [helixed, setHelixed] = useState(false);
  const [drag, setDrag] = useState<string | null>(null);

  const longestRun = useMemo(() => {
    let best = 0, cur = 0;
    for (const r of slots) {
      if (r && HYDROPHOBIC.has(r)) {
        cur++;
        best = Math.max(best, cur);
      } else cur = 0;
    }
    return best;
  }, [slots]);

  const canHelix = longestRun >= 4 && !helixed;

  const setSlot = (i: number, residue: string) => {
    setSlots((s) => {
      const cp = s.slice();
      cp[i] = residue;
      return cp;
    });
  };

  const clearSlot = (i: number) => {
    setSlots((s) => {
      const cp = s.slice();
      cp[i] = null;
      return cp;
    });
    setHelixed(false);
  };

  const formHelix = () => {
    setHelixed(true);
    onAwardXp?.(60);
  };

  const reset = () => {
    setSlots(Array(SLOTS).fill(null));
    setHelixed(false);
  };

  return (
    <div className="bah-root">
      <div className="bah-head">
        <div className="bah-title">Build a Helix</div>
        <div className="bah-info">
          Drag residues into the track. Place <strong>4+ hydrophobic in a row</strong> to unlock fold.
          <span className="bah-run">Longest run: {longestRun}</span>
        </div>
      </div>

      <div className={`bah-track ${helixed ? "helixed" : ""}`}>
        {slots.map((r, i) => {
          const angle = helixed ? i * 100 : 0;
          const tx = helixed ? Math.cos((i * 100 * Math.PI) / 180) * 50 : 0;
          const ty = helixed ? Math.sin((i * 100 * Math.PI) / 180) * 30 : 0;
          return (
            <div
              key={i}
              className={`bah-slot ${r ? (HYDROPHOBIC.has(r) ? "hydrophobic" : "filled") : ""}`}
              style={{
                transform: `translate(${tx}px, ${ty}px) rotate(${angle}deg)`,
                transition: "transform 0.8s ease",
              }}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const v = e.dataTransfer.getData("text/plain") || drag || "";
                if (v) setSlot(i, v);
                setDrag(null);
                setHelixed(false);
              }}
              onClick={() => r && clearSlot(i)}
              title={r ? "Click to remove" : "Drop a residue here"}
            >
              {r || "·"}
            </div>
          );
        })}
      </div>

      <div className="bah-palette">
        {PALETTE.map((p) => (
          <div
            key={p}
            className={`bah-chip ${HYDROPHOBIC.has(p) ? "hydrophobic" : ""}`}
            draggable
            onDragStart={(e) => {
              e.dataTransfer.setData("text/plain", p);
              setDrag(p);
            }}
            onDragEnd={() => setDrag(null)}
          >
            {p}
          </div>
        ))}
      </div>

      <div className="bah-actions">
        <button disabled={!canHelix} onClick={formHelix} className="bah-form-btn">
          Form Helix
        </button>
        <button onClick={reset} className="bah-reset-btn">Reset</button>
      </div>

      {helixed && (
        <div className="bah-success">It folds! Hydrophobic residues drive helix formation.</div>
      )}
    </div>
  );
}
