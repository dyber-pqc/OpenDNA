import { useState } from "react";
import "./Sidebar.css";
import type { StoredStructure } from "../../App";

interface SidebarProps {
  onFold: (sequence: string) => void;
  onEvaluate: (sequence: string) => void;
  onMutate: (mutation: string) => void;
  onDesign: () => void;
  hasActive: boolean;
  structures: StoredStructure[];
  activeId: string | null;
  compareId: string | null;
  onSelectActive: (id: string) => void;
  onSelectCompare: (id: string | null) => void;
}

function Sidebar({
  onFold,
  onEvaluate,
  onMutate,
  onDesign,
  hasActive,
  structures,
  activeId,
  compareId,
  onSelectActive,
  onSelectCompare,
}: SidebarProps) {
  const [activeTab, setActiveTab] = useState<"projects" | "tools" | "learn">(
    "tools"
  );
  const [sequence, setSequence] = useState("");
  const [mutation, setMutation] = useState("");

  const handleFold = () => {
    if (sequence.trim()) onFold(sequence.trim());
  };
  const handleEvaluate = () => {
    if (sequence.trim()) onEvaluate(sequence.trim());
  };
  const handleMutate = () => {
    if (mutation.trim()) {
      onMutate(mutation.trim());
      setMutation("");
    }
  };

  return (
    <aside className="sidebar">
      <nav className="sidebar-tabs">
        <button
          className={activeTab === "projects" ? "active" : ""}
          onClick={() => setActiveTab("projects")}
        >
          Structures
        </button>
        <button
          className={activeTab === "tools" ? "active" : ""}
          onClick={() => setActiveTab("tools")}
        >
          Tools
        </button>
        <button
          className={activeTab === "learn" ? "active" : ""}
          onClick={() => setActiveTab("learn")}
        >
          Learn
        </button>
      </nav>

      <div className="sidebar-content">
        {activeTab === "projects" && (
          <div className="panel">
            <h3>Folded Structures</h3>
            {structures.length === 0 ? (
              <p className="placeholder">No structures yet. Fold a protein first.</p>
            ) : (
              <div className="structure-list">
                {structures.map((s) => (
                  <div
                    key={s.id}
                    className={`structure-item ${
                      s.id === activeId ? "active" : ""
                    }`}
                  >
                    <div
                      className="structure-label"
                      onClick={() => onSelectActive(s.id)}
                    >
                      {s.label}
                      <span className="structure-conf">
                        pLDDT: {(s.meanConfidence * 100).toFixed(0)}
                      </span>
                    </div>
                    <button
                      className={`compare-btn ${
                        s.id === compareId ? "active" : ""
                      }`}
                      onClick={() =>
                        onSelectCompare(s.id === compareId ? null : s.id)
                      }
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

        {activeTab === "tools" && (
          <div className="panel">
            <h3>Quick Actions</h3>

            <div className="tool-section">
              <label>Protein Sequence</label>
              <textarea
                className="sequence-input"
                placeholder="Paste amino acid sequence..."
                value={sequence}
                onChange={(e) => setSequence(e.target.value)}
                rows={4}
              />
              <button className="btn-primary" onClick={handleFold}>
                Predict Structure
              </button>
              <button
                className="btn-primary"
                style={{ marginTop: 6, background: "var(--success)" }}
                onClick={handleEvaluate}
              >
                Score Protein (Instant)
              </button>
            </div>

            <div className="tool-section">
              <label>Mutate Active Protein</label>
              <input
                className="sequence-input"
                placeholder="e.g. G45D"
                value={mutation}
                onChange={(e) => setMutation(e.target.value)}
                style={{ fontFamily: "JetBrains Mono, monospace" }}
              />
              <button
                className="btn-primary"
                style={{ marginTop: 6, background: "var(--warning)" }}
                onClick={handleMutate}
              >
                Apply Mutation & Refold
              </button>
            </div>

            <div className="tool-section">
              <label>Design Alternative Sequences</label>
              <button
                className="btn-primary"
                style={{ background: "#9c27b0" }}
                onClick={onDesign}
                disabled={!hasActive}
                title={!hasActive ? "Fold a protein first" : "Generate 10 sequences for the active backbone"}
              >
                Design 10 Sequences (ESM-IF1)
              </button>
            </div>

            <div className="tool-list">
              <button className="tool-btn" disabled>
                Dock Molecules
              </button>
              <button className="tool-btn" disabled>
                Run Simulation
              </button>
            </div>
          </div>
        )}

        {activeTab === "learn" && (
          <div className="panel">
            <h3>Protein Academy</h3>
            <div className="learn-card">
              <span className="badge">Level 1</span>
              <h4>What is a Protein?</h4>
              <p>Interactive 3D tutorial</p>
              <button className="btn-secondary">Start</button>
            </div>
            <div className="learn-card">
              <span className="badge">Level 2</span>
              <h4>Amino Acids Game</h4>
              <p>Match the building blocks</p>
              <button className="btn-secondary">Start</button>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

export default Sidebar;
