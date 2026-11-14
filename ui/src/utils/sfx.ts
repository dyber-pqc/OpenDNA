// Pure Web Audio API sound effects - no audio files needed.
// Each sound is a synthesized oscillator with a custom envelope.

const STORAGE_KEY = "opendna.sfx_enabled";
export const SFX_MUTE_HOTKEY = "m";

let _ctx: AudioContext | null = null;

function getCtx(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (_ctx) return _ctx;
  try {
    const AC = (window as any).AudioContext || (window as any).webkitAudioContext;
    if (!AC) return null;
    _ctx = new AC();
    return _ctx;
  } catch {
    return null;
  }
}

export function getSfxEnabled(): boolean {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === null) return true;
    return v === "true";
  } catch {
    return true;
  }
}

export function setSfxEnabled(enabled: boolean): void {
  try {
    localStorage.setItem(STORAGE_KEY, enabled ? "true" : "false");
  } catch {
    /* ignore */
  }
}

interface Beep {
  freq: number;
  type?: OscillatorType;
  duration: number;
  attack?: number;
  release?: number;
  gain?: number;
  slideTo?: number;
}

function playBeeps(beeps: Beep[]): void {
  if (!getSfxEnabled()) return;
  const ctx = getCtx();
  if (!ctx) return;
  try {
    if (ctx.state === "suspended") ctx.resume().catch(() => {});
    let t = ctx.currentTime;
    for (const b of beeps) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = b.type || "sine";
      osc.frequency.setValueAtTime(b.freq, t);
      if (b.slideTo !== undefined) {
        osc.frequency.linearRampToValueAtTime(b.slideTo, t + b.duration);
      }
      const attack = b.attack ?? 0.005;
      const release = b.release ?? 0.05;
      const peak = b.gain ?? 0.15;
      gain.gain.setValueAtTime(0, t);
      gain.gain.linearRampToValueAtTime(peak, t + attack);
      gain.gain.linearRampToValueAtTime(0, t + b.duration + release);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(t);
      osc.stop(t + b.duration + release + 0.02);
      t += b.duration;
    }
  } catch {
    /* audio failed; ignore */
  }
}

export function playDing(): void {
  playBeeps([{ freq: 1320, type: "sine", duration: 0.12, gain: 0.18, release: 0.15 }]);
}

export function playSuccess(): void {
  playBeeps([
    { freq: 660, type: "triangle", duration: 0.08, gain: 0.18 },
    { freq: 880, type: "triangle", duration: 0.08, gain: 0.2 },
    { freq: 1320, type: "triangle", duration: 0.12, gain: 0.2, release: 0.12 },
  ]);
}

export function playFail(): void {
  playBeeps([
    { freq: 300, type: "sawtooth", duration: 0.12, gain: 0.18, slideTo: 180 },
    { freq: 180, type: "sawtooth", duration: 0.18, gain: 0.16, slideTo: 90, release: 0.1 },
  ]);
}

export function playClick(): void {
  playBeeps([{ freq: 2000, type: "square", duration: 0.02, gain: 0.08, release: 0.02 }]);
}

export function playWhoosh(): void {
  playBeeps([
    { freq: 200, type: "sine", duration: 0.22, gain: 0.12, slideTo: 1200, release: 0.08 },
  ]);
}
