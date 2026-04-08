import { useMemo, useState } from "react";
import "./Ramachandran.css";

interface Props {
  pdb_string: string;
  onResidueClick?: (residue_number: number) => void;
  onClose?: () => void;
}

interface Atom {
  chain: string;
  resnum: number;
  name: string;
  x: number;
  y: number;
  z: number;
}

interface PhiPsi {
  resnum: number;
  chain: string;
  phi: number;
  psi: number;
}

type Vec3 = [number, number, number];

const sub = (a: Vec3, b: Vec3): Vec3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const cross = (a: Vec3, b: Vec3): Vec3 => [
  a[1] * b[2] - a[2] * b[1],
  a[2] * b[0] - a[0] * b[2],
  a[0] * b[1] - a[1] * b[0],
];
const dot = (a: Vec3, b: Vec3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const norm = (a: Vec3) => Math.sqrt(dot(a, a));
const scale = (a: Vec3, s: number): Vec3 => [a[0] * s, a[1] * s, a[2] * s];

function dihedral(p1: Vec3, p2: Vec3, p3: Vec3, p4: Vec3): number {
  const b1 = sub(p2, p1);
  const b2 = sub(p3, p2);
  const b3 = sub(p4, p3);
  const n1 = cross(b1, b2);
  const n2 = cross(b2, b3);
  const m1 = cross(n1, scale(b2, 1 / norm(b2)));
  const x = dot(n1, n2);
  const y = dot(m1, n2);
  return (Math.atan2(y, x) * 180) / Math.PI;
}

function parsePdbBackbone(pdb: string): Atom[] {
  const atoms: Atom[] = [];
  for (const line of pdb.split("\n")) {
    if (!line.startsWith("ATOM")) continue;
    if (line.length < 54) continue;
    const name = line.substring(12, 16).trim();
    if (name !== "N" && name !== "CA" && name !== "C") continue;
    const chain = line.substring(21, 22);
    const resnum = parseInt(line.substring(22, 26).trim(), 10);
    const x = parseFloat(line.substring(30, 38).trim());
    const y = parseFloat(line.substring(38, 46).trim());
    const z = parseFloat(line.substring(46, 54).trim());
    if (isNaN(resnum) || isNaN(x)) continue;
    atoms.push({ chain, resnum, name, x, y, z });
  }
  return atoms;
}

function computePhiPsi(atoms: Atom[]): PhiPsi[] {
  // Group atoms by chain+resnum -> {N, CA, C}
  const byKey = new Map<string, { N?: Atom; CA?: Atom; C?: Atom; chain: string; resnum: number }>();
  for (const a of atoms) {
    const k = `${a.chain}:${a.resnum}`;
    if (!byKey.has(k)) byKey.set(k, { chain: a.chain, resnum: a.resnum });
    const r = byKey.get(k)!;
    (r as any)[a.name] = a;
  }
  const sorted = Array.from(byKey.values()).sort((a, b) => {
    if (a.chain !== b.chain) return a.chain.localeCompare(b.chain);
    return a.resnum - b.resnum;
  });
  const out: PhiPsi[] = [];
  for (let i = 1; i < sorted.length - 1; i++) {
    const prev = sorted[i - 1];
    const curr = sorted[i];
    const next = sorted[i + 1];
    if (prev.chain !== curr.chain || curr.chain !== next.chain) continue;
    if (prev.resnum + 1 !== curr.resnum || curr.resnum + 1 !== next.resnum) continue;
    if (!prev.C || !curr.N || !curr.CA || !curr.C || !next.N) continue;
    const p1: Vec3 = [prev.C.x, prev.C.y, prev.C.z];
    const p2: Vec3 = [curr.N.x, curr.N.y, curr.N.z];
    const p3: Vec3 = [curr.CA.x, curr.CA.y, curr.CA.z];
    const p4: Vec3 = [curr.C.x, curr.C.y, curr.C.z];
    const p5: Vec3 = [next.N.x, next.N.y, next.N.z];
    const phi = dihedral(p1, p2, p3, p4);
    const psi = dihedral(p2, p3, p4, p5);
    out.push({ resnum: curr.resnum, chain: curr.chain, phi, psi });
  }
  return out;
}

const SIZE = 360;
// Map phi/psi (-180..180) to SVG (0..SIZE), psi axis flipped (positive psi up).
const x = (phi: number) => ((phi + 180) / 360) * SIZE;
const y = (psi: number) => SIZE - ((psi + 180) / 360) * SIZE;

export default function Ramachandran({ pdb_string, onResidueClick, onClose }: Props) {
  const [hover, setHover] = useState<PhiPsi | null>(null);

  const phiPsi = useMemo(() => {
    if (!pdb_string) return [];
    try {
      return computePhiPsi(parsePdbBackbone(pdb_string));
    } catch {
      return [];
    }
  }, [pdb_string]);

  return (
    <div className="rama-panel">
      <div className="rama-header">
        <h2>Ramachandran plot</h2>
        {onClose && <button onClick={onClose}>✕</button>}
      </div>
      <div className="rama-meta">
        {phiPsi.length} residues plotted (excluding chain termini)
      </div>
      <div className="rama-body">
        <svg width={SIZE} height={SIZE} className="rama-svg">
          {/* Background */}
          <rect x={0} y={0} width={SIZE} height={SIZE} fill="#0e1224" />

          {/* Beta sheet region (upper-left) */}
          <ellipse cx={x(-120)} cy={y(130)} rx={60} ry={45} fill="#5a8a5a" opacity={0.35} />
          {/* Right-handed alpha helix region (lower-left) */}
          <ellipse cx={x(-65)} cy={y(-40)} rx={45} ry={35} fill="#7aa2ff" opacity={0.4} />
          {/* Left-handed alpha helix (upper-right small) */}
          <ellipse cx={x(60)} cy={y(45)} rx={25} ry={20} fill="#c47aff" opacity={0.35} />
          {/* Generic loop region (broader light) */}
          <ellipse cx={x(-90)} cy={y(0)} rx={120} ry={90} fill="#888" opacity={0.08} />

          {/* Axes */}
          <line x1={x(0)} y1={0} x2={x(0)} y2={SIZE} stroke="#444" strokeWidth={1} />
          <line x1={0} y1={y(0)} x2={SIZE} y2={y(0)} stroke="#444" strokeWidth={1} />
          <rect x={0} y={0} width={SIZE} height={SIZE} fill="none" stroke="#555" strokeWidth={1} />

          {/* Tick labels */}
          {[-180, -90, 0, 90, 180].map(v => (
            <g key={`xt${v}`}>
              <line x1={x(v)} y1={SIZE} x2={x(v)} y2={SIZE - 4} stroke="#888" />
              <text x={x(v)} y={SIZE - 6} fontSize={9} fill="#888" textAnchor="middle">{v}</text>
            </g>
          ))}
          {[-180, -90, 0, 90, 180].map(v => (
            <g key={`yt${v}`}>
              <line x1={0} y1={y(v)} x2={4} y2={y(v)} stroke="#888" />
              <text x={6} y={y(v) + 3} fontSize={9} fill="#888">{v}</text>
            </g>
          ))}

          {/* Axis labels */}
          <text x={SIZE / 2} y={SIZE - 18} fontSize={11} fill="#bbb" textAnchor="middle">φ (phi)</text>
          <text x={14} y={14} fontSize={11} fill="#bbb">ψ (psi)</text>

          {/* Residue dots */}
          {phiPsi.map(p => (
            <circle
              key={`${p.chain}:${p.resnum}`}
              cx={x(p.phi)}
              cy={y(p.psi)}
              r={3}
              fill="#ffd47a"
              stroke="#1a1a2a"
              strokeWidth={0.5}
              className="rama-dot"
              onMouseEnter={() => setHover(p)}
              onMouseLeave={() => setHover(null)}
              onClick={() => onResidueClick?.(p.resnum)}
            />
          ))}
        </svg>

        <div className="rama-legend">
          <div><span className="sw" style={{ background: "#7aa2ff", opacity: 0.7 }} /> α-helix (right)</div>
          <div><span className="sw" style={{ background: "#5a8a5a", opacity: 0.7 }} /> β-sheet</div>
          <div><span className="sw" style={{ background: "#c47aff", opacity: 0.7 }} /> α-helix (left)</div>
          <div><span className="sw" style={{ background: "#888", opacity: 0.3 }} /> loop / other</div>
          {hover && (
            <div className="rama-hover">
              <strong>{hover.chain}:{hover.resnum}</strong><br />
              φ = {hover.phi.toFixed(1)}°<br />
              ψ = {hover.psi.toFixed(1)}°<br />
              <em>(click to select)</em>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
