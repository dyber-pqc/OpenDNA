import { useState } from "react";
import "./PaperExtractor.css";

interface Extraction {
  type: string;
  value: string;
  context: string;
}

interface PaperExtractorProps {
  onClose: () => void;
  onPickSequence: (sequence: string, label?: string) => void;
}

const API_BASE = "http://localhost:8765";

export default function PaperExtractor({
  onClose,
  onPickSequence,
}: PaperExtractorProps) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<Extraction[] | null>(null);

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.name.toLowerCase().endsWith(".pdf")) {
      const buf = await f.arrayBuffer();
      let binary = "";
      const bytes = new Uint8Array(buf);
      for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
      }
      const b64 = btoa(binary);
      await runExtract({ pdf_base64: b64 });
    } else {
      const t = await f.text();
      setText(t);
    }
  };

  const runExtract = async (body: { text?: string; pdf_base64?: string }) => {
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const res = await fetch(`${API_BASE}/v1/llm/extract_paper`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResults(data.extractions || []);
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  };

  const onExtract = () => runExtract({ text });

  const onPick = (ext: Extraction) => {
    if (ext.type === "fasta" || ext.type === "sequence") {
      onPickSequence(ext.value, ext.type);
    } else if (ext.type === "uniprot") {
      // Fetch sequence from backend by UniProt id.
      fetch(`${API_BASE}/v1/uniprot/${encodeURIComponent(ext.value)}`)
        .then((r) => r.json())
        .then((d) => {
          if (d.sequence) onPickSequence(d.sequence, ext.value);
        })
        .catch(() => {
          /* ignore */
        });
    } else if (ext.type === "pdb") {
      fetch(`${API_BASE}/v1/pdb/${encodeURIComponent(ext.value)}`)
        .then((r) => r.json())
        .then((d) => {
          if (d.sequence) onPickSequence(d.sequence, ext.value);
        })
        .catch(() => {
          /* ignore */
        });
    }
  };

  return (
    <div className="paper-extractor-overlay">
      <div className="paper-extractor">
        <div className="pe-header">
          <h2>📄 Extract Proteins from Paper</h2>
          <button className="pe-close" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="pe-body">
          <p className="pe-hint">
            Paste paper text below, or upload a .pdf / .txt file. We'll scan
            for FASTA blocks, UniProt accessions, PDB IDs, and inline
            sequences.
          </p>
          <textarea
            className="pe-textarea"
            placeholder="Paste abstract, methods section, or full paper text here…"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
          />
          <div className="pe-actions">
            <label className="pe-file-label">
              <input
                type="file"
                accept=".pdf,.txt,.md"
                onChange={onFile}
                style={{ display: "none" }}
              />
              📁 Upload file
            </label>
            <button
              className="pe-extract-btn"
              onClick={onExtract}
              disabled={loading || !text.trim()}
            >
              {loading ? "Scanning…" : "Extract proteins"}
            </button>
          </div>

          {error && <div className="pe-error">Error: {error}</div>}

          {results && (
            <div className="pe-results">
              <div className="pe-results-head">
                Found {results.length} reference
                {results.length === 1 ? "" : "s"}
              </div>
              {results.length === 0 && (
                <div className="pe-empty">
                  No protein references detected in this text.
                </div>
              )}
              {results.map((ext, i) => (
                <div key={i} className={`pe-card pe-card-${ext.type}`}>
                  <div className="pe-card-head">
                    <span className={`pe-badge pe-badge-${ext.type}`}>
                      {ext.type}
                    </span>
                    <span className="pe-value" title={ext.value}>
                      {ext.value.length > 60
                        ? ext.value.slice(0, 60) + "…"
                        : ext.value}
                    </span>
                  </div>
                  <div className="pe-context">{ext.context}</div>
                  <button
                    className="pe-load-btn"
                    onClick={() => onPick(ext)}
                  >
                    Load this sequence
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
