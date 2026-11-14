import { useMemo, useState } from "react";
import * as api from "../../api/client";
import "./PlasmidMap.css";

interface PlasmidMapProps {
  initialSequence?: string;
  onClose: () => void;
}

const FEATURE_COLORS: Record<string, string> = {
  promoter: "#f59e0b",
  RBS: "#10b981",
  CDS_start: "#8b5cf6",
  tag: "#ec4899",
  linker: "#6b7280",
  CDS: "#3b82f6",
  terminator: "#ef4444",
  rep_origin: "#14b8a6",
  resistance: "#a855f7",
  misc_feature: "#64748b",
};

function polar(cx: number, cy: number, r: number, angleDeg: number): [number, number] {
  const a = ((angleDeg - 90) * Math.PI) / 180.0;
  return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
}

function arcPath(cx: number, cy: number, r: number, startAngle: number, endAngle: number, thickness: number): string {
  const outerR = r + thickness / 2;
  const innerR = r - thickness / 2;
  const [sx, sy] = polar(cx, cy, outerR, endAngle);
  const [ex, ey] = polar(cx, cy, outerR, startAngle);
  const [sx2, sy2] = polar(cx, cy, innerR, startAngle);
  const [ex2, ey2] = polar(cx, cy, innerR, endAngle);
  const large = endAngle - startAngle <= 180 ? 0 : 1;
  return `M ${sx} ${sy} A ${outerR} ${outerR} 0 ${large} 0 ${ex} ${ey} L ${sx2} ${sy2} A ${innerR} ${innerR} 0 ${large} 1 ${ex2} ${ey2} Z`;
}

function PlasmidMap({ initialSequence = "", onClose }: PlasmidMapProps) {
  const [sequence, setSequence] = useState(initialSequence);
  const [vector, setVector] = useState("pET28a");
  const [tag, setTag] = useState("His6");
  const [result, setResult] = useState<api.PlasmidResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [hover, setHover] = useState<api.PlasmidFeature | null>(null);

  const cx = 220, cy = 220, radius = 150, thickness = 22;

  const arcs = useMemo(() => {
    if (!result) return [];
    const total = result.length;
    return result.features.map((f) => {
      const startAngle = (f.start / total) * 360;
      const endAngle = (f.end / total) * 360;
      const midAngle = (startAngle + endAngle) / 2;
      const [lx, ly] = polar(cx, cy, radius + 28, midAngle);
      const [px, py] = polar(cx, cy, radius + thickness / 2 + 2, midAngle);
      return {
        feature: f,
        d: arcPath(cx, cy, radius, startAngle, endAngle, thickness),
        labelX: lx,
        labelY: ly,
        pinX: px,
        pinY: py,
        color: FEATURE_COLORS[f.type] || "#888",
      };
    });
  }, [result]);

  const run = async () => {
    setBusy(true);
    setErr(null);
    try {
      const r = await api.plasmidGenerate(sequence, vector, tag, "T7");
      setResult(r);
    } catch (e: any) {
      setErr(e.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  const download = () => {
    if (!result) return;
    const blob = new Blob([result.genbank], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${vector}_${tag}_construct.gb`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="pm-modal" onClick={(e) => e.stopPropagation()}>
        <div className="pm-header">
          <h3>Plasmid Map Generator</h3>
          <button className="header-btn small" onClick={onClose}>Close</button>
        </div>

        <div className="pm-controls">
          <label className="pm-label">Protein sequence</label>
          <textarea
            className="pm-textarea"
            value={sequence}
            onChange={(e) => setSequence(e.target.value.toUpperCase().replace(/[^A-Z]/g, ""))}
            rows={3}
            placeholder="MKTAYIAKQRQISFVK..."
          />
          <div className="pm-row">
            <div>
              <label className="pm-label">Vector</label>
              <select className="pm-select" value={vector} onChange={(e) => setVector(e.target.value)}>
                <option value="pET28a">pET28a</option>
                <option value="pUC19">pUC19</option>
              </select>
            </div>
            <div>
              <label className="pm-label">Tag</label>
              <select className="pm-select" value={tag} onChange={(e) => setTag(e.target.value)}>
                <option value="His6">His6</option>
                <option value="His8">His8</option>
                <option value="FLAG">FLAG</option>
                <option value="Myc">Myc</option>
                <option value="HA">HA</option>
                <option value="StrepII">StrepII</option>
                <option value="none">none</option>
              </select>
            </div>
            <button className="pm-run" disabled={busy || !sequence} onClick={run}>
              {busy ? "Generating..." : "Generate plasmid"}
            </button>
          </div>
        </div>

        {err && <div className="pm-error">{err}</div>}

        {result && (
          <>
            <div className="pm-meta">
              <b>{vector}_{tag}</b> | {result.length} bp | {result.features.length} features
              <button className="pm-download" onClick={download}>Download GenBank</button>
            </div>
            <div className="pm-mapwrap">
              <svg width={440} height={440} viewBox="0 0 440 440">
                <circle cx={cx} cy={cy} r={radius} fill="none" stroke="#333" strokeWidth={1} strokeDasharray="2,2" />
                {arcs.map((a, i) => (
                  <g key={i}>
                    <path
                      d={a.d}
                      fill={a.color}
                      stroke="#000"
                      strokeWidth={0.5}
                      onMouseEnter={() => setHover(a.feature)}
                      onMouseLeave={() => setHover(null)}
                      style={{ cursor: "pointer", opacity: hover && hover.name !== a.feature.name ? 0.4 : 1 }}
                    />
                    <line x1={a.pinX} y1={a.pinY} x2={a.labelX} y2={a.labelY} stroke={a.color} strokeWidth={0.8} />
                    <text x={a.labelX} y={a.labelY} fill="#ddd" fontSize={10} textAnchor={a.labelX > cx ? "start" : "end"} dominantBaseline="middle">
                      {a.feature.name}
                    </text>
                  </g>
                ))}
                <text x={cx} y={cy - 6} fill="#ccc" fontSize={13} textAnchor="middle">{vector}_{tag}</text>
                <text x={cx} y={cy + 12} fill="#888" fontSize={11} textAnchor="middle">{result.length} bp</text>
              </svg>
              {hover && (
                <div className="pm-tooltip">
                  <div><b>{hover.name}</b></div>
                  <div>type: {hover.type}</div>
                  <div>pos: {hover.start}..{hover.end}</div>
                  <div>strand: {hover.strand > 0 ? "+" : "-"}</div>
                  <div>length: {hover.end - hover.start + 1} bp</div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default PlasmidMap;
