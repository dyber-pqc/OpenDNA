import { useEffect, useState } from "react";
import "./ProjectTemplates.css";

const API_BASE = "http://localhost:8765";

interface TemplateListItem {
  id: string;
  name: string;
  description: string;
  academy_level: number;
  tags: string[];
  has_starter_sequence: boolean;
  starter_pdb_id: string | null;
  starter_uniprot_id: string | null;
}

interface Props {
  userId?: string;
  onClose: () => void;
  onInstantiated: (args: {
    templateId: string;
    projectId: string;
    starterSequence: string;
    payload: any;
  }) => void;
}

const TEMPLATE_ICONS: Record<string, string> = {
  cancer_binder: "🎯",
  antibody_optimization: "🧬",
  enzyme_engineering: "⚗️",
  de_novo_mini: "✨",
  membrane_sensor: "💡",
  peptide_drug: "💊",
};

export default function ProjectTemplates({ userId, onClose, onInstantiated }: Props) {
  const [templates, setTemplates] = useState<TemplateListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(`${API_BASE}/v1/templates`);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = await r.json();
        if (!cancelled) setTemplates(data.templates || []);
      } catch (e: any) {
        if (!cancelled) setErr(String(e?.message || e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const use = async (t: TemplateListItem) => {
    setBusy(t.id);
    setErr(null);
    try {
      const projectId = `${t.id}_${Date.now().toString(36)}`;
      const r = await fetch(`${API_BASE}/v1/templates/${t.id}/instantiate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId || "anonymous",
          project_id: projectId,
        }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      const starter = data?.payload?.starter_sequence || "";
      onInstantiated({
        templateId: t.id,
        projectId,
        starterSequence: starter,
        payload: data?.payload || {},
      });
      onClose();
    } catch (e: any) {
      setErr(String(e?.message || e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="proj-templates-backdrop" onClick={onClose}>
      <div className="proj-templates-modal" onClick={(e) => e.stopPropagation()}>
        <header className="proj-templates-header">
          <h2>📋 Project Templates</h2>
          <button className="proj-templates-close" onClick={onClose} title="Close">
            ✕
          </button>
        </header>
        <p className="proj-templates-sub">
          Start from a ready-made protein engineering scenario. Each template pre-loads a
          starter sequence and a runnable workflow graph.
        </p>
        {loading && <div className="proj-templates-loading">Loading templates...</div>}
        {err && <div className="proj-templates-err">Error: {err}</div>}
        <div className="proj-templates-grid">
          {templates.map((t) => (
            <div key={t.id} className="proj-template-card">
              <div className="proj-template-icon">{TEMPLATE_ICONS[t.id] || "📦"}</div>
              <div className="proj-template-name">{t.name}</div>
              <div className="proj-template-desc">{t.description}</div>
              <div className="proj-template-tags">
                {t.tags.slice(0, 4).map((tag) => (
                  <span key={tag} className="proj-template-tag">
                    {tag}
                  </span>
                ))}
                <span className="proj-template-level">Lvl {t.academy_level}</span>
              </div>
              <button
                className="proj-template-use"
                disabled={busy !== null}
                onClick={() => use(t)}
              >
                {busy === t.id ? "Loading..." : "Use this template"}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
