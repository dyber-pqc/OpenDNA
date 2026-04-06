import { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar/Sidebar";
import ProteinViewer from "./components/ProteinViewer/ProteinViewer";
import ChatPanel from "./components/ChatPanel/ChatPanel";
import JobMonitor from "./components/JobMonitor/JobMonitor";
import * as api from "./api/client";
import "./App.css";

interface Job {
  id: string;
  type: string;
  status: string;
  progress: number;
}

export interface StoredStructure {
  id: string;
  label: string;
  sequence: string;
  pdbData: string;
  meanConfidence: number;
}

interface DesignCandidate {
  rank: number;
  sequence: string;
  score: number;
  recovery: number;
}

function App() {
  const [structures, setStructures] = useState<StoredStructure[]>([]);
  const [activeStructureId, setActiveStructureId] = useState<string | null>(null);
  const [compareStructureId, setCompareStructureId] = useState<string | null>(null);
  const [score, setScore] = useState<api.ScoreData | null>(null);
  const [designResults, setDesignResults] = useState<DesignCandidate[] | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [darkMode, setDarkMode] = useState(true);
  const [currentSequence, setCurrentSequence] = useState<string>("");

  useEffect(() => {
    document.documentElement.setAttribute(
      "data-theme",
      darkMode ? "dark" : "light"
    );
  }, [darkMode]);

  const activeStructure = structures.find((s) => s.id === activeStructureId);
  const compareStructure = structures.find((s) => s.id === compareStructureId);

  const handleFold = async (sequence: string) => {
    setScore(null);
    setCurrentSequence(sequence);
    try {
      const data = await api.fold(sequence);
      setJobs((prev) => [
        ...prev,
        { id: data.job_id, type: "fold", status: "running", progress: 0 },
      ]);
      pollJob(data.job_id, sequence);
    } catch (e) {
      console.error("Fold failed:", e);
    }
  };

  const handleEvaluate = async (sequence: string) => {
    setCurrentSequence(sequence);
    try {
      const data = await api.evaluate(sequence);
      setScore(data);
    } catch (e) {
      console.error("Evaluate failed:", e);
    }
  };

  const handleMutate = async (mutation: string) => {
    if (!currentSequence) {
      alert("No active protein. Fold or paste a sequence first.");
      return;
    }
    try {
      const result = await api.mutate(currentSequence, mutation);
      setCurrentSequence(result.mutated);
      // Auto-refold the mutated sequence
      handleFold(result.mutated);
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleDesign = async () => {
    if (!activeStructure) {
      alert("Fold a protein first, then design alternative sequences for it.");
      return;
    }
    setDesignResults(null);
    setScore(null);
    try {
      const data = await api.design(activeStructure.pdbData, 10);
      setJobs((prev) => [
        ...prev,
        { id: data.job_id, type: "design", status: "running", progress: 0 },
      ]);
      pollDesignJob(data.job_id);
    } catch (e) {
      console.error("Design failed:", e);
    }
  };

  const pollDesignJob = (jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const data = await api.getJob(jobId);
        setJobs((prev) =>
          prev.map((j) =>
            j.id === jobId
              ? { ...j, status: data.status, progress: data.progress }
              : j
          )
        );
        if (data.status === "completed") {
          clearInterval(interval);
          if (data.result?.candidates) {
            setDesignResults(data.result.candidates);
          }
        } else if (data.status === "failed") {
          clearInterval(interval);
          alert(`Design failed: ${data.error}`);
        }
      } catch {
        clearInterval(interval);
      }
    }, 1000);
  };

  const handleUseCandidate = (sequence: string) => {
    setDesignResults(null);
    handleFold(sequence);
  };

  const handleChat = async (message: string): Promise<string> => {
    try {
      const intent = await api.chat(message);
      if (intent.action === "fold" && intent.sequence) {
        handleFold(intent.sequence);
      } else if (intent.action === "score" && intent.sequence) {
        handleEvaluate(intent.sequence);
      } else if (intent.action === "mutate" && intent.mutation) {
        handleMutate(intent.mutation);
      }
      return intent.response;
    } catch (e: any) {
      return `Error: ${e.message}`;
    }
  };

  const pollJob = (jobId: string, sequence: string) => {
    const interval = setInterval(async () => {
      try {
        const data = await api.getJob(jobId);
        setJobs((prev) =>
          prev.map((j) =>
            j.id === jobId
              ? { ...j, status: data.status, progress: data.progress }
              : j
          )
        );
        if (data.status === "completed") {
          clearInterval(interval);
          if (data.result?.pdb) {
            const id = `s${Date.now()}`;
            const newStruct: StoredStructure = {
              id,
              label: `${sequence.slice(0, 8)}... (${sequence.length}aa)`,
              sequence,
              pdbData: data.result.pdb,
              meanConfidence: data.result.mean_confidence,
            };
            setStructures((prev) => [...prev, newStruct]);
            setActiveStructureId(id);
            setScore(null);
          }
        } else if (data.status === "failed") {
          clearInterval(interval);
          console.error("Job failed:", data.error);
        }
      } catch {
        clearInterval(interval);
      }
    }, 1000);
  };

  const handleSavePdb = () => {
    if (!activeStructure) return;
    const blob = new Blob([activeStructure.pdbData], { type: "chemical/x-pdb" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${activeStructure.sequence.slice(0, 12)}.pdb`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <h1 className="logo">OpenDNA</h1>
          <span className="version">v0.1.0-alpha</span>
        </div>
        <div className="header-right">
          {activeStructure && (
            <button className="header-btn" onClick={handleSavePdb}>
              Save PDB
            </button>
          )}
          <button
            className="theme-toggle"
            onClick={() => setDarkMode(!darkMode)}
            title={darkMode ? "Switch to light mode" : "Switch to dark mode"}
          >
            {darkMode ? "\u2600" : "\u263E"}
          </button>
        </div>
      </header>

      <div className="app-body">
        <Sidebar
          onFold={handleFold}
          onEvaluate={handleEvaluate}
          onMutate={handleMutate}
          onDesign={handleDesign}
          hasActive={!!activeStructure}
          structures={structures}
          activeId={activeStructureId}
          compareId={compareStructureId}
          onSelectActive={(id) => {
            setActiveStructureId(id);
            setScore(null);
            setDesignResults(null);
          }}
          onSelectCompare={setCompareStructureId}
        />

        <main className="main-content">
          <div className="viewer-container">
            <ProteinViewer
              pdbData={activeStructure?.pdbData || ""}
              compareData={compareStructure?.pdbData}
              score={score}
              designResults={designResults}
              onUseCandidate={handleUseCandidate}
              onCloseDesign={() => setDesignResults(null)}
            />
          </div>

          <div className="bottom-panels">
            <ChatPanel onChat={handleChat} />
          </div>
        </main>
      </div>

      <JobMonitor jobs={jobs} />
    </div>
  );
}

export default App;
