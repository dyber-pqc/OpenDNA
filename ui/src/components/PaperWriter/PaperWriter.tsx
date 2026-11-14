import { useState } from "react";
import "./PaperWriter.css";

const API_BASE = "http://localhost:8765";

interface Props {
  onClose: () => void;
  defaultProjectId?: string;
}

export default function PaperWriter({ onClose, defaultProjectId = "default" }: Props) {
  const [projectId, setProjectId] = useState(defaultProjectId);
  const [researchQuestion, setResearchQuestion] = useState(
    "Can we design a stable, small protein binder for a given target?"
  );
  const [title, setTitle] = useState("Untitled OpenDNA Project");
  const [authors, setAuthors] = useState("Anon Researcher");
  const [markdown, setMarkdown] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const call = async (path: string, body: any) => {
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(`${path} failed: ${r.status}`);
      const j = await r.json();
      setMarkdown(j.markdown || "");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const doMethods = () =>
    call("/v1/paper_writer/methods", { project_id: projectId });
  const doAbstract = () =>
    call("/v1/paper_writer/abstract", {
      project_id: projectId,
      research_question: researchQuestion,
    });
  const doFull = () =>
    call("/v1/paper_writer/full", {
      project_id: projectId,
      title,
      research_question: researchQuestion,
      author_names: authors.split(",").map((s) => s.trim()).filter(Boolean),
    });

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="paper-writer-panel" onClick={(e) => e.stopPropagation()}>
        <div className="pw-header">
          <h2>📝 Paper Writer</h2>
          <button onClick={onClose}>×</button>
        </div>
        <div className="pw-body">
          <div className="pw-fields">
            <label>
              Project ID
              <input value={projectId} onChange={(e) => setProjectId(e.target.value)} />
            </label>
            <label>
              Title
              <input value={title} onChange={(e) => setTitle(e.target.value)} />
            </label>
            <label>
              Authors (comma-separated)
              <input value={authors} onChange={(e) => setAuthors(e.target.value)} />
            </label>
            <label>
              Research question
              <input
                value={researchQuestion}
                onChange={(e) => setResearchQuestion(e.target.value)}
              />
            </label>
          </div>
          <div className="pw-actions">
            <button disabled={busy} onClick={doMethods}>Methods</button>
            <button disabled={busy} onClick={doAbstract}>Abstract</button>
            <button disabled={busy} onClick={doFull}>Full Paper</button>
          </div>
          {error && <div className="pw-error">{error}</div>}
          <textarea
            className="pw-output"
            value={markdown}
            onChange={(e) => setMarkdown(e.target.value)}
            placeholder="Generated markdown will appear here..."
            spellCheck={false}
          />
        </div>
      </div>
    </div>
  );
}
