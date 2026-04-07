import type { AnalysisResult } from "../../api/client";
import "./AnalysisPanel.css";

interface AnalysisPanelProps {
  analysis: AnalysisResult;
  onClose: () => void;
}

export default function AnalysisPanel({ analysis, onClose }: AnalysisPanelProps) {
  const { properties: p, lipinski, hydropathy_profile, disorder, structure } = analysis;

  return (
    <div className="analysis-panel">
      <div className="analysis-header">
        <h2>Protein Analysis Suite</h2>
        <button className="ap-close" onClick={onClose}>×</button>
      </div>

      <div className="analysis-content">
        {/* Properties grid */}
        <section className="ap-section">
          <h3>Sequence Properties</h3>
          <div className="props-grid">
            <Prop label="Length" value={`${p.length} aa`} />
            <Prop label="Molecular Weight" value={`${p.molecular_weight.toLocaleString()} Da`} />
            <Prop label="Isoelectric Point (pI)" value={p.isoelectric_point.toFixed(2)} />
            <Prop label="GRAVY Hydropathy" value={p.gravy.toFixed(3)} />
            <Prop label="Aromaticity" value={(p.aromaticity * 100).toFixed(1) + "%"} />
            <Prop label="Aliphatic Index" value={p.aliphatic_index.toFixed(1)} />
            <Prop label="Charge @ pH 7" value={p.charge_at_ph7.toFixed(2)} />
            <Prop label="Instability Index" value={`${p.instability_index.toFixed(1)} (${p.classification})`} />
            <Prop label="Ext. Coef. (reduced)" value={`${p.extinction_coefficient_reduced.toLocaleString()} M⁻¹·cm⁻¹`} />
            <Prop label="N-term Half-life" value={p.half_life_mammalian} />
          </div>
        </section>

        {/* Lipinski Rule of Five */}
        <section className="ap-section">
          <h3>
            Lipinski's Rule of Five
            <span className={`ap-badge ${lipinski.passes_ro5 ? "pass" : "fail"}`}>
              {lipinski.passes_ro5 ? "PASS" : "FAIL"}
            </span>
          </h3>
          <div className="props-grid">
            <Prop label="Mol. Weight" value={`${lipinski.molecular_weight.toFixed(0)} (≤500)`} />
            <Prop label="H-bond Donors" value={`${lipinski.h_bond_donors} (≤5)`} />
            <Prop label="H-bond Acceptors" value={`${lipinski.h_bond_acceptors} (≤10)`} />
            <Prop label="LogP estimate" value={`${lipinski.logp_estimate} (≤5)`} />
          </div>
          {lipinski.violations.length > 0 && (
            <div className="ap-violations">
              <strong>Violations:</strong>
              <ul>
                {lipinski.violations.map((v, i) => (
                  <li key={i}>{v}</li>
                ))}
              </ul>
            </div>
          )}
        </section>

        {/* Hydropathy plot */}
        <section className="ap-section">
          <h3>Hydropathy Profile (Kyte-Doolittle)</h3>
          <HydropathyPlot data={hydropathy_profile} />
          <p className="ap-note">
            Values above 0 indicate hydrophobic regions; below 0, hydrophilic. Peaks above 1.6 over a window of ~19 residues suggest transmembrane segments.
          </p>
        </section>

        {/* Disorder */}
        <section className="ap-section">
          <h3>
            Intrinsic Disorder
            <span className="ap-badge">{disorder.disorder_percent.toFixed(0)}% disordered</span>
          </h3>
          <DisorderPlot scores={disorder.scores} />
          {disorder.regions.length > 0 && (
            <div className="ap-regions">
              <strong>Disordered regions:</strong>
              <ul>
                {disorder.regions.map((r, i) => (
                  <li key={i}>
                    Residues {r.start}–{r.end} ({r.length} aa)
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>

        {/* Composition */}
        <section className="ap-section">
          <h3>Amino Acid Composition</h3>
          <CompositionBars composition={p.composition_pct} />
        </section>

        {/* Structure-based */}
        {structure && !("error" in structure) && (
          <>
            <section className="ap-section">
              <h3>Secondary Structure</h3>
              <div className="props-grid">
                <Prop label="α-Helix" value={`${structure.helix_pct.toFixed(1)}%`} />
                <Prop label="β-Strand" value={`${structure.strand_pct.toFixed(1)}%`} />
                <Prop label="Coil/Loop" value={`${structure.coil_pct.toFixed(1)}%`} />
                <Prop label="Radius of Gyration" value={`${structure.radius_of_gyration} Å`} />
                <Prop label="SASA (estimate)" value={`${structure.sasa_estimate} Å²`} />
                <Prop label="Atoms" value={`${structure.num_atoms}`} />
              </div>
              <SecondaryStructureBar ss={structure.secondary_structure} />
            </section>

            <section className="ap-section">
              <h3>Ramachandran Plot</h3>
              <RamachandranPlot angles={structure.ramachandran} />
            </section>

            {structure.pockets.length > 0 && (
              <section className="ap-section">
                <h3>Putative Binding Pockets</h3>
                <div className="pocket-list">
                  {structure.pockets.slice(0, 5).map((pk, i) => (
                    <div key={i} className="pocket-item">
                      <span className="pocket-rank">#{i + 1}</span>
                      <span>Residue {pk.residue_index}</span>
                      <span className="pocket-score">score {pk.score.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function Prop({ label, value }: { label: string; value: string }) {
  return (
    <div className="prop">
      <div className="prop-label">{label}</div>
      <div className="prop-value">{value}</div>
    </div>
  );
}

function HydropathyPlot({ data }: { data: number[] }) {
  const w = 600;
  const h = 100;
  const max = Math.max(...data, 4);
  const min = Math.min(...data, -4);
  const range = max - min;

  const points = data
    .map((d, i) => {
      const x = (i / (data.length - 1)) * w;
      const y = h - ((d - min) / range) * h;
      return `${x},${y}`;
    })
    .join(" ");

  const zeroY = h - ((-min) / range) * h;

  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} className="ap-plot">
      <line x1="0" y1={zeroY} x2={w} y2={zeroY} stroke="#666" strokeDasharray="2,2" />
      <polyline points={points} fill="none" stroke="#00b4d8" strokeWidth="2" />
    </svg>
  );
}

function DisorderPlot({ scores }: { scores: number[] }) {
  const w = 600;
  const h = 60;
  const points = scores
    .map((s, i) => {
      const x = (i / (scores.length - 1)) * w;
      const y = h - s * h;
      return `${x},${y}`;
    })
    .join(" ");
  const threshY = h - 0.5 * h;
  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} className="ap-plot">
      <line x1="0" y1={threshY} x2={w} y2={threshY} stroke="#ff9800" strokeDasharray="2,2" />
      <polyline points={points} fill="none" stroke="#9c27b0" strokeWidth="2" />
    </svg>
  );
}

function CompositionBars({ composition }: { composition: Record<string, number> }) {
  const entries = Object.entries(composition);
  const max = Math.max(...entries.map(([, v]) => v));
  return (
    <div className="comp-bars">
      {entries.map(([aa, pct]) => (
        <div key={aa} className="comp-bar">
          <div className="comp-aa">{aa}</div>
          <div className="comp-bar-bg">
            <div
              className="comp-bar-fill"
              style={{ width: `${(pct / max) * 100}%` }}
            />
          </div>
          <div className="comp-pct">{pct.toFixed(1)}%</div>
        </div>
      ))}
    </div>
  );
}

function SecondaryStructureBar({ ss }: { ss: string }) {
  const colors: Record<string, string> = {
    H: "#ff4500",
    E: "#1e90ff",
    C: "#666",
  };
  return (
    <div className="ss-bar">
      {ss.split("").map((c, i) => (
        <div
          key={i}
          className="ss-cell"
          style={{ background: colors[c] || "#666" }}
          title={`Pos ${i + 1}: ${c === "H" ? "Helix" : c === "E" ? "Strand" : "Coil"}`}
        />
      ))}
    </div>
  );
}

function RamachandranPlot({ angles }: { angles: { phi: number | null; psi: number | null }[] }) {
  const w = 300;
  const h = 300;
  // -180 to 180 mapped to 0..w
  const map = (v: number) => ((v + 180) / 360) * w;

  const points = angles
    .filter((a) => a.phi !== null && a.psi !== null)
    .map((a) => ({ phi: a.phi as number, psi: a.psi as number }));

  return (
    <div className="rama-container">
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="rama-plot">
        {/* Background regions (favored) */}
        <ellipse cx={map(-65)} cy={h - map(-45)} rx="30" ry="15" fill="rgba(0, 180, 216, 0.2)" />
        <ellipse cx={map(-120)} cy={h - map(120)} rx="35" ry="20" fill="rgba(255, 152, 0, 0.2)" />
        {/* Axes */}
        <line x1={w / 2} y1="0" x2={w / 2} y2={h} stroke="#444" />
        <line x1="0" y1={h / 2} x2={w} y2={h / 2} stroke="#444" />
        {/* Points */}
        {points.map((a, i) => (
          <circle
            key={i}
            cx={map(a.phi)}
            cy={h - map(a.psi)}
            r="2"
            fill="#00b4d8"
          />
        ))}
        {/* Labels */}
        <text x="5" y="15" fill="#999" fontSize="10">+ψ</text>
        <text x="5" y={h - 5} fill="#999" fontSize="10">-ψ</text>
        <text x={w - 25} y={h / 2 + 12} fill="#999" fontSize="10">+φ</text>
        <text x="5" y={h / 2 + 12} fill="#999" fontSize="10">-φ</text>
      </svg>
      <p className="ap-note">
        Each dot is one residue. Blue region = α-helix, orange region = β-sheet.
      </p>
    </div>
  );
}
