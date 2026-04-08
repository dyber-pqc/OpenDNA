import { useEffect, useState, useCallback } from "react";
import {
  listComponents,
  installComponent,
  uninstallComponent,
  getComponentJob,
} from "../../api/client";
import type { ComponentInfo, ComponentJob } from "../../api/client";
import "./ComponentManager.css";

const CATEGORY_ORDER = ["folding", "multimer", "design", "docking", "md", "qm", "llm"];
const CATEGORY_LABELS: Record<string, string> = {
  folding: "🧬 Folding",
  multimer: "🔗 Multimer",
  design: "🎨 Design",
  docking: "💊 Docking",
  md: "⚛️ Molecular Dynamics",
  qm: "🔬 Quantum Chemistry",
  llm: "🤖 Local AI",
};

interface Props {
  onClose?: () => void;
}

export default function ComponentManager({ onClose }: Props) {
  const [components, setComponents] = useState<ComponentInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeJobs, setActiveJobs] = useState<Record<string, ComponentJob>>({});
  const [activeTab, setActiveTab] = useState<string>("folding");

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const data = await listComponents();
      setComponents(data.components);
      setError(null);
    } catch (e: any) {
      setError(e.message || "Failed to load components");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  // Poll active install jobs
  useEffect(() => {
    const ids = Object.entries(activeJobs)
      .filter(([, j]) => j.status === "running")
      .map(([id]) => id);
    if (ids.length === 0) return;
    const t = setInterval(async () => {
      for (const id of ids) {
        try {
          const job = await getComponentJob(id);
          setActiveJobs(prev => ({ ...prev, [id]: job }));
          if (job.status !== "running") refresh();
        } catch { /* swallow */ }
      }
    }, 1500);
    return () => clearInterval(t);
  }, [activeJobs, refresh]);

  const handleInstall = async (name: string) => {
    try {
      const res = await installComponent(name);
      setActiveJobs(prev => ({
        ...prev,
        [res.job_id]: { component: name, status: "running", progress: 0, messages: [] },
      }));
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleUninstall = async (name: string) => {
    if (!confirm(`Uninstall ${name}?`)) return;
    try {
      await uninstallComponent(name);
      refresh();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const jobForComponent = (name: string): ComponentJob | null => {
    for (const j of Object.values(activeJobs)) {
      if (j.component === name && j.status === "running") return j;
    }
    return null;
  };

  const byCategory: Record<string, ComponentInfo[]> = {};
  for (const c of components) {
    (byCategory[c.category] ||= []).push(c);
  }
  const categories = CATEGORY_ORDER.filter(c => byCategory[c]?.length);

  const installedCount = components.filter(c => c.status === "installed").length;
  const totalSize = components
    .filter(c => c.status === "installed")
    .reduce((s, c) => s + c.size_mb, 0);

  return (
    <div className="component-manager">
      <div className="cm-header">
        <div>
          <h2>Component Manager</h2>
          <p className="cm-subtitle">
            Install the heavy ML models and physics engines you need. Keep the ones you don't uninstalled to save disk.
          </p>
        </div>
        {onClose && <button className="cm-close" onClick={onClose}>✕</button>}
      </div>

      <div className="cm-summary">
        <span><strong>{installedCount}</strong> / {components.length} installed</span>
        <span><strong>{(totalSize / 1024).toFixed(1)}</strong> GB on disk</span>
        <button className="cm-refresh" onClick={refresh}>↻ Refresh</button>
      </div>

      {error && <div className="cm-error">{error}</div>}
      {loading && components.length === 0 && <div className="cm-loading">Loading components…</div>}

      <div className="cm-tabs">
        {categories.map(cat => (
          <button
            key={cat}
            className={`cm-tab ${activeTab === cat ? "active" : ""}`}
            onClick={() => setActiveTab(cat)}
          >
            {CATEGORY_LABELS[cat] || cat}
            <span className="cm-tab-count">{byCategory[cat].length}</span>
          </button>
        ))}
      </div>

      <div className="cm-list">
        {(byCategory[activeTab] || []).map(comp => {
          const job = jobForComponent(comp.name);
          const installed = comp.status === "installed";
          return (
            <div key={comp.name} className={`cm-card ${installed ? "installed" : ""}`}>
              <div className="cm-card-main">
                <div className="cm-card-title">
                  {comp.display_name}
                  <span className="cm-card-version">v{comp.version}</span>
                  {installed && <span className="cm-badge-ok">✓ Installed</span>}
                </div>
                <div className="cm-card-desc">{comp.description}</div>
                <div className="cm-card-meta">
                  <span>{(comp.size_mb / 1024).toFixed(1)} GB</span>
                  {comp.license && <span>{comp.license}</span>}
                  {comp.homepage && (
                    <a href={comp.homepage} target="_blank" rel="noreferrer">homepage ↗</a>
                  )}
                </div>
                {job && (
                  <div className="cm-progress">
                    <div
                      className="cm-progress-bar"
                      style={{ width: `${Math.max(5, job.progress * 100)}%` }}
                    />
                    <div className="cm-progress-msg">
                      {job.messages[job.messages.length - 1] || "Installing…"}
                    </div>
                  </div>
                )}
              </div>
              <div className="cm-card-actions">
                {installed ? (
                  <button className="cm-btn cm-btn-danger" onClick={() => handleUninstall(comp.name)}>
                    Uninstall
                  </button>
                ) : job ? (
                  <button className="cm-btn" disabled>Installing…</button>
                ) : (
                  <button className="cm-btn cm-btn-primary" onClick={() => handleInstall(comp.name)}>
                    Install
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
