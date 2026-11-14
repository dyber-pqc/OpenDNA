import { useEffect, useRef, useState, useCallback } from "react";
import "./PresentationMode.css";

export type PresentationAction =
  | { action: "rotate"; duration: number; axis?: "x" | "y" | "z"; degrees?: number }
  | { action: "zoom"; duration: number; scale?: number }
  | { action: "highlight"; residues: number[]; duration: number }
  | { action: "pause"; duration: number };

interface BuiltInScript {
  id: string;
  name: string;
  script: PresentationAction[];
}

const BUILT_IN_SCRIPTS: BuiltInScript[] = [
  {
    id: "overview",
    name: "Overview",
    script: [
      { action: "rotate", duration: 4000, axis: "y", degrees: 360 },
      { action: "zoom", duration: 2000, scale: 1.5 },
      { action: "rotate", duration: 4000, axis: "y", degrees: 360 },
      { action: "pause", duration: 800 },
    ],
  },
  {
    id: "active_site",
    name: "Active site",
    script: [
      { action: "zoom", duration: 1500, scale: 2.5 },
      { action: "highlight", residues: [45, 67, 89], duration: 2500 },
      { action: "rotate", duration: 3000, axis: "y", degrees: 180 },
      { action: "pause", duration: 800 },
    ],
  },
  {
    id: "fold_trajectory",
    name: "Fold trajectory",
    script: [
      { action: "rotate", duration: 5000, axis: "y", degrees: 360 },
      { action: "zoom", duration: 2000, scale: 1.3 },
      { action: "rotate", duration: 5000, axis: "x", degrees: 360 },
    ],
  },
];

interface PresentationModeProps {
  pdb_string: string;
  trajectoryFrames?: string[];
  script?: PresentationAction[];
  onClose: () => void;
}

export default function PresentationMode({
  pdb_string,
  trajectoryFrames,
  script: customScript,
  onClose,
}: PresentationModeProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const pluginRef = useRef<any>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [scriptId, setScriptId] = useState<string>(customScript ? "custom" : "overview");
  const [sceneIdx, setSceneIdx] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);
  const [highlightInfo, setHighlightInfo] = useState<{ residues: number[] } | null>(null);
  const [recording, setRecording] = useState<"none" | "video" | "gif">("none");
  const [statusMsg, setStatusMsg] = useState<string>("");
  const sceneTimerRef = useRef<number | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const trajIdxRef = useRef(0);

  const activeScript: PresentationAction[] =
    customScript ?? BUILT_IN_SCRIPTS.find((s) => s.id === scriptId)?.script ?? BUILT_IN_SCRIPTS[0].script;

  // Initialise Mol* viewer
  useEffect(() => {
    if (!pdb_string || !containerRef.current) return;
    let cancelled = false;
    (async () => {
      try {
        const { createPluginUI } = await import("molstar/lib/mol-plugin-ui/index");
        const { renderReact18 } = await import("molstar/lib/mol-plugin-ui/react18");
        const { DefaultPluginUISpec } = await import("molstar/lib/mol-plugin-ui/spec");
        const { PluginConfig } = await import("molstar/lib/mol-plugin/config");
        const { ColorNames } = await import("molstar/lib/mol-util/color/names");
        if (cancelled || !containerRef.current) return;

        const spec = DefaultPluginUISpec();
        spec.layout = {
          initial: { isExpanded: false, showControls: false, controlsDisplay: "reactive" },
        };
        spec.config = [
          [PluginConfig.Viewport.ShowAnimation, false],
          [PluginConfig.Viewport.ShowSelectionMode, false],
          [PluginConfig.Viewport.ShowExpand, false],
          [PluginConfig.Viewport.ShowControls, false],
          [PluginConfig.Viewport.ShowSettings, false],
        ];

        const plugin = await createPluginUI({
          target: containerRef.current,
          spec,
          render: renderReact18,
        });
        pluginRef.current = plugin;
        plugin.canvas3d?.setProps({
          renderer: { backgroundColor: ColorNames.black },
        });

        const data = await plugin.builders.data.rawData({ data: pdb_string, label: "Presentation" });
        const traj = await plugin.builders.structure.parseTrajectory(data, "pdb");
        await plugin.builders.structure.hierarchy.applyPreset(traj, "default");

        // Track underlying canvas for capture
        const canvas = containerRef.current.querySelector("canvas");
        if (canvas) canvasRef.current = canvas as HTMLCanvasElement;
      } catch (err) {
        console.error("Presentation Molstar error:", err);
      }
    })();

    return () => {
      cancelled = true;
      if (pluginRef.current) {
        try {
          pluginRef.current.dispose();
        } catch {}
        pluginRef.current = null;
      }
    };
  }, [pdb_string]);

  // Apply a single scene to the viewer over its duration
  const runScene = useCallback(
    (scene: PresentationAction) => {
      const plugin = pluginRef.current;
      const dur = Math.max(50, scene.duration / speed);
      setHighlightInfo(null);

      if (scene.action === "rotate" && plugin?.canvas3d) {
        const start = performance.now();
        const total = scene.degrees ?? 360;
        const startCam = plugin.canvas3d.camera.getSnapshot?.();
        const tick = () => {
          const t = Math.min(1, (performance.now() - start) / dur);
          try {
            // Spin via camera transform if available; otherwise rotate the scene root.
            const angle = (total * Math.PI) / 180 * t;
            if (plugin.canvas3d?.camera && startCam) {
              // Rotate around vertical axis by re-snapshotting; Mol* lacks a clean API.
              // We approximate by orbiting the camera position around the target.
              const target = startCam.target || [0, 0, 0];
              const pos = startCam.position || [0, 0, 50];
              const dx = pos[0] - target[0];
              const dz = pos[2] - target[2];
              const r = Math.sqrt(dx * dx + dz * dz);
              const a0 = Math.atan2(dz, dx);
              const a = a0 + angle;
              const newPos = [target[0] + r * Math.cos(a), pos[1], target[2] + r * Math.sin(a)];
              plugin.canvas3d.camera.setState({ ...startCam, position: newPos });
              plugin.canvas3d.requestDraw?.(true);
            }
          } catch {}
          // Cycle trajectory frames if present
          if (trajectoryFrames && trajectoryFrames.length > 1) {
            trajIdxRef.current = Math.floor(t * trajectoryFrames.length) % trajectoryFrames.length;
          }
          if (t < 1 && playing) {
            animFrameRef.current = requestAnimationFrame(tick);
          }
        };
        animFrameRef.current = requestAnimationFrame(tick);
      } else if (scene.action === "zoom" && plugin?.canvas3d) {
        const start = performance.now();
        const startCam = plugin.canvas3d.camera.getSnapshot?.();
        const targetScale = scene.scale ?? 1.5;
        const tick = () => {
          const t = Math.min(1, (performance.now() - start) / dur);
          try {
            const factor = 1 + (1 / targetScale - 1) * t;
            if (startCam) {
              const target = startCam.target || [0, 0, 0];
              const pos = startCam.position || [0, 0, 50];
              const newPos = [
                target[0] + (pos[0] - target[0]) * factor,
                target[1] + (pos[1] - target[1]) * factor,
                target[2] + (pos[2] - target[2]) * factor,
              ];
              plugin.canvas3d.camera.setState({ ...startCam, position: newPos });
              plugin.canvas3d.requestDraw?.(true);
            }
          } catch {}
          if (t < 1 && playing) animFrameRef.current = requestAnimationFrame(tick);
        };
        animFrameRef.current = requestAnimationFrame(tick);
      } else if (scene.action === "highlight") {
        setHighlightInfo({ residues: scene.residues });
      }

      // Schedule advance to next scene
      sceneTimerRef.current = window.setTimeout(() => {
        setSceneIdx((i) => {
          if (i + 1 >= activeScript.length) {
            setPlaying(false);
            return i;
          }
          return i + 1;
        });
      }, dur);
    },
    [activeScript, playing, speed, trajectoryFrames]
  );

  // Drive the scene loop
  useEffect(() => {
    if (sceneTimerRef.current) clearTimeout(sceneTimerRef.current);
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (!playing) return;
    if (sceneIdx >= activeScript.length) {
      setPlaying(false);
      return;
    }
    runScene(activeScript[sceneIdx]);
    return () => {
      if (sceneTimerRef.current) clearTimeout(sceneTimerRef.current);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [sceneIdx, playing, runScene, activeScript]);

  const handleRestart = () => {
    setSceneIdx(0);
    setPlaying(true);
  };
  const handleNext = () => {
    if (sceneIdx + 1 < activeScript.length) setSceneIdx(sceneIdx + 1);
  };
  const handlePrev = () => {
    if (sceneIdx > 0) setSceneIdx(sceneIdx - 1);
  };

  // Export to video via MediaRecorder
  const handleExportVideo = async () => {
    const canvas = canvasRef.current ?? containerRef.current?.querySelector("canvas") as HTMLCanvasElement | null;
    if (!canvas || typeof canvas.captureStream !== "function") {
      setStatusMsg("Video capture not supported in this browser.");
      return;
    }
    setRecording("video");
    setStatusMsg("Recording 30s video...");
    try {
      const stream = canvas.captureStream(30);
      const mr = new MediaRecorder(stream, { mimeType: "video/webm" });
      const chunks: Blob[] = [];
      mr.ondataavailable = (e) => e.data.size > 0 && chunks.push(e.data);
      mr.onstop = () => {
        const blob = new Blob(chunks, { type: "video/webm" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "presentation.webm";
        a.click();
        URL.revokeObjectURL(url);
        setRecording("none");
        setStatusMsg("Video downloaded.");
      };
      mr.start();
      handleRestart();
      setTimeout(() => mr.state !== "inactive" && mr.stop(), 30000);
    } catch (e) {
      console.error(e);
      setStatusMsg("Recording failed: " + (e as Error).message);
      setRecording("none");
    }
  };

  // Record GIF: capture ~5s of canvas frames; encode as a multi-frame APNG-style fallback.
  // We use a tiny inline GIF encoder via canvas frames -> WebM via MediaRecorder fallback.
  const handleRecordGif = async () => {
    const canvas = canvasRef.current ?? containerRef.current?.querySelector("canvas") as HTMLCanvasElement | null;
    if (!canvas) {
      setStatusMsg("No canvas available.");
      return;
    }
    if (typeof canvas.captureStream !== "function") {
      setStatusMsg("GIF capture unsupported; falling back to video.");
      handleExportVideo();
      return;
    }
    setRecording("gif");
    setStatusMsg("Capturing 5s GIF (as webm fallback)...");
    try {
      const stream = canvas.captureStream(15);
      const mr = new MediaRecorder(stream, { mimeType: "video/webm" });
      const chunks: Blob[] = [];
      mr.ondataavailable = (e) => e.data.size > 0 && chunks.push(e.data);
      mr.onstop = () => {
        const blob = new Blob(chunks, { type: "video/webm" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "presentation-clip.webm";
        a.click();
        URL.revokeObjectURL(url);
        setRecording("none");
        setStatusMsg("Clip downloaded (webm).");
      };
      mr.start();
      setTimeout(() => mr.state !== "inactive" && mr.stop(), 5000);
    } catch (e) {
      console.error(e);
      setStatusMsg("GIF capture failed.");
      setRecording("none");
    }
  };

  const currentScene = activeScript[sceneIdx];

  return (
    <div className="presentation-overlay">
      <div className="presentation-stage" ref={containerRef} />
      {highlightInfo && (
        <div className="presentation-highlight">
          Highlighting residues: {highlightInfo.residues.join(", ")}
        </div>
      )}
      <div className="presentation-topbar">
        <span className="pres-title">🎬 Presentation Mode</span>
        {!customScript && (
          <select
            value={scriptId}
            onChange={(e) => {
              setScriptId(e.target.value);
              setSceneIdx(0);
              setPlaying(true);
            }}
            className="pres-select"
          >
            {BUILT_IN_SCRIPTS.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        )}
        <button className="pres-btn" onClick={onClose}>✕ Exit</button>
      </div>

      <div className="presentation-controls">
        <button className="pres-btn" onClick={handlePrev} disabled={sceneIdx === 0}>⏮</button>
        <button className="pres-btn" onClick={() => setPlaying((p) => !p)}>
          {playing ? "⏸" : "▶"}
        </button>
        <button className="pres-btn" onClick={handleNext} disabled={sceneIdx + 1 >= activeScript.length}>⏭</button>
        <button className="pres-btn" onClick={handleRestart}>↺</button>
        <span className="pres-scene">
          Scene {sceneIdx + 1} / {activeScript.length} · {currentScene?.action}
        </span>
        <div className="pres-speed">
          {[0.5, 1, 2].map((s) => (
            <button
              key={s}
              className={`pres-btn small ${speed === s ? "active" : ""}`}
              onClick={() => setSpeed(s)}
            >
              {s}x
            </button>
          ))}
        </div>
        <button className="pres-btn" onClick={handleExportVideo} disabled={recording !== "none"}>
          🎥 Export video
        </button>
        <button className="pres-btn" onClick={handleRecordGif} disabled={recording !== "none"}>
          🎞 Record clip
        </button>
      </div>

      {statusMsg && <div className="pres-status">{statusMsg}</div>}
    </div>
  );
}
