import { useEffect, useState } from "react";
import "./Hub.css";

const API_BASE = "http://localhost:8765";

interface HubProject {
  user_id: string;
  project_name: string;
  description: string;
  hub_url: string;
  published_at: number;
  forked_from?: string;
}

interface Props {
  onClose: () => void;
  currentPdb?: string;
  currentSequence?: string;
}

export default function Hub({ onClose, currentPdb = "" }: Props) {
  const [projects, setProjects] = useState<HubProject[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const r = await fetch(`${API_BASE}/v1/hub/projects`);
      const j = await r.json();
      setProjects(j.projects || []);
    } catch (e: any) {
      setError(e.message);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const publishCurrent = async () => {
    const user = window.prompt("Your hub username:", "anon") || "anon";
    const name = window.prompt("Project name:", "my-protein") || "";
    if (!name) return;
    const desc = window.prompt("Short description:", "") || "";
    setBusy(true);
    try {
      const r = await fetch(`${API_BASE}/v1/hub/publish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: user,
          project_name: name,
          pdb_string: currentPdb,
          description: desc,
        }),
      });
      if (!r.ok) throw new Error(`Publish failed: ${r.status}`);
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const fork = async (p: HubProject) => {
    const who = window.prompt("Fork as which username?", "anon") || "anon";
    try {
      const r = await fetch(`${API_BASE}/v1/hub/fork`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hub_url: p.hub_url, new_user_id: who }),
      });
      if (!r.ok) throw new Error(`Fork failed: ${r.status}`);
      await load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="hub-panel" onClick={(e) => e.stopPropagation()}>
        <div className="hub-header">
          <h2>🌐 OpenDNA Hub <span className="hub-local">(local)</span></h2>
          <div>
            <button
              className="hub-publish-btn"
              onClick={publishCurrent}
              disabled={busy || !currentPdb}
              title={currentPdb ? "Publish current structure" : "Load a structure first"}
            >
              Publish current
            </button>
            <button className="hub-close" onClick={onClose}>×</button>
          </div>
        </div>
        {error && <div className="hub-error">{error}</div>}
        <div className="hub-list">
          {projects.length === 0 && (
            <div className="hub-empty">No projects published yet.</div>
          )}
          {projects.map((p) => (
            <div key={p.hub_url} className="hub-project">
              <div className="hub-project-head">
                <strong>{p.user_id}</strong> / {p.project_name}
              </div>
              <div className="hub-project-url">{p.hub_url}</div>
              {p.description && <div className="hub-project-desc">{p.description}</div>}
              {p.forked_from && (
                <div className="hub-forked">forked from {p.forked_from}</div>
              )}
              <button className="hub-fork-btn" onClick={() => fork(p)}>Fork</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
