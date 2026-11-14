import type { ChangeEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import "./TrajectoryPlayer.css";

export interface TrajectoryPlayerProps {
  frames: string[];
  onFrameChange?: (index: number) => void;
  onFramesLoaded?: (frames: string[]) => void;
  /** Current static structure used as the seed for "Generate demo trajectory". */
  sourcePdb?: string;
}

/** Split a multi-MODEL PDB into an array of per-frame PDB strings. */
export function splitMultiModelPdb(text: string): string[] {
  const lines = text.split(/\r?\n/);
  const frames: string[] = [];
  let current: string[] = [];
  let inModel = false;
  let header: string[] = [];
  for (const line of lines) {
    if (line.startsWith("MODEL")) {
      inModel = true;
      current = [];
    } else if (line.startsWith("ENDMDL")) {
      if (current.length) frames.push(current.join("\n") + "\nEND\n");
      current = [];
      inModel = false;
    } else if (inModel) {
      current.push(line);
    } else {
      header.push(line);
    }
  }
  if (frames.length === 0) {
    // Single-model PDB: return the whole file as one frame
    return [text];
  }
  // Prepend any CRYST1/HEADER lines we collected before the first MODEL
  const headerText = header.filter((l) =>
    l.startsWith("HEADER") || l.startsWith("CRYST1") || l.startsWith("TITLE"),
  ).join("\n");
  if (headerText) {
    return frames.map((f) => headerText + "\n" + f);
  }
  return frames;
}

/** Generate a demo trajectory by perturbing CA atoms of the seed PDB. */
export function generateDemoTrajectory(sourcePdb: string, nFrames = 20, amplitude = 0.3): string[] {
  if (!sourcePdb) return [];
  const lines = sourcePdb.split(/\r?\n/);
  const frames: string[] = [];
  for (let f = 0; f < nFrames; f++) {
    const out: string[] = [];
    for (const line of lines) {
      if ((line.startsWith("ATOM") || line.startsWith("HETATM")) && line.length >= 54) {
        const atomName = line.substring(12, 16).trim();
        if (atomName === "CA") {
          const x = parseFloat(line.substring(30, 38));
          const y = parseFloat(line.substring(38, 46));
          const z = parseFloat(line.substring(46, 54));
          if (!isNaN(x) && !isNaN(y) && !isNaN(z)) {
            const dx = (Math.random() - 0.5) * 2 * amplitude;
            const dy = (Math.random() - 0.5) * 2 * amplitude;
            const dz = (Math.random() - 0.5) * 2 * amplitude;
            const fmt = (v: number) => v.toFixed(3).padStart(8);
            out.push(
              line.substring(0, 30) +
                fmt(x + dx) +
                fmt(y + dy) +
                fmt(z + dz) +
                line.substring(54),
            );
            continue;
          }
        }
      }
      out.push(line);
    }
    frames.push(out.join("\n"));
  }
  return frames;
}

const SPEEDS = [0.5, 1, 2, 4] as const;
const BASE_FPS = 10;

export function TrajectoryPlayer({
  frames,
  onFrameChange,
  onFramesLoaded,
  sourcePdb,
}: TrajectoryPlayerProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleFile = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const loaded = splitMultiModelPdb(text);
      if (loaded.length === 0) {
        console.warn("No frames parsed from", file.name);
        return;
      }
      onFramesLoaded?.(loaded);
    } catch (err) {
      console.error("Trajectory load failed:", err);
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDemo = () => {
    if (!sourcePdb) {
      console.warn("No source PDB to generate demo trajectory from");
      return;
    }
    const demo = generateDemoTrajectory(sourcePdb, 20, 0.3);
    if (demo.length) onFramesLoaded?.(demo);
  };
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<number>(1);
  const [loop, setLoop] = useState(true);
  const rafRef = useRef<number | null>(null);
  const lastTickRef = useRef<number>(0);
  const indexRef = useRef(0);

  const total = frames.length;

  const emit = useCallback(
    (i: number) => {
      indexRef.current = i;
      setIndex(i);
      onFrameChange?.(i);
    },
    [onFrameChange],
  );

  // Reset when frames swap out
  useEffect(() => {
    emit(0);
    setPlaying(false);
  }, [frames, emit]);

  useEffect(() => {
    if (!playing || total <= 1) return;
    const intervalMs = 1000 / (BASE_FPS * speed);

    const tick = (now: number) => {
      if (!lastTickRef.current) lastTickRef.current = now;
      const elapsed = now - lastTickRef.current;
      if (elapsed >= intervalMs) {
        lastTickRef.current = now;
        let next = indexRef.current + 1;
        if (next >= total) {
          if (loop) {
            next = 0;
          } else {
            setPlaying(false);
            return;
          }
        }
        emit(next);
      }
      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
      lastTickRef.current = 0;
    };
  }, [playing, speed, loop, total, emit]);

  const stepBack = () => emit(Math.max(0, indexRef.current - 1));
  const stepFwd = () => emit(Math.min(total - 1, indexRef.current + 1));
  const togglePlay = () => {
    if (total <= 1) return;
    setPlaying((p) => !p);
  };

  return (
    <div className="trajectory-player">
      <div className="tp-controls">
        <button
          className="tp-btn"
          onClick={stepBack}
          disabled={total === 0 || index === 0}
          title="Step back"
          aria-label="Step back"
        >
          {"\u23EE"}
        </button>
        <button
          className="tp-btn tp-play"
          onClick={togglePlay}
          disabled={total <= 1}
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? "\u23F8" : "\u25B6"}
        </button>
        <button
          className="tp-btn"
          onClick={stepFwd}
          disabled={total === 0 || index >= total - 1}
          title="Step forward"
          aria-label="Step forward"
        >
          {"\u23ED"}
        </button>
        <button
          className={`tp-btn tp-loop ${loop ? "active" : ""}`}
          onClick={() => setLoop((l) => !l)}
          title="Toggle loop"
          aria-label="Toggle loop"
        >
          {"\u21BB"}
        </button>
        <div className="tp-speed">
          <label htmlFor="tp-speed-range">Speed</label>
          <input
            id="tp-speed-range"
            type="range"
            min={0}
            max={SPEEDS.length - 1}
            step={1}
            value={SPEEDS.indexOf(speed as (typeof SPEEDS)[number])}
            onChange={(e) => setSpeed(SPEEDS[Number(e.target.value)])}
          />
          <span className="tp-speed-label">{speed}x</span>
        </div>
      </div>
      <div className="tp-load">
        <button
          className="tp-btn"
          onClick={() => fileInputRef.current?.click()}
          title="Load a multi-MODEL PDB trajectory"
        >
          Load trajectory
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdb,.ent,chemical/x-pdb"
          style={{ display: "none" }}
          onChange={handleFile}
        />
        <button
          className="tp-btn"
          onClick={handleDemo}
          disabled={!sourcePdb}
          title="Generate a 20-frame demo trajectory from the current structure"
        >
          Generate demo trajectory
        </button>
      </div>
      <div className="tp-scrubber">
        <input
          type="range"
          min={0}
          max={Math.max(0, total - 1)}
          value={index}
          disabled={total === 0}
          onChange={(e) => emit(Number(e.target.value))}
        />
        <div className="tp-frame-count">
          {total === 0 ? "no frames" : `frame ${index + 1} / ${total}`}
        </div>
      </div>
    </div>
  );
}

export default TrajectoryPlayer;
