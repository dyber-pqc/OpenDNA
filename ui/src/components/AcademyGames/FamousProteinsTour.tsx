import { useState } from "react";
import * as api from "../../api/client";
import "./FamousProteinsTour.css";

interface FamousProtein {
  key: string;
  name: string;
  function: string;
  famousFor: string;
  funFact: string;
  uniprot: string;
}

const PROTEINS: FamousProtein[] = [
  {
    key: "hemoglobin",
    name: "Hemoglobin",
    function: "Carries oxygen from lungs to tissues in red blood cells.",
    famousFor: "First protein whose structure was solved by X-ray crystallography (Perutz, 1959).",
    funFact: "An adult human contains about 750 g of hemoglobin and turns over 6 g of it every day.",
    uniprot: "P69905",
  },
  {
    key: "insulin",
    name: "Insulin",
    function: "Hormone that signals cells to take up glucose from the blood.",
    famousFor: "First protein to have its amino acid sequence determined (Sanger, 1955).",
    funFact: "Insulin was the first recombinant DNA drug, produced in E. coli in 1978.",
    uniprot: "P01308",
  },
  {
    key: "gfp",
    name: "GFP (Green Fluorescent Protein)",
    function: "Glows bright green under UV light; used as a tag to track other proteins.",
    famousFor: "Won the 2008 Nobel Prize in Chemistry (Shimomura, Chalfie, Tsien).",
    funFact: "Originally isolated from the jellyfish Aequorea victoria.",
    uniprot: "P42212",
  },
  {
    key: "ubiquitin",
    name: "Ubiquitin",
    function: "Tags other proteins for destruction by the proteasome.",
    famousFor: "One of the most evolutionarily conserved proteins known — nearly identical from yeast to humans.",
    funFact: "Just 76 residues long, but its ubiquitination system controls almost every cellular process.",
    uniprot: "P0CG48",
  },
  {
    key: "lysozyme",
    name: "Lysozyme",
    function: "Breaks down bacterial cell walls; part of the innate immune defense.",
    famousFor: "Second protein structure ever solved (Phillips, 1965). Discovered by Alexander Fleming in 1922.",
    funFact: "Found in tears, saliva, and egg whites — a natural antibiotic.",
    uniprot: "P00698",
  },
];

interface Props {
  onPickSequence?: (seq: string, label: string) => void;
  onComplete?: () => void;
  onAwardXp?: (amt: number) => void;
}

export default function FamousProteinsTour({ onPickSequence, onComplete, onAwardXp }: Props) {
  const [idx, setIdx] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const p = PROTEINS[idx];

  const next = () => {
    if (idx + 1 < PROTEINS.length) setIdx(idx + 1);
    else {
      onAwardXp?.(40);
      onComplete?.();
    }
  };
  const prev = () => idx > 0 && setIdx(idx - 1);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.fetchUniprot(p.uniprot);
      onPickSequence?.(r.sequence, r.name || p.name);
    } catch (e: any) {
      setError(e.message || "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fpt-root">
      <div className="fpt-progress">
        Protein {idx + 1} of {PROTEINS.length}
      </div>
      <div className="fpt-card">
        <h3 className="fpt-name">{p.name}</h3>
        <div className="fpt-row"><strong>Function:</strong> {p.function}</div>
        <div className="fpt-row"><strong>Famous for:</strong> {p.famousFor}</div>
        <div className="fpt-row fpt-fun"><strong>Fun fact:</strong> {p.funFact}</div>
        <div className="fpt-actions">
          <button className="fpt-load" onClick={load} disabled={loading}>
            {loading ? "Loading..." : "Load this protein"}
          </button>
          {error && <span className="fpt-error">{error}</span>}
        </div>
      </div>
      <div className="fpt-nav">
        <button onClick={prev} disabled={idx === 0}>← Prev</button>
        <button onClick={next}>{idx + 1 === PROTEINS.length ? "Finish" : "Next →"}</button>
      </div>
    </div>
  );
}
