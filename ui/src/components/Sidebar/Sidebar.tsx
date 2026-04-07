import { useState } from "react";
import "./Sidebar.css";
import type { StoredStructure } from "../../App";

interface SidebarProps {
  onFold: (sequence: string) => void;
  onEvaluate: (sequence: string) => void;
  onMutate: (mutation: string) => void;
  onDesign: () => void;
  onIterativeDesign: (rounds: number, perRound: number) => void;
  onAnalyze: () => void;
  onExplain: () => void;
  onMd: () => void;
  onCost: () => void;
  onImport: (kind: "uniprot" | "pdb", id: string) => void;
  hasActive: boolean;
  hasSequence: boolean;
  structures: StoredStructure[];
  activeId: string | null;
  compareId: string | null;
  onSelectActive: (id: string) => void;
  onSelectCompare: (id: string | null) => void;
}

export default function Sidebar({
  onFold,
  onEvaluate,
  onMutate,
  onDesign,
  onIterativeDesign,
  onAnalyze,
  onExplain,
  onMd,
  onCost,
  onImport,
  hasActive,
  hasSequence,
  structures,
  activeId,
  compareId,
  onSelectActive,
  onSelectCompare,
}: SidebarProps) {
  const [activeTab, setActiveTab] = useState<"tools" | "structures" | "import">("tools");
  const [sequence, setSequence] = useState("");
  const [mutation, setMutation] = useState("");
  const [iterRounds, setIterRounds] = useState(3);
  const [iterPerRound, setIterPerRound] = useState(5);
  const [importId, setImportId] = useState("");
  const [importKind, setImportKind] = useState<"uniprot" | "pdb">("uniprot");

  const submitFold = () => sequence.trim() && onFold(sequence.trim());
  const submitEval = () => sequence.trim() && onEvaluate(sequence.trim());
  const submitMutate = () => {
    if (mutation.trim()) {
      onMutate(mutation.trim());
      setMutation("");
    }
  };
  const submitIter = () => {
    if (sequence.trim()) onIterativeDesign(iterRounds, iterPerRound);
  };
  const submitImport = () => {
    if (importId.trim()) onImport(importKind, importId.trim());
  };

  return (
    <aside className="sidebar">
      <nav className="sidebar-tabs">
        <button className={activeTab === "tools" ? "active" : ""} onClick={() => setActiveTab("tools")}>Tools</button>
        <button className={activeTab === "structures" ? "active" : ""} onClick={() => setActiveTab("structures")}>
          Structures {structures.length > 0 && <span className="tab-count">{structures.length}</span>}
        </button>
        <button className={activeTab === "import" ? "active" : ""} onClick={() => setActiveTab("import")}>Import</button>
      </nav>

      <div className="sidebar-content">
        {activeTab === "tools" && (
          <div className="panel">
            <div className="tool-section">
              <label>Protein Sequence</label>
              <textarea
                className="sequence-input"
                placeholder="Paste amino acid sequence..."
                value={sequence}
                onChange={(e) => setSequence(e.target.value)}
                rows={4}
              />
              <button className="btn-primary" onClick={submitFold}>Predict Structure</button>
              <button className="btn-primary success" onClick={submitEval}>Score Protein</button>
              <button className="btn-primary info" onClick={submitImport}></button>
            </div>

            <div className="tool-section">
              <label>Iterative Design Loop</label>
              <div className="row">
                <input
                  type="number"
                  className="num-input"
                  value={iterRounds}
                  onChange={(e) => setIterRounds(parseInt(e.target.value || "3"))}
                  min="1"
                  max="10"
                  title="rounds"
                />
                <span className="lbl">rounds × </span>
                <input
                  type="number"
                  className="num-input"
                  value={iterPerRound}
                  onChange={(e) => setIterPerRound(parseInt(e.target.value || "5"))}
                  min="1"
                  max="20"
                  title="candidates"
                />
                <span className="lbl">candidates</span>
              </div>
              <button
                className="btn-primary purple"
                onClick={submitIter}
                disabled={!hasSequence}
                title={!hasSequence ? "Enter a sequence first" : "Auto-optimize protein over multiple rounds"}
              >
                Run Iterative Design
              </button>
            </div>

            <div className="tool-section">
              <label>Mutate Active Protein</label>
              <input
                className="sequence-input"
                placeholder="e.g. K48R"
                value={mutation}
                onChange={(e) => setMutation(e.target.value)}
                style={{ fontFamily: "JetBrains Mono, monospace" }}
              />
              <button className="btn-primary warning" onClick={submitMutate} disabled={!hasActive}>
                Apply Mutation & Refold
              </button>
            </div>

            <div className="tool-section">
              <label>Active Structure Tools</label>
              <button className="btn-secondary" onClick={onDesign} disabled={!hasActive}>
                Design 10 Sequences (ESM-IF1)
              </button>
              <button className="btn-secondary" onClick={onAnalyze} disabled={!hasSequence}>
                Full Analysis Suite
              </button>
              <button className="btn-secondary" onClick={onExplain} disabled={!hasSequence}>
                Explain This Protein (AI)
              </button>
              <button className="btn-secondary" onClick={onMd} disabled={!hasActive}>
                Quick MD (stability check)
              </button>
              <button className="btn-secondary" onClick={onCost} disabled={!hasSequence}>
                Cost & Carbon Estimate
              </button>
            </div>
          </div>
        )}

        {activeTab === "structures" && (
          <div className="panel">
            <h3>Folded Structures</h3>
            {structures.length === 0 ? (
              <p className="placeholder">No structures yet. Fold a protein first.</p>
            ) : (
              <div className="structure-list">
                {structures.map((s) => (
                  <div key={s.id} className={`structure-item ${s.id === activeId ? "active" : ""}`}>
                    <div className="structure-label" onClick={() => onSelectActive(s.id)}>
                      {s.label}
                      <span className="structure-conf">pLDDT: {(s.meanConfidence * 100).toFixed(0)}</span>
                    </div>
                    <button
                      className={`compare-btn ${s.id === compareId ? "active" : ""}`}
                      onClick={() => onSelectCompare(s.id === compareId ? null : s.id)}
                      title="Compare with active"
                    >
                      vs
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "import" && (
          <div className="panel">
            <h3>Import Protein</h3>
            <div className="tool-section">
              <label>Source</label>
              <div className="seg">
                <button
                  className={importKind === "uniprot" ? "seg-active" : ""}
                  onClick={() => setImportKind("uniprot")}
                >
                  UniProt
                </button>
                <button
                  className={importKind === "pdb" ? "seg-active" : ""}
                  onClick={() => setImportKind("pdb")}
                >
                  PDB
                </button>
              </div>
              <label>{importKind === "uniprot" ? "UniProt Accession or famous name" : "PDB ID"}</label>
              <input
                className="sequence-input"
                placeholder={importKind === "uniprot" ? "e.g. P0CG48 or 'ubiquitin'" : "e.g. 1UBQ"}
                value={importId}
                onChange={(e) => setImportId(e.target.value)}
              />
              <button className="btn-primary" onClick={submitImport}>
                Fetch
              </button>
            </div>

            <div className="tool-section">
              <label>Famous proteins</label>
              <div className="famous-grid">
                {[
                  ["ubiquitin", "P0CG48"],
                  ["insulin", "P01308"],
                  ["gfp", "P42212"],
                  ["lysozyme", "P00698"],
                  ["myoglobin", "P02185"],
                  ["p53", "P04637"],
                  ["kras", "P01116"],
                  ["egfr", "P00533"],
                ].map(([name]) => (
                  <button
                    key={name}
                    className="famous-btn"
                    onClick={() => {
                      setImportKind("uniprot");
                      setImportId(name);
                      onImport("uniprot", name);
                    }}
                  >
                    {name}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
