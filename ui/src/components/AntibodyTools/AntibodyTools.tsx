import { useState } from "react";
import * as api from "../../api/client";
import "./AntibodyTools.css";

interface AntibodyToolsProps {
  initialSequence?: string;
  onClose: () => void;
}

type Tab = "number" | "humanize" | "immuno";

function AntibodyTools({ initialSequence = "", onClose }: AntibodyToolsProps) {
  const [tab, setTab] = useState<Tab>("number");
  const [sequence, setSequence] = useState(initialSequence);
  const [germline, setGermline] = useState("IGHV1-46");
  const [parent, setParent] = useState(initialSequence);
  const [humanized, setHumanized] = useState("");
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const run = async (fn: () => Promise<any>) => {
    setBusy(true);
    setErr(null);
    try {
      setResult(await fn());
    } catch (e: any) {
      setErr(e.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="ab-modal" onClick={(e) => e.stopPropagation()}>
        <div className="ab-header">
          <h3>Antibody Tools</h3>
          <button className="header-btn small" onClick={onClose}>Close</button>
        </div>
        <div className="ab-tabs">
          <button className={`ab-tab ${tab === "number" ? "active" : ""}`} onClick={() => { setTab("number"); setResult(null); }}>Number</button>
          <button className={`ab-tab ${tab === "humanize" ? "active" : ""}`} onClick={() => { setTab("humanize"); setResult(null); }}>Humanize</button>
          <button className={`ab-tab ${tab === "immuno" ? "active" : ""}`} onClick={() => { setTab("immuno"); setResult(null); }}>Immunogenicity</button>
        </div>

        <div className="ab-body">
          {tab === "number" && (
            <>
              <label className="ab-label">VH or VL sequence</label>
              <textarea
                className="ab-textarea"
                value={sequence}
                onChange={(e) => setSequence(e.target.value.toUpperCase().replace(/[^A-Z]/g, ""))}
                rows={5}
                placeholder="QVQLVQSGAEVKKPGASVKVSCKASGYTFT..."
              />
              <button className="ab-run" disabled={busy || !sequence} onClick={() => run(() => api.antibodyNumber(sequence))}>
                {busy ? "Working..." : "Number (Kabat)"}
              </button>
              {result && result.regions && (
                <div className="ab-regions">
                  <div className="ab-meta">
                    chain: <b>{result.chain_type}</b> | length: <b>{result.length}</b> | CDRs: <b>{result.n_cdrs}</b>
                  </div>
                  {result.regions.map((r: any, i: number) => (
                    <div key={i} className={`ab-region ${r.name.startsWith("CDR") ? "cdr" : "fr"}`}>
                      <div className="ab-region-head">{r.name} ({r.start}-{r.end})</div>
                      <div className="ab-region-seq">{r.residues}</div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {tab === "humanize" && (
            <>
              <label className="ab-label">Parent (mouse) sequence</label>
              <textarea
                className="ab-textarea"
                value={sequence}
                onChange={(e) => setSequence(e.target.value.toUpperCase().replace(/[^A-Z]/g, ""))}
                rows={5}
              />
              <label className="ab-label">Target germline</label>
              <select className="ab-select" value={germline} onChange={(e) => setGermline(e.target.value)}>
                <option value="IGHV1-46">IGHV1-46 (heavy)</option>
                <option value="IGHV3-23">IGHV3-23 (heavy)</option>
                <option value="IGKV1-39">IGKV1-39 (kappa light)</option>
              </select>
              <button className="ab-run" disabled={busy || !sequence} onClick={() => run(() => api.antibodyHumanize(sequence, germline))}>
                {busy ? "Working..." : "Humanize (CDR graft)"}
              </button>
              {result && result.humanized && (
                <div className="ab-result">
                  <div className="ab-meta">
                    germline: <b>{result.target_germline}</b> | id→parent: <b>{(result.identity_to_parent * 100).toFixed(1)}%</b> | id→germline: <b>{(result.identity_to_germline * 100).toFixed(1)}%</b> | mutations: <b>{result.n_mutations}</b>
                  </div>
                  <label className="ab-label">Humanized sequence</label>
                  <textarea className="ab-textarea" readOnly value={result.humanized} rows={5} />
                  <button className="ab-run secondary" onClick={() => { setParent(sequence); setHumanized(result.humanized); setTab("immuno"); setResult(null); }}>
                    Check immunogenicity
                  </button>
                </div>
              )}
            </>
          )}

          {tab === "immuno" && (
            <>
              <label className="ab-label">Parent sequence</label>
              <textarea className="ab-textarea" value={parent} onChange={(e) => setParent(e.target.value.toUpperCase().replace(/[^A-Z]/g, ""))} rows={4} />
              <label className="ab-label">Humanized sequence</label>
              <textarea className="ab-textarea" value={humanized} onChange={(e) => setHumanized(e.target.value.toUpperCase().replace(/[^A-Z]/g, ""))} rows={4} />
              <button className="ab-run" disabled={busy || !parent || !humanized} onClick={() => run(() => api.antibodyImmunogenicity(parent, humanized))}>
                {busy ? "Working..." : "Compute Δ immunogenicity"}
              </button>
              {result && typeof result.delta === "number" && (
                <div className="ab-result">
                  <div className={`ab-delta ${result.delta > 0 ? "good" : result.delta < 0 ? "bad" : ""}`}>
                    Δ = {result.delta.toFixed(2)} motifs
                  </div>
                  <div className="ab-hint">{result.interpretation}</div>
                </div>
              )}
            </>
          )}

          {err && <div className="ab-error">{err}</div>}
        </div>
      </div>
    </div>
  );
}

export default AntibodyTools;
