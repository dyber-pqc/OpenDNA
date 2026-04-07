import { useEffect, useState } from "react";
import * as api from "../../api/client";
import "./Dashboard.css";

interface DashboardProps {
  structures: number;
  onClose: () => void;
}

export default function Dashboard({ structures, onClose }: DashboardProps) {
  const [hardware, setHardware] = useState<any>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);

  useEffect(() => {
    api.getHardware().then(setHardware).catch(() => {});
    api.listJobs().then((d) => setJobs(d.jobs)).catch(() => {});
    api.listProjects().then((d) => setProjects(d.projects)).catch(() => {});
  }, []);

  const completedJobs = jobs.filter((j) => j.status === "completed").length;
  const failedJobs = jobs.filter((j) => j.status === "failed").length;
  const runningJobs = jobs.filter((j) => j.status === "running").length;

  return (
    <div className="dashboard">
      <div className="dash-header">
        <h2>OpenDNA Dashboard</h2>
        <button className="dash-close" onClick={onClose}>×</button>
      </div>

      <div className="dash-grid">
        <div className="dash-card">
          <div className="dash-stat">{structures}</div>
          <div className="dash-label">Structures in session</div>
        </div>
        <div className="dash-card">
          <div className="dash-stat">{completedJobs}</div>
          <div className="dash-label">Jobs completed</div>
        </div>
        <div className="dash-card">
          <div className="dash-stat">{runningJobs}</div>
          <div className="dash-label">Running</div>
        </div>
        <div className="dash-card">
          <div className="dash-stat">{failedJobs}</div>
          <div className="dash-label">Failed</div>
        </div>
        <div className="dash-card">
          <div className="dash-stat">{projects.length}</div>
          <div className="dash-label">Saved projects</div>
        </div>
      </div>

      {hardware && (
        <div className="dash-section">
          <h3>Hardware</h3>
          <table className="dash-table">
            <tbody>
              <tr><td>CPU</td><td>{hardware.cpu}</td></tr>
              <tr><td>Cores</td><td>{hardware.cores}</td></tr>
              <tr><td>RAM</td><td>{hardware.ram_gb} GB</td></tr>
              <tr><td>GPU</td><td>{hardware.gpu ? `${hardware.gpu.name} (${hardware.gpu.vram_gb} GB)` : "None"}</td></tr>
              <tr><td>Backend</td><td>{hardware.recommended_backend}</td></tr>
              <tr><td>Tier</td><td>{hardware.recommended_tier}</td></tr>
            </tbody>
          </table>
        </div>
      )}

      <div className="dash-section">
        <h3>Recent Jobs</h3>
        {jobs.length === 0 ? (
          <p className="dash-empty">No jobs yet</p>
        ) : (
          <table className="dash-table">
            <thead>
              <tr><th>ID</th><th>Type</th><th>Status</th><th>Progress</th></tr>
            </thead>
            <tbody>
              {jobs.slice(0, 10).map((j) => (
                <tr key={j.id}>
                  <td className="mono">{j.id}</td>
                  <td>{j.type}</td>
                  <td><span className={`status ${j.status}`}>{j.status}</span></td>
                  <td>{Math.round(j.progress * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {projects.length > 0 && (
        <div className="dash-section">
          <h3>Saved Projects</h3>
          <table className="dash-table">
            <thead>
              <tr><th>Name</th><th>Structures</th><th>Saved</th></tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.name}>
                  <td>{p.name}</td>
                  <td>{p.structures}</td>
                  <td className="mono">{p.saved_at?.slice(0, 16)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
