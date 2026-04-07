import { useState } from "react";
import "./Academy.css";

const AMINO_ACIDS = [
  { letter: "A", name: "Alanine", prop: "Hydrophobic", color: "#FF8C00" },
  { letter: "R", name: "Arginine", prop: "Positive", color: "#1E90FF" },
  { letter: "N", name: "Asparagine", prop: "Polar", color: "#00CED1" },
  { letter: "D", name: "Aspartate", prop: "Negative", color: "#FF4500" },
  { letter: "C", name: "Cysteine", prop: "Special", color: "#FFD700" },
  { letter: "E", name: "Glutamate", prop: "Negative", color: "#FF4500" },
  { letter: "Q", name: "Glutamine", prop: "Polar", color: "#00CED1" },
  { letter: "G", name: "Glycine", prop: "Special", color: "#808080" },
  { letter: "H", name: "Histidine", prop: "Positive", color: "#1E90FF" },
  { letter: "I", name: "Isoleucine", prop: "Hydrophobic", color: "#FF8C00" },
  { letter: "L", name: "Leucine", prop: "Hydrophobic", color: "#FF8C00" },
  { letter: "K", name: "Lysine", prop: "Positive", color: "#1E90FF" },
  { letter: "M", name: "Methionine", prop: "Hydrophobic", color: "#FF8C00" },
  { letter: "F", name: "Phenylalanine", prop: "Aromatic", color: "#9370DB" },
  { letter: "P", name: "Proline", prop: "Special", color: "#808080" },
  { letter: "S", name: "Serine", prop: "Polar", color: "#00CED1" },
  { letter: "T", name: "Threonine", prop: "Polar", color: "#00CED1" },
  { letter: "W", name: "Tryptophan", prop: "Aromatic", color: "#9370DB" },
  { letter: "Y", name: "Tyrosine", prop: "Aromatic", color: "#9370DB" },
  { letter: "V", name: "Valine", prop: "Hydrophobic", color: "#FF8C00" },
];

interface AcademyProps {
  onClose: () => void;
  onAwardXp: (amount: number) => void;
}

export default function Academy({ onClose, onAwardXp }: AcademyProps) {
  const [level, setLevel] = useState<string | null>(null);

  return (
    <div className="academy">
      <div className="acad-header">
        <h2>Protein Academy</h2>
        <button className="acad-close" onClick={onClose}>×</button>
      </div>

      {!level ? (
        <div className="acad-levels">
          <LevelCard
            n={1}
            title="Amino Acid Match"
            desc="Learn the 20 building blocks of life"
            time="5 min"
            xp={50}
            onClick={() => setLevel("aa-match")}
          />
          <LevelCard
            n={2}
            title="Memory Quiz"
            desc="Test your knowledge of amino acid properties"
            time="3 min"
            xp={75}
            onClick={() => setLevel("aa-quiz")}
          />
          <LevelCard
            n={3}
            title="Sequence Reader"
            desc="Decode what a protein sequence tells you"
            time="5 min"
            xp={100}
            onClick={() => setLevel("seq-reader")}
          />
          <LevelCard
            n={4}
            title="Famous Proteins Tour"
            desc="Meet hemoglobin, insulin, GFP and more"
            time="10 min"
            xp={150}
            locked
          />
          <LevelCard
            n={5}
            title="Drug Design 101"
            desc="Design a binder for a cancer protein"
            time="15 min"
            xp={300}
            locked
          />
        </div>
      ) : level === "aa-match" ? (
        <AAMatchGame onComplete={(xp) => { onAwardXp(xp); setLevel(null); }} onBack={() => setLevel(null)} />
      ) : level === "aa-quiz" ? (
        <AAQuiz onComplete={(xp) => { onAwardXp(xp); setLevel(null); }} onBack={() => setLevel(null)} />
      ) : level === "seq-reader" ? (
        <SeqReader onComplete={(xp) => { onAwardXp(xp); setLevel(null); }} onBack={() => setLevel(null)} />
      ) : null}
    </div>
  );
}

function LevelCard({ n, title, desc, time, xp, onClick, locked }: any) {
  return (
    <div className={`level-card ${locked ? "locked" : ""}`} onClick={!locked ? onClick : undefined}>
      <div className="level-num">Level {n}</div>
      <div className="level-title">{title}</div>
      <div className="level-desc">{desc}</div>
      <div className="level-meta">
        <span>{time}</span>
        <span>+{xp} XP</span>
      </div>
      {locked && <div className="level-locked">Coming soon</div>}
    </div>
  );
}

function AAMatchGame({ onComplete, onBack }: { onComplete: (xp: number) => void; onBack: () => void }) {
  const [score, setScore] = useState(0);
  const [matched, setMatched] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<{ letter?: string; name?: string }>({});

  const shuffled = [...AMINO_ACIDS].sort(() => Math.random() - 0.5).slice(0, 8);
  const names = [...shuffled].sort(() => Math.random() - 0.5);

  const onLetterClick = (letter: string) => {
    if (matched.has(letter)) return;
    if (selected.name) {
      const aa = AMINO_ACIDS.find((a) => a.letter === letter);
      if (aa?.name === selected.name) {
        setMatched(new Set([...matched, letter]));
        setScore(score + 10);
        setSelected({});
        if (matched.size + 1 >= shuffled.length) {
          setTimeout(() => onComplete(50), 500);
        }
      } else {
        setSelected({});
      }
    } else {
      setSelected({ letter });
    }
  };

  const onNameClick = (name: string) => {
    const aa = AMINO_ACIDS.find((a) => a.name === name);
    if (aa && matched.has(aa.letter)) return;
    if (selected.letter) {
      if (aa?.letter === selected.letter) {
        setMatched(new Set([...matched, selected.letter]));
        setScore(score + 10);
        setSelected({});
        if (matched.size + 1 >= shuffled.length) {
          setTimeout(() => onComplete(50), 500);
        }
      } else {
        setSelected({});
      }
    } else {
      setSelected({ name });
    }
  };

  return (
    <div className="game">
      <div className="game-header">
        <button className="back" onClick={onBack}>← Back</button>
        <h3>Match the Letter to the Amino Acid Name</h3>
        <div className="game-score">Score: {score}</div>
      </div>
      <div className="match-grid">
        <div className="match-col">
          {shuffled.map((aa) => (
            <button
              key={aa.letter}
              className={`match-btn letter ${matched.has(aa.letter) ? "matched" : ""} ${selected.letter === aa.letter ? "selected" : ""}`}
              style={{ background: matched.has(aa.letter) ? aa.color : undefined }}
              onClick={() => onLetterClick(aa.letter)}
            >
              {aa.letter}
            </button>
          ))}
        </div>
        <div className="match-col">
          {names.map((aa) => (
            <button
              key={aa.name}
              className={`match-btn name ${matched.has(aa.letter) ? "matched" : ""} ${selected.name === aa.name ? "selected" : ""}`}
              onClick={() => onNameClick(aa.name)}
            >
              {aa.name}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function AAQuiz({ onComplete, onBack }: { onComplete: (xp: number) => void; onBack: () => void }) {
  const [qIdx, setQIdx] = useState(0);
  const [score, setScore] = useState(0);

  const questions = [
    { q: "Which amino acid is positively charged at pH 7?", opts: ["Lysine", "Glutamate", "Glycine", "Phenylalanine"], correct: 0 },
    { q: "Which amino acid forms disulfide bonds?", opts: ["Methionine", "Cysteine", "Serine", "Threonine"], correct: 1 },
    { q: "Which is the smallest amino acid?", opts: ["Alanine", "Valine", "Glycine", "Proline"], correct: 2 },
    { q: "Which amino acid often causes kinks in helices?", opts: ["Leucine", "Tryptophan", "Histidine", "Proline"], correct: 3 },
    { q: "What does GRAVY score measure?", opts: ["Charge", "Hydrophobicity", "Mass", "Aromaticity"], correct: 1 },
  ];

  const q = questions[qIdx];

  const answer = (idx: number) => {
    if (idx === q.correct) setScore(score + 15);
    if (qIdx + 1 < questions.length) {
      setQIdx(qIdx + 1);
    } else {
      setTimeout(() => onComplete(75), 500);
    }
  };

  return (
    <div className="game">
      <div className="game-header">
        <button className="back" onClick={onBack}>← Back</button>
        <h3>Question {qIdx + 1} of {questions.length}</h3>
        <div className="game-score">Score: {score}</div>
      </div>
      <div className="quiz">
        <div className="quiz-q">{q.q}</div>
        <div className="quiz-opts">
          {q.opts.map((opt, i) => (
            <button key={i} className="quiz-opt" onClick={() => answer(i)}>{opt}</button>
          ))}
        </div>
      </div>
    </div>
  );
}

function SeqReader({ onComplete, onBack }: { onComplete: (xp: number) => void; onBack: () => void }) {
  return (
    <div className="game">
      <div className="game-header">
        <button className="back" onClick={onBack}>← Back</button>
        <h3>Sequence Reader Tutorial</h3>
      </div>
      <div className="reader">
        <p>
          A protein is a chain of amino acids written as a string of letters.
          Each letter is one amino acid. For example:
        </p>
        <div className="reader-seq">MQIFVKTLTGKTITLE</div>
        <p>
          Reading this: M = Methionine (start codon), Q = Glutamine, I = Isoleucine, F = Phenylalanine...
        </p>
        <p>
          Patterns to look for:
          <ul>
            <li><strong>K, R, H</strong> = positive charge (often surface-exposed)</li>
            <li><strong>D, E</strong> = negative charge</li>
            <li><strong>I, L, V, F, W, Y, M, A</strong> = hydrophobic (often buried in core)</li>
            <li><strong>C</strong> = cysteine, can form disulfide bridges</li>
            <li><strong>P</strong> = proline, kinks the chain</li>
            <li><strong>G</strong> = glycine, very flexible</li>
          </ul>
        </p>
        <button className="btn-primary" onClick={() => onComplete(100)}>
          I get it! (+100 XP)
        </button>
      </div>
    </div>
  );
}
