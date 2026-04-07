import { useState, useEffect, useMemo, useCallback } from "react";
import Sidebar from "./components/Sidebar/Sidebar";
import ProteinViewer from "./components/ProteinViewer/ProteinViewer";
import ChatPanel from "./components/ChatPanel/ChatPanel";
import JobMonitor from "./components/JobMonitor/JobMonitor";
import CommandPalette, { type Command } from "./components/CommandPalette/CommandPalette";
import Toasts from "./components/Toasts/Toasts";
import AnalysisPanel from "./components/AnalysisPanel/AnalysisPanel";
import Dashboard from "./components/Dashboard/Dashboard";
import Academy from "./components/Academy/Academy";
import IterativePanel from "./components/IterativePanel/IterativePanel";
import { useToasts } from "./hooks/useToasts";
import { useKeyboard } from "./hooks/useKeyboard";
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

type Overlay = "none" | "analysis" | "dashboard" | "academy";

function App() {
  const [structures, setStructures] = useState<StoredStructure[]>([]);
  const [activeStructureId, setActiveStructureId] = useState<string | null>(null);
  const [compareStructureId, setCompareStructureId] = useState<string | null>(null);
  const [score, setScore] = useState<api.ScoreData | null>(null);
  const [analysis, setAnalysis] = useState<api.AnalysisResult | null>(null);
  const [explainText, setExplainText] = useState<string | null>(null);
  const [designResults, setDesignResults] = useState<DesignCandidate[] | null>(null);
  const [iterativeResult, setIterativeResult] = useState<any>(null);
  const [costInfo, setCostInfo] = useState<any>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [darkMode, setDarkMode] = useState(true);
  const [currentSequence, setCurrentSequence] = useState<string>("");
  const [overlay, setOverlay] = useState<Overlay>("none");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [xp, setXp] = useState(0);
  const { toasts, addToast, removeToast } = useToasts();

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  const activeStructure = structures.find((s) => s.id === activeStructureId);
  const compareStructure = structures.find((s) => s.id === compareStructureId);

  const clearOverlays = useCallback(() => {
    setAnalysis(null);
    setExplainText(null);
    setCostInfo(null);
    setOverlay("none");
  }, []);

  // === Actions ===

  const handleFold = async (sequence: string) => {
    setScore(null);
    clearOverlays();
    setCurrentSequence(sequence);
    try {
      const data = await api.fold(sequence);
      addToast({ kind: "info", message: `Folding ${sequence.length} residues...` });
      if (data.job_id) {
        setJobs((prev) => [...prev, { id: data.job_id, type: "fold", status: "running", progress: 0 }]);
        pollFoldJob(data.job_id, sequence);
      }
    } catch (e: any) {
      addToast({ kind: "error", message: e.message });
    }
  };

  const handleEvaluate = async (sequence: string) => {
    clearOverlays();
    setCurrentSequence(sequence);
    try {
      const data = await api.evaluate(sequence);
      setScore(data);
      addToast({ kind: "success", message: `Score: ${(data.overall * 100).toFixed(0)}/100` });
    } catch (e: any) {
      addToast({ kind: "error", message: e.message });
    }
  };

  const handleAnalyze = async () => {
    if (!currentSequence) {
      addToast({ kind: "warning", message: "Enter a sequence first" });
      return;
    }
    addToast({ kind: "info", message: "Running full analysis suite..." });
    try {
      const result = await api.analyze(currentSequence, activeStructure?.pdbData);
      setAnalysis(result);
      setOverlay("analysis");
      addToast({ kind: "success", message: "Analysis complete" });
    } catch (e: any) {
      addToast({ kind: "error", message: e.message });
    }
  };

  const handleExplain = async () => {
    if (!currentSequence) {
      addToast({ kind: "warning", message: "Enter a sequence first" });
      return;
    }
    addToast({ kind: "info", message: "AI is thinking..." });
    try {
      const r = await api.explain(currentSequence, activeStructure?.pdbData);
      setExplainText(r.explanation);
      addToast({ kind: "success", message: "Explanation ready" });
    } catch (e: any) {
      addToast({ kind: "error", message: e.message });
    }
  };

  const handleMutate = async (mutation: string) => {
    if (!currentSequence) {
      addToast({ kind: "warning", message: "No active protein" });
      return;
    }
    try {
      const result = await api.mutate(currentSequence, mutation);
      setCurrentSequence(result.mutated);
      addToast({ kind: "success", message: `Applied ${mutation}, refolding...` });
      handleFold(result.mutated);
    } catch (e: any) {
      addToast({ kind: "error", message: e.message });
    }
  };

  const handleDesign = async () => {
    if (!activeStructure) {
      addToast({ kind: "warning", message: "Fold a protein first" });
      return;
    }
    setDesignResults(null);
    setScore(null);
    clearOverlays();
    try {
      const data = await api.design(activeStructure.pdbData, 10);
      addToast({ kind: "info", message: "Designing 10 alternative sequences..." });
      setJobs((prev) => [...prev, { id: data.job_id, type: "design", status: "running", progress: 0 }]);
      pollDesignJob(data.job_id);
    } catch (e: any) {
      addToast({ kind: "error", message: e.message });
    }
  };

  const handleIterativeDesign = async (rounds: number, perRound: number) => {
    if (!currentSequence) {
      addToast({ kind: "warning", message: "Enter a sequence first" });
      return;
    }
    clearOverlays();
    setIterativeResult(null);
    try {
      const data = await api.iterativeDesign(currentSequence, rounds, perRound);
      addToast({
        kind: "info",
        message: `Iterative design: ${rounds} rounds × ${perRound} candidates. This will take a while.`,
      });
      setJobs((prev) => [...prev, { id: data.job_id, type: "iterative", status: "running", progress: 0 }]);
      pollIterativeJob(data.job_id);
    } catch (e: any) {
      addToast({ kind: "error", message: e.message });
    }
  };

  const handleMd = async () => {
    if (!activeStructure) return;
    try {
      const data = await api.md(activeStructure.pdbData);
      setJobs((prev) => [...prev, { id: data.job_id, type: "md", status: "running", progress: 0 }]);
      addToast({ kind: "info", message: "Running quick MD stability check..." });
      pollMdJob(data.job_id);
    } catch (e: any) {
      addToast({ kind: "error", message: e.message });
    }
  };

  const handleCost = async () => {
    if (!currentSequence) {
      addToast({ kind: "warning", message: "Enter a sequence first" });
      return;
    }
    try {
      const r = await api.cost(currentSequence);
      setCostInfo(r);
      addToast({ kind: "success", message: "Cost & carbon estimates ready" });
    } catch (e: any) {
      addToast({ kind: "error", message: e.message });
    }
  };

  const handleImport = async (kind: "uniprot" | "pdb", id: string) => {
    try {
      if (kind === "uniprot") {
        const r = await api.fetchUniprot(id);
        setCurrentSequence(r.sequence);
        addToast({
          kind: "success",
          title: r.name,
          message: `Loaded ${r.length} aa from ${r.organism}`,
        });
      } else {
        const r = await api.fetchPdb(id);
        const id2 = `s${Date.now()}`;
        const struct: StoredStructure = {
          id: id2,
          label: `${r.pdb_id} (imported)`,
          sequence: "",
          pdbData: r.pdb_string,
          meanConfidence: 1.0,
        };
        setStructures((p) => [...p, struct]);
        setActiveStructureId(id2);
        addToast({ kind: "success", message: `Loaded PDB ${r.pdb_id}` });
      }
    } catch (e: any) {
      addToast({ kind: "error", message: e.message });
    }
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
      } else if (intent.action === "explain") {
        handleExplain();
      }
      return intent.response;
    } catch (e: any) {
      return `Error: ${e.message}`;
    }
  };

  const handleSavePdb = () => {
    if (!activeStructure) return;
    const blob = new Blob([activeStructure.pdbData], { type: "chemical/x-pdb" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${activeStructure.sequence.slice(0, 12) || activeStructure.label}.pdb`;
    a.click();
    URL.revokeObjectURL(url);
    addToast({ kind: "success", message: "PDB saved" });
  };

  const handleSaveProject = async () => {
    const name = prompt("Project name:");
    if (!name) return;
    try {
      await api.saveProject(name, { structures, currentSequence, xp });
      addToast({ kind: "success", message: `Project '${name}' saved` });
    } catch (e: any) {
      addToast({ kind: "error", message: e.message });
    }
  };

  // === Pollers ===

  const pollFoldJob = (jobId: string, sequence: string) => {
    const interval = setInterval(async () => {
      try {
        const data = await api.getJob(jobId);
        setJobs((prev) =>
          prev.map((j) => (j.id === jobId ? { ...j, status: data.status, progress: data.progress } : j))
        );
        if (data.status === "completed") {
          clearInterval(interval);
          if (data.result?.pdb) {
            const id = `s${Date.now()}`;
            setStructures((prev) => [
              ...prev,
              {
                id,
                label: `${sequence.slice(0, 8)}... (${sequence.length}aa)`,
                sequence,
                pdbData: data.result.pdb,
                meanConfidence: data.result.mean_confidence,
              },
            ]);
            setActiveStructureId(id);
            setScore(null);
            addToast({
              kind: "success",
              title: "Fold complete",
              message: `pLDDT: ${(data.result.mean_confidence * 100).toFixed(0)}`,
            });
          }
        } else if (data.status === "failed") {
          clearInterval(interval);
          addToast({ kind: "error", message: data.error || "Fold failed" });
        }
      } catch {
        clearInterval(interval);
      }
    }, 1000);
  };

  const pollDesignJob = (jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const data = await api.getJob(jobId);
        setJobs((prev) =>
          prev.map((j) => (j.id === jobId ? { ...j, status: data.status, progress: data.progress } : j))
        );
        if (data.status === "completed") {
          clearInterval(interval);
          if (data.result?.candidates) {
            setDesignResults(data.result.candidates);
            addToast({ kind: "success", message: `Designed ${data.result.candidates.length} sequences` });
          }
        } else if (data.status === "failed") {
          clearInterval(interval);
          addToast({ kind: "error", message: data.error || "Design failed" });
        }
      } catch {
        clearInterval(interval);
      }
    }, 1000);
  };

  const pollIterativeJob = (jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const data = await api.getJob(jobId);
        setJobs((prev) =>
          prev.map((j) => (j.id === jobId ? { ...j, status: data.status, progress: data.progress } : j))
        );
        if (data.status === "completed") {
          clearInterval(interval);
          setIterativeResult(data.result);
          // Add the final structure to the list
          if (data.result?.rounds?.length) {
            const last = data.result.rounds[data.result.rounds.length - 1];
            const id = `s${Date.now()}`;
            setStructures((prev) => [
              ...prev,
              {
                id,
                label: `iter-final (${last.sequence.length}aa)`,
                sequence: last.sequence,
                pdbData: last.pdb,
                meanConfidence: last.confidence,
              },
            ]);
            setActiveStructureId(id);
          }
          addToast({
            kind: "success",
            title: "Iterative design complete",
            message: `Score improved by ${((data.result.improvement || 0) * 100).toFixed(1)} pts`,
          });
        } else if (data.status === "failed") {
          clearInterval(interval);
          addToast({ kind: "error", message: data.error || "Iterative design failed" });
        }
      } catch {
        clearInterval(interval);
      }
    }, 2000);
  };

  const pollMdJob = (jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const data = await api.getJob(jobId);
        setJobs((prev) =>
          prev.map((j) => (j.id === jobId ? { ...j, status: data.status, progress: data.progress } : j))
        );
        if (data.status === "completed") {
          clearInterval(interval);
          addToast({
            kind: "success",
            title: "MD complete",
            message: `Final RMSD: ${data.result?.final_rmsd?.toFixed(2)} Å. ${data.result?.stable ? "Stable!" : "Unstable"}`,
          });
        } else if (data.status === "failed") {
          clearInterval(interval);
          addToast({ kind: "error", message: data.error || "MD failed" });
        }
      } catch {
        clearInterval(interval);
      }
    }, 1500);
  };

  // === Command palette ===

  const commands: Command[] = useMemo(
    () => [
      { id: "fold", group: "Action", label: "Fold current sequence", shortcut: "F", action: () => currentSequence && handleFold(currentSequence) },
      { id: "score", group: "Action", label: "Score current sequence", shortcut: "S", action: () => currentSequence && handleEvaluate(currentSequence) },
      { id: "analyze", group: "Action", label: "Run full analysis", shortcut: "A", action: handleAnalyze },
      { id: "explain", group: "Action", label: "Explain this protein (AI)", action: handleExplain },
      { id: "design", group: "Action", label: "Design 10 sequences (ESM-IF1)", action: handleDesign },
      { id: "iter", group: "Action", label: "Run iterative design loop", action: () => handleIterativeDesign(3, 5) },
      { id: "md", group: "Action", label: "Quick MD stability check", action: handleMd },
      { id: "cost", group: "Action", label: "Estimate cost & carbon", action: handleCost },
      { id: "save-pdb", group: "File", label: "Save current PDB", action: handleSavePdb },
      { id: "save-proj", group: "File", label: "Save project workspace", action: handleSaveProject },
      { id: "import-ub", group: "Import", label: "Import ubiquitin", action: () => handleImport("uniprot", "ubiquitin") },
      { id: "import-ins", group: "Import", label: "Import insulin", action: () => handleImport("uniprot", "insulin") },
      { id: "import-gfp", group: "Import", label: "Import GFP", action: () => handleImport("uniprot", "gfp") },
      { id: "import-lyso", group: "Import", label: "Import lysozyme", action: () => handleImport("uniprot", "lysozyme") },
      { id: "import-p53", group: "Import", label: "Import p53", action: () => handleImport("uniprot", "p53") },
      { id: "import-kras", group: "Import", label: "Import KRAS", action: () => handleImport("uniprot", "kras") },
      { id: "open-dash", group: "View", label: "Open Dashboard", action: () => setOverlay("dashboard") },
      { id: "open-acad", group: "View", label: "Open Protein Academy", action: () => setOverlay("academy") },
      { id: "theme", group: "View", label: "Toggle dark/light mode", action: () => setDarkMode((d) => !d) },
    ],
    [currentSequence, activeStructure]
  );

  // === Keyboard ===

  useKeyboard({
    "cmd+k": () => setPaletteOpen(true),
    "cmd+f": () => currentSequence && handleFold(currentSequence),
    "cmd+s": () => handleSavePdb(),
    "cmd+shift+s": () => handleSaveProject(),
    "cmd+/": () => setPaletteOpen(true),
    f: () => currentSequence && handleFold(currentSequence),
    s: () => currentSequence && handleEvaluate(currentSequence),
    a: () => handleAnalyze(),
    escape: () => {
      setOverlay("none");
      setExplainText(null);
      setCostInfo(null);
      setIterativeResult(null);
      setDesignResults(null);
    },
  });

  // === Render ===

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <h1 className="logo">OpenDNA</h1>
          <span className="version">v0.2.0-beta</span>
          {xp > 0 && <span className="xp-badge">⭐ {xp} XP</span>}
        </div>
        <div className="header-right">
          <button className="header-btn small" onClick={() => setPaletteOpen(true)} title="Command palette (Ctrl+K)">
            ⌘K
          </button>
          <button className="header-btn small" onClick={() => setOverlay("dashboard")}>Dashboard</button>
          <button className="header-btn small" onClick={() => setOverlay("academy")}>Academy</button>
          {activeStructure && (
            <button className="header-btn" onClick={handleSavePdb}>Save PDB</button>
          )}
          <button className="theme-toggle" onClick={() => setDarkMode(!darkMode)}>
            {darkMode ? "☀" : "☾"}
          </button>
        </div>
      </header>

      <div className="app-body">
        <Sidebar
          onFold={handleFold}
          onEvaluate={handleEvaluate}
          onMutate={handleMutate}
          onDesign={handleDesign}
          onIterativeDesign={handleIterativeDesign}
          onAnalyze={handleAnalyze}
          onExplain={handleExplain}
          onMd={handleMd}
          onCost={handleCost}
          onImport={handleImport}
          hasActive={!!activeStructure}
          hasSequence={!!currentSequence}
          structures={structures}
          activeId={activeStructureId}
          compareId={compareStructureId}
          onSelectActive={(id) => {
            setActiveStructureId(id);
            setScore(null);
            clearOverlays();
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
              onUseCandidate={(seq) => {
                setDesignResults(null);
                handleFold(seq);
              }}
              onCloseDesign={() => setDesignResults(null)}
            />

            {overlay === "analysis" && analysis && (
              <AnalysisPanel analysis={analysis} onClose={() => setOverlay("none")} />
            )}
            {overlay === "dashboard" && (
              <Dashboard structures={structures.length} onClose={() => setOverlay("none")} />
            )}
            {overlay === "academy" && (
              <Academy
                onClose={() => setOverlay("none")}
                onAwardXp={(amt) => {
                  setXp((x) => x + amt);
                  addToast({ kind: "success", message: `+${amt} XP` });
                }}
              />
            )}

            {iterativeResult && (
              <IterativePanel
                result={iterativeResult}
                onUseRound={() => {
                  setIterativeResult(null);
                }}
                onClose={() => setIterativeResult(null)}
              />
            )}

            {explainText && (
              <div className="explain-overlay">
                <div className="explain-panel">
                  <div className="explain-header">
                    <h3>AI Explanation</h3>
                    <button onClick={() => setExplainText(null)}>×</button>
                  </div>
                  <div className="explain-body">{explainText}</div>
                </div>
              </div>
            )}

            {costInfo && (
              <div className="explain-overlay">
                <div className="explain-panel">
                  <div className="explain-header">
                    <h3>Cost & Carbon Estimate</h3>
                    <button onClick={() => setCostInfo(null)}>×</button>
                  </div>
                  <div className="cost-body">
                    <h4>Synthesis Cost (DNA gene order)</h4>
                    <div className="cost-row">Twist Bioscience: <strong>${costInfo.synthesis.twist_bioscience_usd}</strong></div>
                    <div className="cost-row">IDT: <strong>${costInfo.synthesis.idt_usd}</strong></div>
                    <div className="cost-row">GenScript: <strong>${costInfo.synthesis.genscript_usd}</strong></div>
                    <div className="cost-cheapest">
                      Cheapest: <strong>{costInfo.synthesis.cheapest_vendor}</strong> at <strong>${costInfo.synthesis.cheapest_price}</strong>
                    </div>
                    <h4>Compute Carbon Footprint</h4>
                    <div className="cost-row">CPU: <strong>{costInfo.compute_carbon_cpu.equivalent}</strong></div>
                    <div className="cost-row">GPU: <strong>{costInfo.compute_carbon_gpu.equivalent}</strong></div>
                    <p className="ap-note">{costInfo.synthesis.notes}</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="bottom-panels">
            <ChatPanel onChat={handleChat} />
          </div>
        </main>
      </div>

      <JobMonitor jobs={jobs} />
      <Toasts toasts={toasts} onRemove={removeToast} />
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} commands={commands} />
    </div>
  );
}

export default App;
