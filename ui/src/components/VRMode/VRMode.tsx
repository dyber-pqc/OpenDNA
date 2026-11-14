import { useEffect, useRef, useState } from "react";
import "./VRMode.css";

/**
 * VRMode — WebXR immersive view of the current PDB structure.
 *
 * Renders CA atoms as instanced WebGL spheres. No external dependencies:
 * the sphere mesh is generated at runtime and instanced positions come
 * from the parsed PDB. Controllers can "grab" the molecule to translate it.
 *
 * We avoid three.js / molstar here because WebXR inside Tauri is finicky
 * enough without an extra framework layer. Keeping this file self-contained
 * also means zero new deps in package.json.
 */

interface VRModeProps {
  pdbString: string | null;
  onClose: () => void;
}

type Vec3 = [number, number, number];

// ---------- PDB parsing ----------------------------------------------------

function parseCAAtoms(pdb: string): Vec3[] {
  const out: Vec3[] = [];
  const lines = pdb.split(/\r?\n/);
  for (const line of lines) {
    if (!line.startsWith("ATOM")) continue;
    const atomName = line.substring(12, 16).trim();
    if (atomName !== "CA") continue;
    const x = parseFloat(line.substring(30, 38));
    const y = parseFloat(line.substring(38, 46));
    const z = parseFloat(line.substring(46, 54));
    if (Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(z)) {
      out.push([x, y, z]);
    }
  }
  return out;
}

function centerAtoms(atoms: Vec3[]): { centered: Vec3[]; scale: number } {
  if (atoms.length === 0) return { centered: [], scale: 1 };
  let cx = 0, cy = 0, cz = 0;
  for (const a of atoms) { cx += a[0]; cy += a[1]; cz += a[2]; }
  cx /= atoms.length; cy /= atoms.length; cz /= atoms.length;
  let maxR = 0;
  const centered: Vec3[] = atoms.map((a) => {
    const v: Vec3 = [a[0] - cx, a[1] - cy, a[2] - cz];
    const r = Math.hypot(v[0], v[1], v[2]);
    if (r > maxR) maxR = r;
    return v;
  });
  // Target radius ~0.3m in headset space.
  const scale = maxR > 0 ? 0.3 / maxR : 0.01;
  return { centered, scale };
}

// ---------- Math helpers (column-major mat4) -------------------------------

type Mat4 = Float32Array;

function mat4Identity(): Mat4 {
  const m = new Float32Array(16);
  m[0] = 1; m[5] = 1; m[10] = 1; m[15] = 1;
  return m;
}

function mat4Multiply(a: Mat4, b: Mat4): Mat4 {
  const out = new Float32Array(16);
  for (let i = 0; i < 4; i++) {
    for (let j = 0; j < 4; j++) {
      let s = 0;
      for (let k = 0; k < 4; k++) s += a[i + k * 4] * b[k + j * 4];
      out[i + j * 4] = s;
    }
  }
  return out;
}

function mat4Translate(x: number, y: number, z: number): Mat4 {
  const m = mat4Identity();
  m[12] = x; m[13] = y; m[14] = z;
  return m;
}

// ---------- Icosphere mesh ------------------------------------------------

function buildIcosphere(subdiv: number): { positions: Float32Array; indices: Uint16Array } {
  const t = (1 + Math.sqrt(5)) / 2;
  let verts: number[][] = [
    [-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0],
    [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t],
    [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1],
  ].map((v) => {
    const l = Math.hypot(v[0], v[1], v[2]);
    return [v[0] / l, v[1] / l, v[2] / l];
  });
  let faces: number[][] = [
    [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
    [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
    [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
    [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1],
  ];
  for (let s = 0; s < subdiv; s++) {
    const mid = new Map<string, number>();
    const next: number[][] = [];
    const midpoint = (a: number, b: number) => {
      const key = a < b ? `${a}_${b}` : `${b}_${a}`;
      const existing = mid.get(key);
      if (existing !== undefined) return existing;
      const va = verts[a], vb = verts[b];
      const v: number[] = [(va[0] + vb[0]) / 2, (va[1] + vb[1]) / 2, (va[2] + vb[2]) / 2];
      const l = Math.hypot(v[0], v[1], v[2]);
      v[0] /= l; v[1] /= l; v[2] /= l;
      verts.push(v);
      const idx = verts.length - 1;
      mid.set(key, idx);
      return idx;
    };
    for (const f of faces) {
      const a = midpoint(f[0], f[1]);
      const b = midpoint(f[1], f[2]);
      const c = midpoint(f[2], f[0]);
      next.push([f[0], a, c]);
      next.push([f[1], b, a]);
      next.push([f[2], c, b]);
      next.push([a, b, c]);
    }
    faces = next;
  }
  const positions = new Float32Array(verts.length * 3);
  for (let i = 0; i < verts.length; i++) {
    positions[i * 3] = verts[i][0];
    positions[i * 3 + 1] = verts[i][1];
    positions[i * 3 + 2] = verts[i][2];
  }
  const indices = new Uint16Array(faces.length * 3);
  for (let i = 0; i < faces.length; i++) {
    indices[i * 3] = faces[i][0];
    indices[i * 3 + 1] = faces[i][1];
    indices[i * 3 + 2] = faces[i][2];
  }
  return { positions, indices };
}

// ---------- Shaders -------------------------------------------------------

const VERT = `
attribute vec3 a_pos;
attribute vec3 a_offset;
uniform mat4 u_proj;
uniform mat4 u_view;
uniform mat4 u_model;
uniform float u_radius;
varying vec3 v_normal;
void main() {
  vec3 world = a_offset + a_pos * u_radius;
  gl_Position = u_proj * u_view * u_model * vec4(world, 1.0);
  v_normal = normalize(a_pos);
}
`;

const FRAG = `
precision mediump float;
varying vec3 v_normal;
void main() {
  vec3 light = normalize(vec3(0.3, 0.8, 0.5));
  float d = max(dot(normalize(v_normal), light), 0.0);
  vec3 base = vec3(0.35, 0.75, 1.0);
  gl_FragColor = vec4(base * (0.25 + 0.75 * d), 1.0);
}
`;

// ---------- Component -----------------------------------------------------

type XRSupport =
  | { kind: "unsupported" }
  | { kind: "checking" }
  | { kind: "ready" }
  | { kind: "in-session" }
  | { kind: "error"; message: string };

export default function VRMode({ pdbString, onClose }: VRModeProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const sessionRef = useRef<any>(null);
  const [status, setStatus] = useState<XRSupport>({ kind: "checking" });
  const [atomCount, setAtomCount] = useState(0);

  useEffect(() => {
    const nav = navigator as any;
    if (!nav.xr || typeof nav.xr.isSessionSupported !== "function") {
      setStatus({ kind: "unsupported" });
      return;
    }
    nav.xr
      .isSessionSupported("immersive-vr")
      .then((ok: boolean) => {
        setStatus(ok ? { kind: "ready" } : { kind: "unsupported" });
      })
      .catch(() => setStatus({ kind: "unsupported" }));
  }, []);

  const enterVR = async () => {
    if (!canvasRef.current) return;
    const nav = navigator as any;
    let atoms: Vec3[] = [];
    if (pdbString) atoms = parseCAAtoms(pdbString);
    setAtomCount(atoms.length);
    const { centered, scale } = centerAtoms(atoms);

    const canvas = canvasRef.current;
    const gl = canvas.getContext("webgl", { xrCompatible: true } as any) as WebGLRenderingContext | null;
    if (!gl) {
      setStatus({ kind: "error", message: "WebGL not available" });
      return;
    }

    // Build GL resources.
    const ico = buildIcosphere(1);
    const posBuf = gl.createBuffer()!;
    gl.bindBuffer(gl.ARRAY_BUFFER, posBuf);
    gl.bufferData(gl.ARRAY_BUFFER, ico.positions, gl.STATIC_DRAW);
    const idxBuf = gl.createBuffer()!;
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, ico.indices, gl.STATIC_DRAW);

    const compile = (type: number, src: string) => {
      const s = gl.createShader(type)!;
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
        const info = gl.getShaderInfoLog(s);
        throw new Error("Shader compile error: " + info);
      }
      return s;
    };
    const prog = gl.createProgram()!;
    gl.attachShader(prog, compile(gl.VERTEX_SHADER, VERT));
    gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, FRAG));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      throw new Error("Program link error: " + gl.getProgramInfoLog(prog));
    }
    gl.useProgram(prog);
    const aPos = gl.getAttribLocation(prog, "a_pos");
    const uProj = gl.getUniformLocation(prog, "u_proj");
    const uView = gl.getUniformLocation(prog, "u_view");
    const uModel = gl.getUniformLocation(prog, "u_model");
    const uRadius = gl.getUniformLocation(prog, "u_radius");

    gl.enable(gl.DEPTH_TEST);
    gl.clearColor(0.02, 0.03, 0.06, 1.0);

    // Model state. Grab offset is applied on top of auto-centering.
    const modelOffset: Vec3 = [0, 1.2, -0.6]; // in front of user at head height
    const grabOffset: Vec3 = [0, 0, 0];
    let grabbingFrom: Vec3 | null = null;

    let session: any;
    try {
      session = await nav.xr.requestSession("immersive-vr", {
        optionalFeatures: ["local-floor"],
      });
    } catch (e: any) {
      setStatus({ kind: "error", message: e?.message ?? "requestSession failed" });
      return;
    }
    sessionRef.current = session;
    setStatus({ kind: "in-session" });

    const XRWebGLLayer = (window as any).XRWebGLLayer;
    const baseLayer = new XRWebGLLayer(session, gl);
    await session.updateRenderState({ baseLayer });

    let refSpace: any;
    try {
      refSpace = await session.requestReferenceSpace("local-floor");
    } catch {
      refSpace = await session.requestReferenceSpace("local");
    }

    const onFrame = (_t: number, frame: any) => {
      const sess = frame.session;
      sess.requestAnimationFrame(onFrame);

      // Handle controllers.
      for (const source of sess.inputSources) {
        if (!source.gripSpace) continue;
        const pose = frame.getPose(source.gripSpace, refSpace);
        if (!pose) continue;
        const p = pose.transform.position;
        const gp = source.gamepad;
        const pressed = !!(gp && gp.buttons && (gp.buttons[1]?.pressed || gp.buttons[0]?.pressed));
        if (pressed) {
          if (!grabbingFrom) {
            grabbingFrom = [p.x, p.y, p.z];
          } else {
            grabOffset[0] += p.x - grabbingFrom[0];
            grabOffset[1] += p.y - grabbingFrom[1];
            grabOffset[2] += p.z - grabbingFrom[2];
            grabbingFrom = [p.x, p.y, p.z];
          }
        } else {
          grabbingFrom = null;
        }
      }

      const glLayer = sess.renderState.baseLayer;
      gl.bindFramebuffer(gl.FRAMEBUFFER, glLayer.framebuffer);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

      const pose = frame.getViewerPose(refSpace);
      if (!pose) return;

      const model = mat4Translate(
        modelOffset[0] + grabOffset[0],
        modelOffset[1] + grabOffset[1],
        modelOffset[2] + grabOffset[2]
      );

      gl.useProgram(prog);
      gl.uniformMatrix4fv(uModel, false, model);
      gl.uniform1f(uRadius, 0.015);

      gl.bindBuffer(gl.ARRAY_BUFFER, posBuf);
      gl.enableVertexAttribArray(aPos);
      gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf);

      for (const view of pose.views) {
        const vp = glLayer.getViewport(view);
        gl.viewport(vp.x, vp.y, vp.width, vp.height);
        gl.uniformMatrix4fv(uProj, false, view.projectionMatrix as Float32Array);
        gl.uniformMatrix4fv(uView, false, view.transform.inverse.matrix as Float32Array);

        // Draw one sphere per CA atom. We upload translation via u_model multiplied
        // by per-atom translate, re-using the same sphere mesh.
        for (let i = 0; i < centered.length; i++) {
          const atom = centered[i];
          const atomMat = mat4Multiply(
            model,
            mat4Translate(atom[0] * scale, atom[1] * scale, atom[2] * scale)
          );
          gl.uniformMatrix4fv(uModel, false, atomMat);
          gl.drawElements(gl.TRIANGLES, ico.indices.length, gl.UNSIGNED_SHORT, 0);
        }
      }
    };

    session.addEventListener("end", () => {
      sessionRef.current = null;
      setStatus({ kind: "ready" });
    });
    session.requestAnimationFrame(onFrame);
  };

  const exitVR = async () => {
    const s = sessionRef.current;
    if (s) {
      try { await s.end(); } catch { /* ignore */ }
    }
  };

  return (
    <div className="vr-mode">
      <div className="vr-header">
        <h2>VR Mode</h2>
        <button className="vr-close" onClick={onClose}>Close</button>
      </div>
      <div className="vr-body">
        <canvas ref={canvasRef} className="vr-canvas" width={640} height={360} />

        {status.kind === "checking" && <p>Checking WebXR support…</p>}

        {status.kind === "unsupported" && (
          <div className="vr-unsupported">
            <p><strong>WebXR is not supported in this environment.</strong></p>
            <p>
              To use VR mode you need a WebXR-capable browser (Chrome/Edge with a
              connected headset) or the Tauri build with WebView2 + headset
              runtime installed.
            </p>
            <p>
              <a
                href="https://immersiveweb.dev/"
                target="_blank"
                rel="noopener noreferrer"
              >
                Install / setup guide →
              </a>
            </p>
          </div>
        )}

        {status.kind === "ready" && (
          <div className="vr-ready">
            <p>
              {pdbString
                ? "A structure is loaded. Put on your headset and press Enter VR."
                : "No structure loaded — VR will show an empty scene."}
            </p>
            <button className="vr-enter" onClick={enterVR}>Enter VR</button>
          </div>
        )}

        {status.kind === "in-session" && (
          <div className="vr-insession">
            <p>VR session active. {atomCount} CA atoms rendered. Squeeze a controller trigger to grab and move the molecule.</p>
            <button className="vr-exit" onClick={exitVR}>Exit VR</button>
          </div>
        )}

        {status.kind === "error" && (
          <div className="vr-error">
            <p>Could not start VR: {status.message}</p>
          </div>
        )}
      </div>
    </div>
  );
}
