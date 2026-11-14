import { useState, useEffect, useMemo, useCallback } from "react";
import Sidebar from "./components/Sidebar/Sidebar";
import ProteinViewer from "./components/ProteinViewer/ProteinViewer";
import ChatPanel from "./components/ChatPanel/ChatPanel";
import JobMonitor from "./components/JobMonitor/JobMonitor";
import CommandPalette, { type Command } from "./components/CommandPalette/CommandPalette";
import Toasts from "./components/Toasts/Toasts";
import AnalysisPanel from "./components/AnalysisPanel/AnalysisPanel";
import Dashboard from "./components/Dashboard/Dashboard";
import HardwarePanel from "./components/HardwarePanel/HardwarePanel";
import ProteinOfDayBanner from "./components/ProteinOfDayBanner/ProteinOfDayBanner";
import Academy from "./components/Academy/Academy";
import IterativePanel from "./components/IterativePanel/IterativePanel";
import AgentPanel from "./components/AgentPanel/AgentPanel";
import BackendStatus from "./components/BackendStatus/BackendStatus";
import ComponentManager from "./components/ComponentManager/ComponentManager";
import WorkflowEditor from "./components/WorkflowEditor/WorkflowEditor";
import CollabPanel from "./components/CollabPanel/CollabPanel";
import Ramachandran from "./components/Ramachandran/Ramachandran";
import OnboardingTour from "./components/Onboarding/OnboardingTour";
import ProteinSearch from "./components/ProteinSearch/ProteinSearch";
import AcademyGamesPanel from "./components/Academy/AcademyGamesPanel";
import ProjectExplorer from "./components/ProjectExplorer/ProjectExplorer";
import PaperExtractor from "./components/PaperExtractor/PaperExtractor";
import MutationScanner from "./components/MutationScanner/MutationScanner";
import TrajectoryPlayer from "./components/TrajectoryPlayer/TrajectoryPlayer";
import ErrorBoundary from "./components/ErrorBoundary/ErrorBoundary";
import VRMode from "./components/VRMode/VRMode";
import AntibodyTools from "./components/AntibodyTools/AntibodyTools";
import PlasmidMap from "./components/PlasmidMap/PlasmidMap";
import Competitions from "./components/Competitions/Competitions";
import Hub from "./components/Hub/Hub";
import VoiceControl from "./components/VoiceControl/VoiceControl";
import PaperWriter from "./components/PaperWriter/PaperWriter";
import FeelingLucky from "./components/FeelingLucky/FeelingLucky";
import ProjectTemplates from "./components/ProjectTemplates/ProjectTemplates";
import { useToasts } from "./hooks/useToasts";
import { useKeyboard } from "./hooks/useKeyboard";
import { useRecentlyUpdated } from "./hooks/useRecentlyUpdated";
import { isNightAt, getUserLocation } from "./utils/sunset";
import * as api from "./api/client";
import {
  playDing,
  playSuccess,
  playFail,
  playClick,
  playWhoosh,
  getSfxEnabled,
  setSfxEnabled,
  SFX_MUTE_HOTKEY,
} from "./utils/sfx";
import "./App.css";

type ThemeMode = "light" | "dark" | "auto";
const THEME_KEY = "opendna.themeMode";
function loadThemeMode(): ThemeMode {
  const v = localStorage.getItem(THEME_KEY);
  return v === "light" || v === "dark" || v === "auto" ? v : "dark";
}

interface Job {
  id: string;
  type: string;
  status: string;
  progress: number;
}

export type StructureSource = "esmfold" | "alphafold" | "pdb" | "designed" | "imported";

export interface StoredStructure {
  id: string;
  label: string;
  sequence: string;
  pdbData: string;
  meanConfidence: number;
  source: StructureSource;
}

interface DesignCandidate {
  rank: number;
  sequence: string;
  score: number;
  recovery: number;
}

type Overlay = "none" | "analysis" | "dashboard" | "academy" | "agent" | "components" | "workflow" | "collab" | "search" | "ramachandran" | "games" | "trajectory" | "scanner" | "paper" | "vr" | "competitions" | "hub" | "voice" | "paper_writer" | "feeling_lucky" | "project_templates" | "antibody" | "plasmid" | "hardware";

const AUTOSAVE_KEY = "opendna.autosave";
const AUTOSAVE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;

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
  const [themeMode, setThemeMode] = useState<ThemeMode>(() => loadThemeMode());
  const [autoIsDark, setAutoIsDark] = useState<boolean>(true);
  const [xrAvailable, setXrAvailable] = useState<boolean>(
    typeof navigator !== "undefined" && !!(navigator as any).xr
  );
  const darkMode = themeMode === "auto" ? autoIsDark : themeMode === "dark";
  const [currentSequence, setCurrentSequence] = useState<string>("");
  const [overlay, setOverlay] = useState<Overlay>("none");
  const [trajectoryFrames, setTrajectoryFrames] = useState<string[]>([]);
  const [currentFrame, setCurrentFrame] = useState<number>(0);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [showExplorer, setShowExplorer] = useState(false);
  const [xp, setXp] = useState(0);
  const [sfxEnabled, setSfxEnabledState] = useState<boolean>(() => getSfxEnabled());
  const scoreGlow = useRecentlyUpdated(score ? `${score.overall}` : null);
  const [showOnboarding, setShowOnboarding] = useState(() => {
    return localStorage.getItem("opendna.onboarded") !== "true";
  });
  const finishOnboarding = useCallback(() => {
    localStorage.setItem("opendna.onboarded", "true");
    setShowOnboarding(false);
  }, []);
  // Global drag-and-drop for FASTA/PDB files
  useEffect(() => {
    const onDrop = async (e: DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer?.files?.[0];
      if (!file) return;
      const text = await file.text();
      if (file.name.toLowerCase().endsWith(".fasta") || file.name.toLowerCase().endsWith(".fa") || text.startsWith(">")) {
        const seq = text.split("\n").filter(l => !l.startsWith(">")).join("").replace(/\s/g, "");
        setCurrentSequence(seq);
      } else if (file.name.toLowerCase().endsWith(".pdb") || text.startsWith("ATOM") || text.includes("\nATOM")) {
        // Treat as imported structure
        console.log("PDB drop:", file.name, text.length, "chars");
      }
    };
    const onDragOver = (e: DragEvent) => e.preventDefault();
    window.addEventListener("drop", onDrop);
    window.addEventListener("dragover", onDragOver);
    return () => {
      window.removeEventListener("drop", onDrop);
      window.removeEventListener("dragover", onDragOver);
    };
  }, []);
  const [switchToToolsTrigger, setSwitchToToolsTrigger] = useState(0);
  const { toasts, addToast: _rawAddToast, removeToast } = useToasts();
  const addToast = useCallback(
    (t: any) => {
      if (t?.kind === "success") playSuccess();
      else if (t?.kind === "error") playFail();
      _rawAddToast(t);
    },
    [_rawAddToast]
  );
  const [restorePrompt, setRestorePrompt] = useState<any>(null);

  // SFX: ding on score update, whoosh on overlay open, mute hotkey
  useEffect(() => {
    if (score) playDing();
  }, [score]);
  useEffect(() => {
    if (overlay !== "none") playWhoosh();
  }, [overlay]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === SFX_MUTE_HOTKEY && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const tag = (e.target as HTMLElement)?.tagName;
        if (tag === "INPUT" || tag === "TEXTAREA") return;
        const nv = !getSfxEnabled();
        setSfxEnabled(nv);
        setSfxEnabledState(nv);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const toggleSfx = useCallback(() => {
    const nv = !getSfxEnabled();
    setSfxEnabled(nv);
    setSfxEnabledState(nv);
  }, []);

  // === Auto-save state every 30s ===
  useEffect(() => {
    const snapshot = () => {
      try {
        const payload = {
          ts: Date.now(),
          currentSequence,
          structures,
          score,
          analysis,
          overlay,
          xp,
        };
        localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(payload));
      } catch { /* quota or serialization error: ignore */ }
    };
    const interval = setInterval(snapshot, 30000);
    return () => clearInterval(interval);
  }, [currentSequence, structures, score, analysis, overlay, xp]);

  // === Manual save ===
  const handleManualSave = useCallback(() => {
    try {
      const payload = {
        ts: Date.now(),
        currentSequence,
        structures,
        score,
        analysis,
        overlay,
        xp,
      };
      localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(payload));
      addToast({ kind: "success", message: "Session saved" });
    } catch (e: any) {
      addToast({ kind: "error", message: `Save failed: ${e.message}` });
    }
  }, [currentSequence, structures, score, analysis, overlay, xp, addToast]);

  // === On mount: check for recent autosave ===
  useEffect(() => {
    try {
      const raw = localStorage.getItem(AUTOSAVE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (parsed && parsed.ts && Date.now() - parsed.ts < AUTOSAVE_MAX_AGE_MS) {
        setRestorePrompt(parsed);
      }
    } catch { /* ignore */ }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const restoreAutosave = useCallback(() => {
    if (!restorePrompt) return;
    if (restorePrompt.currentSequence) setCurrentSequence(restorePrompt.currentSequence);
    if (Array.isArray(restorePrompt.structures)) setStructures(restorePrompt.structures);
    if (restorePrompt.score) setScore(restorePrompt.score);
    if (restorePrompt.analysis) setAnalysis(restorePrompt.analysis);
    if (typeof restorePrompt.xp === "number") setXp(restorePrompt.xp);
    setRestorePrompt(null);
    addToast({ kind: "success", message: "Previous session restored" });
  }, [restorePrompt, addToast]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  useEffect(() => {
    localStorage.setItem(THEME_KEY, themeMode);
  }, [themeMode]);

  // Auto-theme: fetch location once, then re-evaluate every 5 minutes.
  useEffect(() => {
    if (themeMode !== "auto") return;
    let cancelled = false;
    let timer: ReturnType<typeof setInterval> | null = null;
    (async () => {
      const loc = await getUserLocation();
      if (cancelled) return;
      const evaluate = () => setAutoIsDark(isNightAt(loc.lat, loc.lon));
      evaluate();
      timer = setInterval(evaluate, 5 * 60 * 1000);
    })();
    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
  }, [themeMode]);

  // Detect WebXR once (and listen for late availability).
  useEffect(() => {
    const nav: any = navigator;
    if (!nav.xr) {
      setXrAvailable(false);
      return;
    }
    if (typeof nav.xr.isSessionSupported === "function") {
      nav.xr
        .isSessionSupported("immersive-vr")
        .then((ok: boolean) => setXrAvailable(ok))
        .catch(() => setXrAvailable(false));
    } else {
      setXrAvailable(true);
    }
  }, []);

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
    if (sequence.length > 250) {
      const ok = window.confirm(
        `This protein is ${sequence.length} residues long. ` +
        `On CPU, ESMFold will take ~${Math.round(sequence.length / 30)} minutes and may use 8+ GB RAM.\n\n` +
        `On GPU it would take seconds. Continue?`
      );
      if (!ok) return;
    }
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
        setSwitchToToolsTrigger((n) => n + 1);

        // If AlphaFold DB has a structure for this entry, load it directly
        if (r.pdb_string && r.structure_source === "alphafold") {
          const id2 = `s${Date.now()}`;
          const struct: StoredStructure = {
            id: id2,
            label: `${r.name} (AlphaFold)`,
            sequence: r.sequence,
            pdbData: r.pdb_string,
            meanConfidence: _meanPlddtFromPdb(r.pdb_string),
            source: "alphafold",
          };
          setStructures((p) => [...p, struct]);
          setActiveStructureId(id2);
          addToast({
            kind: "success",
            title: r.name,
            message: `Loaded ${r.length} aa from ${r.organism} + AlphaFold DB structure (high quality, no folding needed)`,
          });
        } else {
          addToast({
            kind: "success",
            title: r.name,
            message: `Loaded ${r.length} aa from ${r.organism}. No AlphaFold structure available - click Predict Structure to fold.`,
          });
        }
      } else {
        const r = await api.fetchPdb(id);
        const id2 = `s${Date.now()}`;
        const struct: StoredStructure = {
          id: id2,
          label: `${r.pdb_id} (RCSB)`,
          sequence: "",
          pdbData: r.pdb_string,
          meanConfidence: 1.0,
          source: "pdb",
        };
        setStructures((p) => [...p, struct]);
        setActiveStructureId(id2);
        addToast({ kind: "success", message: `Loaded PDB ${r.pdb_id} (experimental structure)` });
      }
    } catch (e: any) {
      addToast({ kind: "error", message: e.message });
    }
  };

  // Compute mean pLDDT from B-factor column of a PDB string (AlphaFold convention).
  function _meanPlddtFromPdb(pdb: string): number {
    const lines = pdb.split("\n");
    const values: number[] = [];
    for (const line of lines) {
      if ((line.startsWith("ATOM") || line.startsWith("HETATM")) && line.length >= 66) {
        if (line.substring(12, 16).trim() === "CA") {
          const v = parseFloat(line.substring(60, 66).trim());
          if (!isNaN(v)) values.push(v);
        }
      }
    }
    if (values.length === 0) return 1.0;
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    // AlphaFold pLDDT is 0-100, normalize to 0-1
    return mean > 1 ? mean / 100 : mean;
  }

  const handleChat = async (message: string): Promise<string> => {
    try {
      // Try smart chat first (uses LLM with tool calling)
      const r = await api.smartChat(message);
      let reply = r.text || "";
      // If there were tool calls, summarize them
      if (r.tool_results && r.tool_results.length > 0) {
        for (const tr of r.tool_results) {
          if (tr.tool === "fold_protein" && tr.result?.mean_confidence) {
            reply += `\n[Folded with pLDDT ${(tr.result.mean_confidence * 100).toFixed(0)}]`;
          } else if (tr.tool === "score_protein" && tr.result?.overall) {
            reply += `\n[Scored: ${(tr.result.overall * 100).toFixed(0)}/100]`;
          }
        }
      }
      // Fallback: also handle the simple intent parser actions
      if (!reply || reply.trim().length === 0) {
        const intent = await api.chat(message);
        if (intent.action === "fold" && intent.sequence) handleFold(intent.sequence);
        else if (intent.action === "score" && intent.sequence) handleEvaluate(intent.sequence);
        else if (intent.action === "mutate" && intent.mutation) handleMutate(intent.mutation);
        return intent.response;
      }
      return reply + (r.provider !== "heuristic" ? ` (${r.provider})` : "");
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
                source: "esmfold",
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
                source: "designed",
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
      { id: "open-agent", group: "View", label: "Open AI Agent", action: () => setOverlay("agent") },
      { id: "theme", group: "View", label: "Toggle dark/light mode", action: () => setThemeMode((m) => (m === "light" ? "dark" : m === "dark" ? "auto" : "light")) },
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
    g: () => {
      // Zoom-to-residue keyboard shortcut.
      // TODO: wire this to Molstar focusResidue() once the viewer exposes it.
      const ans = window.prompt("Go to residue #");
      if (ans) {
        const n = parseInt(ans, 10);
        if (!isNaN(n)) {
          // eslint-disable-next-line no-console
          console.log(`[zoom-to-residue] residue ${n} (Molstar focus integration TODO)`);
        }
      }
    },
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
      {restorePrompt && (
        <div className="restore-banner">
          <span>
            Restore previous session? (saved {new Date(restorePrompt.ts).toLocaleString()})
          </span>
          <div className="restore-actions">
            <button className="restore-btn primary" onClick={restoreAutosave}>Restore</button>
            <button className="restore-btn" onClick={() => setRestorePrompt(null)}>Dismiss</button>
          </div>
        </div>
      )}
      <header className="app-header">
        <div className="header-left">
          <h1 className="logo">OpenDNA</h1>
          <span className="version">v0.2.0-beta</span>
          {xp > 0 && <span className="xp-badge">⭐ {xp} XP</span>}
          {score && (
            <span className={`score-badge ${scoreGlow}`}>
              Score: {(score.overall * 100).toFixed(0)}
            </span>
          )}
        </div>
        <div
          className="header-right"
          onClick={(e) => {
            const tgt = e.target as HTMLElement;
            if (tgt && tgt.closest && tgt.closest(".header-btn")) {
              playClick();
              const btn = tgt.closest(".header-btn") as HTMLElement;
              btn.classList.remove("ma-bounce");
              // Force reflow to restart the animation
              void btn.offsetWidth;
              btn.classList.add("ma-bounce");
            }
          }}
        >
          <button className="header-btn small" onClick={() => setOverlay("search")} title="Search UniProt">🔍 Search</button>
          <button className="header-btn small" onClick={() => setPaletteOpen(true)} title="Command palette (Ctrl+K)">
            ⌘K
          </button>
          <button className="header-btn small" onClick={() => setOverlay("agent")} title="AI Agent">
            🤖 Agent
          </button>
          <button className="header-btn small" onClick={() => setOverlay("dashboard")}>Dashboard</button>
          <button className="header-btn small" onClick={() => setOverlay("hardware")} title="Hardware acceleration details">⚡ Hardware</button>
          <button className="header-btn small" onClick={() => setOverlay("academy")}>Academy</button>
          <button className="header-btn small" onClick={() => setOverlay("components")} title="Component Manager">📦 Components</button>
          <button className="header-btn small" onClick={() => setOverlay("feeling_lucky")} title="I'm Feeling Lucky — one-click full pipeline">🍀 Lucky</button>
          <button className="header-btn small" onClick={() => setOverlay("project_templates")} title="Start from a project template">📋 Templates</button>
          <button className="header-btn small" onClick={() => setOverlay("workflow")} title="Visual Workflow Editor">🧩 Workflow</button>
          <button className="header-btn small" onClick={() => setOverlay("collab")} title="Real-time co-editing">🤝 Collab</button>
          <button className="header-btn small" onClick={() => setOverlay("games")} title="Academy Mini-games">🎮 Mini-games</button>
          <button className="header-btn small" onClick={() => setOverlay("paper")} title="Extract proteins from a paper">📄 Paper</button>
          <button className="header-btn small" onClick={() => setOverlay("antibody")} title="Antibody numbering / humanization">🧪 Antibody</button>
          <button className="header-btn small" onClick={() => setOverlay("plasmid")} title="Plasmid map generator">🧬 Plasmid</button>
          <button className="header-btn small" onClick={() => setOverlay("trajectory")} title="Trajectory player">🎞️ Trajectory</button>
          <button className="header-btn small" onClick={() => setShowExplorer(v => !v)} title="Project Explorer">🗂️ Explorer</button>
          <button
            className="header-btn small"
            onClick={() => setOverlay("ramachandran")}
            title="Interactive Ramachandran plot"
            disabled={!activeStructure}
          >
            📐 Ramachandran
          </button>
          <button
            className="header-btn small"
            onClick={() => setOverlay("scanner")}
            title="Saturation mutagenesis heatmap"
            disabled={!currentSequence}
          >
            🎯 Scanner
          </button>
          <button className="header-btn small" onClick={handleManualSave} title="Save session to local storage">
            💾 Save
          </button>
          {activeStructure && (
            <button className="header-btn" onClick={handleSavePdb}>Save PDB</button>
          )}
          <button className="header-btn small" onClick={() => setOverlay("competitions")} title="In-app competitions">🏆 Compete</button>
          <button className="header-btn small" onClick={() => setOverlay("hub")} title="OpenDNA Hub">🌐 Hub</button>
          <button className="header-btn small" onClick={() => setOverlay("voice")} title="Voice control">🎤 Voice</button>
          <button className="header-btn small" onClick={() => setOverlay("paper_writer")} title="Auto paper writer">📝 Paper writer</button>
          <button
            className="header-btn small"
            onClick={toggleSfx}
            title={`Sound effects ${sfxEnabled ? "on" : "off"} (press '${SFX_MUTE_HOTKEY}' to toggle)`}
          >
            {sfxEnabled ? "🔊" : "🔇"}
          </button>
          <button
            className="header-btn small"
            onClick={() => xrAvailable && setOverlay("vr")}
            disabled={!xrAvailable}
            title={xrAvailable ? "Enter VR mode" : "WebXR not detected — needs a WebXR-capable browser + headset"}
            style={!xrAvailable ? { opacity: 0.5, cursor: "not-allowed" } : undefined}
          >
            🥽 VR
          </button>
          <button
            className="theme-toggle"
            onClick={() =>
              setThemeMode((m) => (m === "light" ? "dark" : m === "dark" ? "auto" : "light"))
            }
            title={`Theme: ${themeMode}`}
          >
            {themeMode === "light" ? "☀" : themeMode === "dark" ? "☾" : "🌆"}
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
          onSequenceChange={setCurrentSequence}
          currentSequence={currentSequence}
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
          switchToToolsTab={switchToToolsTrigger}
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
              trajectoryFrames={trajectoryFrames.length > 0 ? trajectoryFrames : undefined}
              currentFrame={trajectoryFrames.length > 0 ? currentFrame : undefined}
              onMutate={(_chain, position, newAA, oldAA) => {
                const mutation = `${oldAA}${position}${newAA}`;
                addToast({ kind: "info", message: `Mutating ${mutation}...` });
                handleMutate(mutation);
              }}
            />

            {!activeStructure && (
              <ProteinOfDayBanner
                onLoadSequence={(seq, label) => {
                  setCurrentSequence(seq);
                  addToast({ kind: "success", message: `Loaded ${label} (${seq.length} aa)` });
                }}
              />
            )}

            {overlay === "analysis" && analysis && (
              <ErrorBoundary>
                <AnalysisPanel analysis={analysis} onClose={() => setOverlay("none")} />
              </ErrorBoundary>
            )}
            {overlay === "dashboard" && (
              <ErrorBoundary>
                <Dashboard
                  structures={structures.length}
                  onClose={() => setOverlay("none")}
                  onLoadSequence={(seq, label) => {
                    setCurrentSequence(seq);
                    setOverlay("none");
                    addToast({ kind: "success", message: `Loaded ${label} (${seq.length} aa)` });
                  }}
                />
              </ErrorBoundary>
            )}
            {overlay === "hardware" && (
              <ErrorBoundary>
                <div className="modal-backdrop" onClick={() => setOverlay("none")}>
                  <div onClick={(e) => e.stopPropagation()}>
                    <HardwarePanel onClose={() => setOverlay("none")} />
                  </div>
                </div>
              </ErrorBoundary>
            )}
            {overlay === "academy" && (
              <ErrorBoundary>
                <Academy
                  onClose={() => setOverlay("none")}
                  onAwardXp={(amt) => {
                    setXp((x) => x + amt);
                    addToast({ kind: "success", message: `+${amt} XP` });
                  }}
                />
              </ErrorBoundary>
            )}
            {overlay === "agent" && (
              <ErrorBoundary>
                <AgentPanel
                  onClose={() => setOverlay("none")}
                  onSequenceFound={(seq) => setCurrentSequence(seq)}
                />
              </ErrorBoundary>
            )}
            {overlay === "components" && (
              <ErrorBoundary>
                <div className="modal-backdrop">
                  <div>
                    <ComponentManager onClose={() => setOverlay("none")} />
                  </div>
                </div>
              </ErrorBoundary>
            )}
            {overlay === "workflow" && (
              <ErrorBoundary>
                <div className="modal-backdrop">
                  <div>
                    <WorkflowEditor onClose={() => setOverlay("none")} />
                  </div>
                </div>
              </ErrorBoundary>
            )}
            {overlay === "feeling_lucky" && (
              <ErrorBoundary>
                <FeelingLucky
                  initialSequence={currentSequence}
                  onClose={() => setOverlay("none")}
                />
              </ErrorBoundary>
            )}
            {overlay === "project_templates" && (
              <ErrorBoundary>
                <ProjectTemplates
                  onClose={() => setOverlay("none")}
                  onInstantiated={({ starterSequence }) => {
                    if (starterSequence) {
                      setCurrentSequence(starterSequence);
                      addToast({ kind: "success", message: "Template loaded into editor" });
                    } else {
                      addToast({ kind: "info", message: "Template instantiated (no starter sequence)" });
                    }
                  }}
                />
              </ErrorBoundary>
            )}
            {overlay === "collab" && (
              <ErrorBoundary>
                <div className="modal-backdrop">
                  <div>
                    <CollabPanel roomName="opendna-default" userName="me" onClose={() => setOverlay("none")} />
                  </div>
                </div>
              </ErrorBoundary>
            )}
            {overlay === "ramachandran" && activeStructure && (
              <div className="modal-backdrop" onClick={() => setOverlay("none")}>
                <div onClick={e => e.stopPropagation()}>
                  <Ramachandran
                    pdb_string={activeStructure.pdbData}
                    onResidueClick={(n) => {
                      // eslint-disable-next-line no-console
                      console.log(`[ramachandran] clicked residue ${n}`);
                    }}
                    onClose={() => setOverlay("none")}
                  />
                </div>
              </div>
            )}
            {overlay === "scanner" && currentSequence && (
              <ErrorBoundary>
                <div className="modal-backdrop" onClick={() => setOverlay("none")}>
                  <div onClick={e => e.stopPropagation()}>
                    <MutationScanner
                      sequence={currentSequence}
                      onClose={() => setOverlay("none")}
                      onCellClick={(position, newAA) => {
                        const oldAA = currentSequence[position - 1];
                        if (!oldAA || oldAA === newAA) return;
                        const mutation = `${oldAA}${position}${newAA}`;
                        addToast({ kind: "info", message: `Mutating ${mutation}...` });
                        handleMutate(mutation);
                        setOverlay("none");
                      }}
                    />
                  </div>
                </div>
              </ErrorBoundary>
            )}
            {overlay === "search" && (
              <ErrorBoundary>
                <div className="modal-backdrop">
                  <div>
                    <ProteinSearch
                      onClose={() => setOverlay("none")}
                      onPick={(hit) => {
                        setCurrentSequence(hit.sequence);
                        setOverlay("none");
                        addToast({ kind: "success", message: `Loaded ${hit.gene || hit.accession} (${hit.length} aa)` });
                      }}
                    />
                  </div>
                </div>
              </ErrorBoundary>
            )}
            {overlay === "trajectory" && (
              <ErrorBoundary>
                <div className="modal-backdrop" onClick={() => setOverlay("none")}>
                  <div
                    onClick={(e) => e.stopPropagation()}
                    style={{
                      background: "var(--panel-bg, #1a1a1a)",
                      padding: 16,
                      borderRadius: 8,
                      minWidth: 520,
                      maxWidth: "90vw",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                      <h3 style={{ margin: 0 }}>Trajectory Player</h3>
                      <button className="header-btn small" onClick={() => setOverlay("none")}>Close</button>
                    </div>
                    <TrajectoryPlayer
                      frames={trajectoryFrames}
                      onFrameChange={setCurrentFrame}
                      onFramesLoaded={(fr) => {
                        setTrajectoryFrames(fr);
                        setCurrentFrame(0);
                      }}
                      sourcePdb={activeStructure?.pdbData || ""}
                    />
                    {trajectoryFrames.length > 0 && (
                      <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                        <button
                          className="header-btn small"
                          onClick={() => { setTrajectoryFrames([]); setCurrentFrame(0); }}
                        >
                          Clear trajectory
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </ErrorBoundary>
            )}
            {overlay === "games" && (
              <ErrorBoundary>
                <AcademyGamesPanel
                  onClose={() => setOverlay("none")}
                  onAwardXp={(amt) => {
                    setXp((x) => x + amt);
                    addToast({ kind: "success", message: `+${amt} XP` });
                  }}
                  onPickSequence={(seq, label) => {
                    setCurrentSequence(seq);
                    addToast({ kind: "success", message: `Loaded ${label || "sequence"} (${seq.length} aa)` });
                  }}
                />
              </ErrorBoundary>
            )}
            {overlay === "vr" && (
              <ErrorBoundary>
                <VRMode
                  pdbString={activeStructure?.pdbData ?? null}
                  onClose={() => setOverlay("none")}
                />
              </ErrorBoundary>
            )}
            {overlay === "paper" && (
              <ErrorBoundary>
                <PaperExtractor
                  onClose={() => setOverlay("none")}
                  onPickSequence={(seq, label) => {
                    setCurrentSequence(seq);
                    setOverlay("none");
                    addToast({ kind: "success", message: `Loaded ${label || "sequence"} (${seq.length} aa)` });
                  }}
                />
              </ErrorBoundary>
            )}
            {overlay === "antibody" && (
              <ErrorBoundary>
                <AntibodyTools
                  initialSequence={currentSequence}
                  onClose={() => setOverlay("none")}
                />
              </ErrorBoundary>
            )}
            {overlay === "plasmid" && (
              <ErrorBoundary>
                <PlasmidMap
                  initialSequence={currentSequence}
                  onClose={() => setOverlay("none")}
                />
              </ErrorBoundary>
            )}
            {overlay === "competitions" && (
              <ErrorBoundary>
                <Competitions
                  onClose={() => setOverlay("none")}
                  defaultSequence={currentSequence}
                />
              </ErrorBoundary>
            )}
            {overlay === "hub" && (
              <ErrorBoundary>
                <Hub
                  onClose={() => setOverlay("none")}
                  currentPdb={activeStructure?.pdbData || ""}
                  currentSequence={currentSequence}
                />
              </ErrorBoundary>
            )}
            {overlay === "voice" && (
              <ErrorBoundary>
                <VoiceControl onClose={() => setOverlay("none")} />
              </ErrorBoundary>
            )}
            {overlay === "paper_writer" && (
              <ErrorBoundary>
                <PaperWriter onClose={() => setOverlay("none")} defaultProjectId="default" />
              </ErrorBoundary>
            )}
            {showExplorer && (
              <ErrorBoundary>
                <ProjectExplorer projectId="default" onClose={() => setShowExplorer(false)} />
              </ErrorBoundary>
            )}
            {showOnboarding && (
              <ErrorBoundary>
                <OnboardingTour onFinish={finishOnboarding} />
              </ErrorBoundary>
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
      <BackendStatus />
    </div>
  );
}

export default App;
