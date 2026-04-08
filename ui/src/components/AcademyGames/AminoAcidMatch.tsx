import { useMemo, useState } from "react";
import "./AminoAcidMatch.css";

const AMINO_ACIDS: { letter: string; name: string }[] = [
  { letter: "A", name: "Alanine" },
  { letter: "R", name: "Arginine" },
  { letter: "N", name: "Asparagine" },
  { letter: "D", name: "Aspartate" },
  { letter: "C", name: "Cysteine" },
  { letter: "E", name: "Glutamate" },
  { letter: "Q", name: "Glutamine" },
  { letter: "G", name: "Glycine" },
  { letter: "H", name: "Histidine" },
  { letter: "I", name: "Isoleucine" },
  { letter: "L", name: "Leucine" },
  { letter: "K", name: "Lysine" },
  { letter: "M", name: "Methionine" },
  { letter: "F", name: "Phenylalanine" },
  { letter: "P", name: "Proline" },
  { letter: "S", name: "Serine" },
  { letter: "T", name: "Threonine" },
  { letter: "W", name: "Tryptophan" },
  { letter: "Y", name: "Tyrosine" },
  { letter: "V", name: "Valine" },
];

function shuffle<T>(arr: T[]): T[] {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

interface Props {
  onAwardXp?: (amt: number) => void;
}

export default function AminoAcidMatch({ onAwardXp }: Props) {
  const namesShuffled = useMemo(() => shuffle(AMINO_ACIDS.map((a) => a.name)), []);
  const lettersShuffled = useMemo(() => shuffle(AMINO_ACIDS.map((a) => a.letter)), []);
  const [matched, setMatched] = useState<Record<string, string>>({}); // letter -> name
  const [score, setScore] = useState(0);
  const [done, setDone] = useState(false);
  const [dragging, setDragging] = useState<string | null>(null);

  const handleDrop = (letter: string, droppedName: string) => {
    if (matched[letter]) return;
    const correct = AMINO_ACIDS.find((a) => a.letter === letter)?.name === droppedName;
    if (correct) {
      const newMatched = { ...matched, [letter]: droppedName };
      setMatched(newMatched);
      setScore((s) => s + 10);
      if (Object.keys(newMatched).length === AMINO_ACIDS.length) {
        setDone(true);
        onAwardXp?.(50);
      }
    } else {
      setScore((s) => s - 2);
    }
    setDragging(null);
  };

  const usedNames = new Set(Object.values(matched));

  const reset = () => {
    setMatched({});
    setScore(0);
    setDone(false);
  };

  return (
    <div className="aam-root">
      <div className="aam-head">
        <div className="aam-title">Match the one-letter code to its amino acid name</div>
        <div className="aam-score">Score: <strong>{score}</strong></div>
      </div>

      <div className="aam-grid">
        <div className="aam-col">
          <div className="aam-col-title">Letters (drop here)</div>
          {lettersShuffled.map((letter) => {
            const name = matched[letter];
            return (
              <div
                key={letter}
                className={`aam-slot ${name ? "filled" : ""}`}
                onDragOver={(e) => {
                  e.preventDefault();
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  const dropped = e.dataTransfer.getData("text/plain") || dragging || "";
                  if (dropped) handleDrop(letter, dropped);
                }}
              >
                <span className="aam-letter">{letter}</span>
                {name && <span className="aam-matched-name">{name}</span>}
              </div>
            );
          })}
        </div>
        <div className="aam-col">
          <div className="aam-col-title">Names (drag from here)</div>
          {namesShuffled.map((n) => {
            const used = usedNames.has(n);
            return (
              <div
                key={n}
                className={`aam-name ${used ? "used" : ""}`}
                draggable={!used}
                onDragStart={(e) => {
                  e.dataTransfer.setData("text/plain", n);
                  e.dataTransfer.effectAllowed = "move";
                  setDragging(n);
                }}
                onDragEnd={() => setDragging(null)}
              >
                {n}
              </div>
            );
          })}
        </div>
      </div>

      {done && (
        <div className="aam-done">
          <h3>Complete!</h3>
          <p>Final score: <strong>{score}</strong></p>
          <button onClick={reset}>Play again</button>
        </div>
      )}
    </div>
  );
}
