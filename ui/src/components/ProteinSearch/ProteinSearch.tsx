import { useState, useCallback } from "react";
import { uniprotSearch, type UniprotHit } from "../../api/client";
import "./ProteinSearch.css";

interface Props {
  onPick: (hit: UniprotHit) => void;
  onClose?: () => void;
}

export default function ProteinSearch({ onPick, onClose }: Props) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<UniprotHit[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reviewedOnly, setReviewedOnly] = useState(true);
  const [organism, setOrganism] = useState("");

  const search = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const r = await uniprotSearch(query.trim(), 30, reviewedOnly, organism || undefined);
      setHits(r.hits);
    } catch (e: any) {
      setError(e.message || "search failed");
    } finally {
      setLoading(false);
    }
  }, [query, reviewedOnly, organism]);

  return (
    <div className="protein-search">
      <div className="ps-header">
        <h2>Search proteins (UniProt)</h2>
        {onClose && <button className="ps-close" onClick={onClose}>✕</button>}
      </div>
      <div className="ps-controls">
        <input
          className="ps-input"
          placeholder="e.g. brain cancer, hemoglobin, kinase, p53…"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") search(); }}
          autoFocus
        />
        <input
          className="ps-organism"
          placeholder="organism (optional)"
          value={organism}
          onChange={e => setOrganism(e.target.value)}
        />
        <label className="ps-checkbox">
          <input type="checkbox" checked={reviewedOnly} onChange={e => setReviewedOnly(e.target.checked)} />
          Reviewed only (Swiss-Prot)
        </label>
        <button className="ps-go" onClick={search} disabled={loading || !query.trim()}>
          {loading ? "Searching…" : "Search"}
        </button>
      </div>
      {error && <div className="ps-error">{error}</div>}
      <div className="ps-results">
        {hits.length === 0 && !loading && (
          <div className="ps-empty">
            Try queries like <em>brain cancer</em>, <em>blood coagulation</em>,
            <em> kinase human</em>, <em>insulin</em>, <em>spike protein coronavirus</em>.
          </div>
        )}
        {hits.map(h => (
          <div key={h.accession} className="ps-hit" onClick={() => onPick(h)}>
            <div className="ps-hit-main">
              <div className="ps-hit-title">
                <strong>{h.gene || h.id}</strong>
                <span className="ps-acc">{h.accession}</span>
                <span className="ps-len">{h.length} aa</span>
              </div>
              <div className="ps-hit-name">{h.name}</div>
              <div className="ps-hit-org">{h.organism}</div>
              {h.function && <div className="ps-hit-fn">{h.function.slice(0, 240)}{h.function.length > 240 ? "…" : ""}</div>}
            </div>
            <button className="ps-load" onClick={(e) => { e.stopPropagation(); onPick(h); }}>
              Load →
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
