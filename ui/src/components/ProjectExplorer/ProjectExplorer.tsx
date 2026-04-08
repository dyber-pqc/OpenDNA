import { useEffect, useState } from "react";
import "./ProjectExplorer.css";

const API_BASE = "http://localhost:8765";

interface NotebookEntry {
  id?: string;
  entry_id?: string;
  title: string;
  body_md?: string;
  created?: string;
  created_at?: string;
  tags?: string[];
}

interface ProvNode {
  id: string;
  kind: string;
  ts: number;
  inputs?: any;
  outputs?: any;
}

interface AttachmentInfo {
  name: string;
  size: number;
}

interface Props {
  projectId?: string;
  onClose: () => void;
}

export default function ProjectExplorer({ projectId = "default", onClose }: Props) {
  const [entries, setEntries] = useState<NotebookEntry[]>([]);
  const [provNodes, setProvNodes] = useState<ProvNode[]>([]);
  const [attachments, setAttachments] = useState<AttachmentInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openEntry, setOpenEntry] = useState<NotebookEntry | null>(null);
  const [expand, setExpand] = useState<Record<string, boolean>>({
    notebook: true,
    prov: true,
    attach: true,
  });

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.allSettled([
      fetch(`${API_BASE}/v1/notebook/${projectId}/entries`).then((r) => r.json()),
      fetch(`${API_BASE}/v1/provenance/${projectId}`).then((r) => r.json()),
      fetch(`${API_BASE}/v1/notebook/${projectId}/attachments`).then((r) => r.json()),
    ])
      .then(([nb, prov, att]) => {
        if (cancelled) return;
        if (nb.status === "fulfilled") setEntries(nb.value?.entries || []);
        if (prov.status === "fulfilled") setProvNodes(prov.value?.nodes || []);
        if (att.status === "fulfilled") setAttachments(att.value?.attachments || []);
        if (nb.status === "rejected" && prov.status === "rejected" && att.status === "rejected") {
          setError("Backend not reachable");
        }
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const toggle = (k: string) => setExpand((e) => ({ ...e, [k]: !e[k] }));

  const provByKind: Record<string, ProvNode[]> = {};
  for (const n of provNodes) {
    (provByKind[n.kind] ||= []).push(n);
  }

  return (
    <aside className="pex-root">
      <div className="pex-header">
        <span className="pex-title">🗂️ Project Explorer</span>
        <button className="pex-close" onClick={onClose} title="Close">×</button>
      </div>
      <div className="pex-project">project: <code>{projectId}</code></div>

      {loading && <div className="pex-msg">Loading…</div>}
      {error && <div className="pex-error">{error}</div>}

      <div className="pex-section">
        <div className="pex-section-head" onClick={() => toggle("notebook")}>
          <span>{expand.notebook ? "▾" : "▸"}</span> 📓 Notebook entries ({entries.length})
        </div>
        {expand.notebook && (
          <div className="pex-list">
            {entries.length === 0 && <div className="pex-empty">No entries</div>}
            {entries.map((e) => (
              <div
                key={e.id || e.entry_id || e.title}
                className="pex-item"
                onClick={() => setOpenEntry(e)}
                title={e.title}
              >
                {e.title || "(untitled)"}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="pex-section">
        <div className="pex-section-head" onClick={() => toggle("prov")}>
          <span>{expand.prov ? "▾" : "▸"}</span> 🔗 Provenance ({provNodes.length})
        </div>
        {expand.prov && (
          <div className="pex-list">
            {Object.keys(provByKind).length === 0 && <div className="pex-empty">No nodes</div>}
            {Object.entries(provByKind).map(([kind, nodes]) => (
              <div key={kind} className="pex-prov-group">
                <div className="pex-prov-kind">{kind} ({nodes.length})</div>
                {nodes.map((n) => (
                  <div key={n.id} className="pex-item pex-sub" title={n.id}>
                    {n.id.slice(0, 12)}
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="pex-section">
        <div className="pex-section-head" onClick={() => toggle("attach")}>
          <span>{expand.attach ? "▾" : "▸"}</span> 📎 Attachments ({attachments.length})
        </div>
        {expand.attach && (
          <div className="pex-list">
            {attachments.length === 0 && <div className="pex-empty">No attachments</div>}
            {attachments.map((a) => (
              <div key={a.name} className="pex-item" title={`${a.size} bytes`}>
                {a.name}
              </div>
            ))}
          </div>
        )}
      </div>

      {openEntry && (
        <div className="pex-preview">
          <div className="pex-preview-head">
            <strong>{openEntry.title}</strong>
            <button onClick={() => setOpenEntry(null)}>×</button>
          </div>
          <pre className="pex-preview-body">{openEntry.body_md || "(empty)"}</pre>
        </div>
      )}
    </aside>
  );
}
