import { useMemo, type ReactNode } from "react";
import "./SequenceRuler.css";

interface Props {
  sequence: string;
  highlight?: number[];
  onResidueClick?: (pos: number, aa: string) => void;
}

const AA_COLORS: Record<string, string> = {
  A: "#c8e6c9", V: "#c8e6c9", L: "#c8e6c9", I: "#c8e6c9", M: "#c8e6c9",  // hydrophobic (green)
  F: "#d1c4e9", Y: "#d1c4e9", W: "#d1c4e9",                                // aromatic (purple)
  S: "#b3e5fc", T: "#b3e5fc", N: "#b3e5fc", Q: "#b3e5fc",                  // polar (blue)
  K: "#ffcdd2", R: "#ffcdd2", H: "#ffcdd2",                                // basic (red)
  D: "#fff9c4", E: "#fff9c4",                                              // acidic (yellow)
  C: "#ffe0b2", G: "#eeeeee", P: "#e1bee7",                                // special
};

export default function SequenceRuler({ sequence, highlight = [], onResidueClick }: Props) {
  const hset = useMemo(() => new Set(highlight), [highlight]);
  if (!sequence) return null;
  const rows: ReactNode[] = [];
  const WIDTH = 60;
  for (let i = 0; i < sequence.length; i += WIDTH) {
    const slice = sequence.slice(i, i + WIDTH);
    rows.push(
      <div key={i} className="sr-row">
        <span className="sr-num">{i + 1}</span>
        <div className="sr-chunk">
          {slice.split("").map((aa, j) => {
            const pos = i + j + 1;
            const bg = AA_COLORS[aa] || "#f5f5f5";
            return (
              <span
                key={j}
                className={`sr-res ${hset.has(pos) ? "hi" : ""}`}
                style={{ background: bg }}
                onClick={() => onResidueClick?.(pos, aa)}
                title={`${aa}${pos}`}
              >
                {aa}
              </span>
            );
          })}
        </div>
        <span className="sr-num end">{Math.min(i + WIDTH, sequence.length)}</span>
      </div>
    );
  }
  return <div className="sr">{rows}</div>;
}
