import { useState } from "react";
import AminoAcidMatch from "../AcademyGames/AminoAcidMatch";
import BuildAHelix from "../AcademyGames/BuildAHelix";
import FamousProteinsTour from "../AcademyGames/FamousProteinsTour";
import "./AcademyGamesPanel.css";

interface Props {
  onClose: () => void;
  onAwardXp: (amt: number) => void;
  onPickSequence: (seq: string, label?: string) => void;
}

type Tab = "L1" | "L2" | "L3";

export default function AcademyGamesPanel({ onClose, onAwardXp, onPickSequence }: Props) {
  const [tab, setTab] = useState<Tab>("L1");

  return (
    <div className="modal-backdrop">
      <div className="agp-root">
        <div className="agp-header">
          <h2>Academy Mini-games</h2>
          <button className="agp-close" onClick={onClose}>×</button>
        </div>
        <div className="agp-tabs">
          <button className={tab === "L1" ? "active" : ""} onClick={() => setTab("L1")}>
            Level 1: Amino Acid Match
          </button>
          <button className={tab === "L2" ? "active" : ""} onClick={() => setTab("L2")}>
            Level 2: Build a Helix
          </button>
          <button className={tab === "L3" ? "active" : ""} onClick={() => setTab("L3")}>
            Level 3: Famous Proteins Tour
          </button>
        </div>
        <div className="agp-body">
          {tab === "L1" && <AminoAcidMatch onAwardXp={onAwardXp} />}
          {tab === "L2" && <BuildAHelix onAwardXp={onAwardXp} />}
          {tab === "L3" && (
            <FamousProteinsTour
              onAwardXp={onAwardXp}
              onPickSequence={onPickSequence}
              onComplete={() => onAwardXp(25)}
            />
          )}
        </div>
      </div>
    </div>
  );
}
