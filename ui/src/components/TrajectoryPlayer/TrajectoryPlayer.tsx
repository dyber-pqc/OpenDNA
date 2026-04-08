import { useCallback, useEffect, useRef, useState } from "react";
import "./TrajectoryPlayer.css";

export interface TrajectoryPlayerProps {
  frames: string[];
  onFrameChange?: (index: number) => void;
}

const SPEEDS = [0.5, 1, 2, 4] as const;
const BASE_FPS = 10;

export function TrajectoryPlayer({ frames, onFrameChange }: TrajectoryPlayerProps) {
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
