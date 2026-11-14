import { useEffect, useState } from "react";
import * as api from "../../api/client";
import "./HardwarePanel.css";

interface BenchmarkRow {
  hardware: string;
  fold_seconds: number;
  matchKey: string;
}

const BENCHMARKS: BenchmarkRow[] = [
  { hardware: "RTX 4090", fold_seconds: 3, matchKey: "4090" },
  { hardware: "RTX 4080", fold_seconds: 4, matchKey: "4080" },
  { hardware: "RTX 3090", fold_seconds: 5, matchKey: "3090" },
  { hardware: "RTX 3060", fold_seconds: 10, matchKey: "3060" },
  { hardware: "Apple M2 Max", fold_seconds: 8, matchKey: "m2 max" },
  { hardware: "Apple M2", fold_seconds: 14, matchKey: "m2" },
  { hardware: "Apple M1", fold_seconds: 18, matchKey: "m1" },
  { hardware: "CPU only", fold_seconds: 120, matchKey: "__cpu__" },
];

interface HardwarePanelProps {
  onClose: () => void;
}

export default function HardwarePanel({ onClose }: HardwarePanelProps) {
  const [hardware, setHardware] = useState<any>(null);
  const [gpu, setGpu] = useState<any>(null);
  const [components, setComponents] = useState<any[]>([]);
  const [networkOk, setNetworkOk] = useState<boolean | null>(null);
  const [diskFree, setDiskFree] = useState<number | null>(null);

  useEffect(() => {
    api.getHardware().then(setHardware).catch(() => {});
    api.gpuInfo().then(setGpu).catch(() => setGpu(null));
    api.listComponents().then((d: any) => setComponents(d?.components || d || [])).catch(() => {});

    // Quick network check via cloudflare
    fetch("https://1.1.1.1/cdn-cgi/trace", { mode: "no-cors" })
      .then(() => setNetworkOk(true))
      .catch(() => setNetworkOk(false));

    // Disk free: navigator.storage.estimate is the closest browser-side approximation
    if (navigator.storage?.estimate) {
      navigator.storage.estimate().then((est) => {
        if (est.quota && est.usage !== undefined) {
          setDiskFree((est.quota - est.usage) / (1024 ** 3));
        }
      }).catch(() => {});
    }
  }, []);

  const gpuName = (hardware?.gpu?.name || gpu?.name || "").toLowerCase();
  const matchedRow = BENCHMARKS.find((b) =>
    gpuName ? gpuName.includes(b.matchKey) : b.matchKey === "__cpu__"
  );

  // Recommendations
  const recommendations: string[] = [];
  const vram = hardware?.gpu?.vram_gb || gpu?.vram_total_gb || 0;
  if (!hardware?.gpu) {
    recommendations.push(
      "No GPU detected. Adding any NVIDIA GPU with 8GB+ VRAM (e.g. RTX 3060) will give roughly a 20x speedup over CPU folding."
    );
  } else if (vram < 8) {
    recommendations.push(
      `Your GPU has only ${vram} GB VRAM. Upgrading to a 12GB+ card unlocks larger models like ESMFold-3B.`
    );
  } else if (gpuName.includes("3060") || gpuName.includes("2060") || gpuName.includes("1660")) {
    recommendations.push(
      "An RTX 4090 would give you roughly 5x the throughput of your current GPU and run Boltz-1 comfortably."
    );
  } else if (gpuName.includes("4090")) {
    recommendations.push(
      "You're already at the top of the consumer stack. Multi-GPU setups give the next big jump for batch jobs."
    );
  }
  if ((hardware?.ram_gb || 0) < 16) {
    recommendations.push("Add more RAM - 32 GB is the comfortable minimum for ESMFold on CPU.");
  }
  if (diskFree !== null && diskFree < 5) {
    recommendations.push("Free some disk space - large model checkpoints need ~10 GB headroom.");
  }
  if (recommendations.length === 0) {
    recommendations.push("Your hardware is well-balanced for current OpenDNA workloads. Nothing to upgrade right now.");
  }

  return (
    <div className="hardware-panel">
      <div className="hp-header">
        <h2>⚡ Hardware</h2>
        <button className="hp-close" onClick={onClose}>×</button>
      </div>

      <div className="hp-grid">
        <div className="hp-card">
          <h3>CPU</h3>
          <div className="hp-row"><span>Name</span><strong>{hardware?.cpu || "—"}</strong></div>
          <div className="hp-row"><span>Cores</span><strong>{hardware?.cores ?? "—"}</strong></div>
          <div className="hp-row"><span>Threads</span><strong>{hardware?.threads ?? hardware?.cores ?? "—"}</strong></div>
        </div>

        <div className="hp-card">
          <h3>GPU</h3>
          <div className="hp-row"><span>Name</span><strong>{hardware?.gpu?.name || "None detected"}</strong></div>
          <div className="hp-row">
            <span>VRAM</span>
            <strong>
              {gpu?.vram_used_gb !== undefined && gpu?.vram_total_gb
                ? `${gpu.vram_used_gb.toFixed(1)} / ${gpu.vram_total_gb.toFixed(1)} GB`
                : hardware?.gpu?.vram_gb
                ? `${hardware.gpu.vram_gb} GB`
                : "—"}
            </strong>
          </div>
          <div className="hp-row"><span>Backend</span><strong>{hardware?.gpu?.backend || hardware?.recommended_backend || "cpu"}</strong></div>
        </div>

        <div className="hp-card">
          <h3>Memory & Storage</h3>
          <div className="hp-row"><span>RAM total</span><strong>{hardware?.ram_gb ? `${hardware.ram_gb} GB` : "—"}</strong></div>
          <div className="hp-row"><span>RAM available</span><strong>{hardware?.ram_available_gb ? `${hardware.ram_available_gb} GB` : "—"}</strong></div>
          <div className="hp-row"><span>Disk free (~/.opendna)</span><strong>{diskFree !== null ? `${diskFree.toFixed(1)} GB` : "—"}</strong></div>
        </div>

        <div className="hp-card">
          <h3>Network</h3>
          <div className="hp-row">
            <span>Reachable</span>
            <strong className={networkOk ? "ok" : networkOk === false ? "bad" : ""}>
              {networkOk === null ? "checking..." : networkOk ? "✓ online" : "✗ offline"}
            </strong>
          </div>
        </div>
      </div>

      <div className="hp-section">
        <h3>Installed components</h3>
        {components.length === 0 ? (
          <p className="hp-empty">No components reported.</p>
        ) : (
          <ul className="hp-components">
            {components.map((c: any) => (
              <li key={c.name || c.id}>
                <span className={`hp-dot ${c.installed ? "on" : "off"}`} />
                {c.name || c.id}
                {c.category && <em> · {c.category}</em>}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="hp-section">
        <h3>Benchmark - fold ubiquitin (76 aa)</h3>
        <table className="hp-table">
          <thead>
            <tr><th>Hardware</th><th>Estimated time</th></tr>
          </thead>
          <tbody>
            {BENCHMARKS.map((b) => (
              <tr key={b.hardware} className={matchedRow?.hardware === b.hardware ? "matched" : ""}>
                <td>{b.hardware}</td>
                <td>{b.fold_seconds}s</td>
              </tr>
            ))}
          </tbody>
        </table>
        {matchedRow && (
          <p className="hp-note">
            Highlighted row is your detected hardware. Times are rough estimates from community benchmarks.
          </p>
        )}
      </div>

      <div className="hp-section">
        <h3>What should I upgrade?</h3>
        <ul className="hp-recommendations">
          {recommendations.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
