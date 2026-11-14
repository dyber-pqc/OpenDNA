import { useEffect, useRef, useState } from "react";
import ExplainButton from "../ExplainButton/ExplainButton";
import PresentationMode from "../PresentationMode/PresentationMode";
import * as api from "../../api/client";
import "./ProteinViewer.css";

interface ScoreData {
  overall: number;
  confidence: number;
  breakdown: Record<string, number>;
  summary: string;
  recommendations: string[];
}

interface DesignCandidate {
  rank: number;
  sequence: string;
  score: number;
  recovery: number;
}

interface ProteinViewerProps {
  pdbData: string;
  compareData?: string;
  score?: ScoreData | null;
  designResults?: DesignCandidate[] | null;
  onUseCandidate?: (sequence: string) => void;
  onCloseDesign?: () => void;
  trajectoryFrames?: string[];
  currentFrame?: number;
  onMutate?: (chain: string, position: number, newAA: string, oldAA: string) => void;
}

// 3-letter to 1-letter amino acid mapping for residues from Molstar
const THREE_TO_ONE: Record<string, string> = {
  ALA: "A", ARG: "R", ASN: "N", ASP: "D", CYS: "C",
  GLU: "E", GLN: "Q", GLY: "G", HIS: "H", ILE: "I",
  LEU: "L", LYS: "K", MET: "M", PHE: "F", PRO: "P",
  SER: "S", THR: "T", TRP: "W", TYR: "Y", VAL: "V",
};

const AA_LIST: { code: string; name: string }[] = [
  { code: "A", name: "Alanine" }, { code: "R", name: "Arginine" },
  { code: "N", name: "Asparagine" }, { code: "D", name: "Aspartate" },
  { code: "C", name: "Cysteine" }, { code: "E", name: "Glutamate" },
  { code: "Q", name: "Glutamine" }, { code: "G", name: "Glycine" },
  { code: "H", name: "Histidine" }, { code: "I", name: "Isoleucine" },
  { code: "L", name: "Leucine" }, { code: "K", name: "Lysine" },
  { code: "M", name: "Methionine" }, { code: "F", name: "Phenylalanine" },
  { code: "P", name: "Proline" }, { code: "S", name: "Serine" },
  { code: "T", name: "Threonine" }, { code: "W", name: "Tryptophan" },
  { code: "Y", name: "Tyrosine" }, { code: "V", name: "Valine" },
];

function ProteinViewer({
  pdbData,
  compareData,
  score,
  designResults,
  onUseCandidate,
  onCloseDesign,
  onMutate,
  trajectoryFrames,
  currentFrame,
}: ProteinViewerProps) {
  // When a trajectory is active, swap the displayed frame in for pdbData
  const hasTraj = !!(trajectoryFrames && trajectoryFrames.length > 0);
  const frameIdx = hasTraj
    ? Math.max(0, Math.min((currentFrame ?? 0), (trajectoryFrames!.length - 1)))
    : 0;
  // (effectivePdb is inlined into the main rebuild effect as initialPdb.)
  const containerRef = useRef<HTMLDivElement>(null);
  const compareRef = useRef<HTMLDivElement>(null);
  const pluginRef = useRef<any>(null);
  const comparePluginRef = useRef<any>(null);
  const [stats, setStats] = useState<{ atoms: number; residues: number } | null>(null);
  const [colorMode, setColorMode] = useState<"chain" | "confidence">("confidence");
  const [repMode, setRepMode] = useState<"cartoon" | "ball-and-stick" | "spacefill" | "surface">("cartoon");
  const [hoverInfo, setHoverInfo] = useState<{
    residue: string;
    residueNum: number;
    chain: string;
    x: number;
    y: number;
  } | null>(null);
  const [presentationOpen, setPresentationOpen] = useState(false);
  const [foldseekOpen, setFoldseekOpen] = useState(false);
  const [foldseekBusy, setFoldseekBusy] = useState(false);
  const [foldseekResult, setFoldseekResult] = useState<api.FoldseekResult | null>(null);

  const runFoldseek = async () => {
    if (!pdbData) return;
    setFoldseekOpen(true);
    setFoldseekBusy(true);
    setFoldseekResult(null);
    try {
      const r = await api.foldseekSearch(pdbData, "afdb");
      setFoldseekResult(r);
    } catch (e: any) {
      setFoldseekResult({ error: e.message || String(e), hits: [] });
    } finally {
      setFoldseekBusy(false);
    }
  };

  const loadFoldseekHit = async (targetId: string) => {
    // Heuristic: AFDB ids like AF-P12345-F1 → fetch from AlphaFold DB
    const m = targetId.match(/AF[-_]([A-Z0-9]+)/i);
    if (m) {
      const acc = m[1];
      try {
        const resp = await fetch(`https://alphafold.ebi.ac.uk/files/AF-${acc}-F1-model_v4.pdb`);
        if (resp.ok) {
          const pdb = await resp.text();
          const blob = new Blob([pdb], { type: "chemical/x-pdb" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `${targetId}.pdb`;
          a.click();
          URL.revokeObjectURL(url);
        }
      } catch {/* ignore */}
    }
  };

  // Baseline used for the full-rebuild effect. When a trajectory is active, we
  // key off the *first* frame so scrubbing doesn't retrigger a full plugin
  // teardown — the in-place swap effect below handles frame changes.
  const rebuildKey = hasTraj ? (trajectoryFrames![0] || "") : pdbData;

  useEffect(() => {
    const initialPdb = hasTraj ? (trajectoryFrames![frameIdx] || trajectoryFrames![0]) : pdbData;
    if (!initialPdb || !containerRef.current) return;
    let cancelled = false;
    const pdbDataLocal = initialPdb;

    (async () => {
      try {
        const { createPluginUI } = await import("molstar/lib/mol-plugin-ui/index");
        const { renderReact18 } = await import("molstar/lib/mol-plugin-ui/react18");
        const { DefaultPluginUISpec } = await import("molstar/lib/mol-plugin-ui/spec");
        const { PluginConfig } = await import("molstar/lib/mol-plugin/config");
        const { ColorNames } = await import("molstar/lib/mol-util/color/names");

        if (cancelled || !containerRef.current) return;

        if (pluginRef.current) {
          pluginRef.current.dispose();
          pluginRef.current = null;
        }
        containerRef.current.innerHTML = "";

        const spec = DefaultPluginUISpec();
        spec.layout = {
          initial: {
            isExpanded: false,
            showControls: false,
            controlsDisplay: "reactive",
          },
        };
        spec.config = [
          [PluginConfig.Viewport.ShowAnimation, false],
          [PluginConfig.Viewport.ShowSelectionMode, false],
          [PluginConfig.Viewport.ShowExpand, false],
          [PluginConfig.Viewport.ShowControls, false],
          [PluginConfig.Viewport.ShowSettings, false],
          [PluginConfig.Viewport.ShowTrajectoryControls, false],
        ];

        const plugin = await createPluginUI({
          target: containerRef.current,
          spec,
          render: renderReact18,
        });
        pluginRef.current = plugin;

        // Set dark background
        plugin.canvas3d?.setProps({
          renderer: { backgroundColor: ColorNames.black },
        });

        // For confidence coloring, transform pLDDT (stored in B-factor as 0-1 fraction)
        // into proper AlphaFold pLDDT scale (0-100) so Molstar's plddt-confidence theme works.
        let pdbForViewer = pdbDataLocal;
        if (colorMode === "confidence") {
          pdbForViewer = pdbDataLocal
            .split("\n")
            .map((line) => {
              if ((line.startsWith("ATOM") || line.startsWith("HETATM")) && line.length >= 66) {
                const bfStr = line.substring(60, 66);
                const bf = parseFloat(bfStr.trim());
                if (!isNaN(bf) && bf <= 1.0) {
                  // Scale 0-1 to 0-100 for proper pLDDT theme
                  const scaled = (bf * 100).toFixed(2).padStart(6);
                  return line.substring(0, 60) + scaled + line.substring(66);
                }
              }
              return line;
            })
            .join("\n");
        }

        const data = await plugin.builders.data.rawData({
          data: pdbForViewer,
          label: "Predicted Structure",
        });
        const traj = await plugin.builders.structure.parseTrajectory(data, "pdb");

        // Apply the right base preset for the chosen representation mode.
        // Molstar's structure-hierarchy presets accept a `representationPresetParams`
        // option that picks among the registered structure-representation presets.
        const colorTheme = colorMode === "confidence" ? "plddt-confidence" : "chain-id";

        // First create a structure model with the default preset
        try {
          await plugin.builders.structure.hierarchy.applyPreset(traj, "default", {
            representationPresetParams: {
              theme: { globalName: colorTheme, focus: { name: colorTheme } },
            },
          } as any);
        } catch {
          await plugin.builders.structure.hierarchy.applyPreset(traj, "default");
        }

        // Now rebuild the representations to match repMode.
        // We do this by clearing existing representations on the polymer component
        // and adding fresh ones with the correct type.
        try {
          const struct = plugin.managers.structure.hierarchy.current.structures[0];
          if (struct?.components && struct.components.length > 0) {
            const update = plugin.build();
            // Remove all existing representations on each component
            for (const comp of struct.components) {
              for (const rep of comp.representations) {
                update.delete(rep.cell.transform.ref);
              }
            }
            await update.commit();

            // Add fresh representation with the chosen type
            const repTypeMap: Record<string, string> = {
              "cartoon": "cartoon",
              "ball-and-stick": "ball-and-stick",
              "spacefill": "spacefill",
              "surface": "molecular-surface",
            };
            const repType = repTypeMap[repMode] || "cartoon";

            for (const comp of struct.components) {
              await plugin.builders.structure.representation.addRepresentation(
                comp.cell,
                {
                  type: repType as any,
                  color: colorTheme as any,
                }
              );
            }
            // After adding, force the color theme on every representation —
            // this is what actually drives the colors in Molstar 4.x.
            try {
              const refreshed = plugin.managers.structure.hierarchy.current.structures[0];
              if (refreshed?.components) {
                await plugin.managers.structure.component.updateRepresentationsTheme(
                  refreshed.components as any,
                  { color: colorTheme as any },
                );
              }
            } catch (e) {
              console.debug("post-add theme update skipped:", e);
            }
          }
        } catch (e) {
          console.warn("Representation rebuild failed, falling back:", e);
          // Fallback: try to update the theme on existing reps
          try {
            const struct = plugin.managers.structure.hierarchy.current.structures[0];
            if (struct?.components) {
              for (const comp of struct.components) {
                await plugin.managers.structure.component.updateRepresentationsTheme(
                  [comp],
                  { color: colorTheme as any }
                );
              }
            }
          } catch (e2) {
            console.warn("Fallback theme update also failed:", e2);
          }
        }

        // Wire up click-to-show-residue: subscribe to Molstar's interaction stream.
        // When the user clicks an atom, find its residue and show a popup.
        try {
          if (plugin.behaviors?.interaction?.click) {
            const sub = plugin.behaviors.interaction.click.subscribe(
              (e: any) => {
                try {
                  const loc = e?.current?.loci;
                  if (!loc || loc.kind === "empty-loci") {
                    setHoverInfo(null);
                    return;
                  }
                  // Try to extract residue info from the loci
                  let residueName = "";
                  let residueNum = 0;
                  let chainId = "";

                  // Use a Loci.getFirstLocation API if available
                  if (loc.elements && loc.elements.length > 0) {
                    const elem = loc.elements[0];
                    const unit = elem.unit;
                    const idx = elem.indices?.[0] ?? 0;
                    if (unit?.model?.atomicHierarchy) {
                      const ah = unit.model.atomicHierarchy;
                      const elemIdx = unit.elements?.[idx] ?? idx;
                      const residueIdx = ah.residueAtomSegments?.index?.[elemIdx];
                      if (residueIdx !== undefined) {
                        residueName =
                          ah.atoms?.label_comp_id?.value(elemIdx) ||
                          ah.residues?.label_comp_id?.value(residueIdx) || "";
                        residueNum =
                          ah.residues?.auth_seq_id?.value(residueIdx) ?? 0;
                        chainId =
                          ah.chains?.label_asym_id?.value(
                            ah.chainAtomSegments?.index?.[elemIdx] ?? 0
                          ) || "A";
                      }
                    }
                  }

                  if (residueName) {
                    // Position the popup near the cursor
                    const containerRect =
                      containerRef.current?.getBoundingClientRect();
                    const x = containerRect ? containerRect.width / 2 : 100;
                    const y = containerRect ? containerRect.height / 2 : 100;
                    setHoverInfo({
                      residue: residueName,
                      residueNum,
                      chain: chainId,
                      x,
                      y,
                    });
                  } else {
                    setHoverInfo(null);
                  }
                } catch (err) {
                  console.debug("Click parsing failed:", err);
                }
              }
            );
            // Store the subscription for cleanup
            (plugin as any)._clickSub = sub;
          }
        } catch (e) {
          console.debug("Click handler setup failed (non-critical):", e);
        }

        // Stats
        const lines = pdbDataLocal.split("\n");
        const atomLines = lines.filter(
          (l) => l.startsWith("ATOM") || l.startsWith("HETATM")
        );
        const residueSet = new Set<string>();
        atomLines.forEach((l) => residueSet.add(l.substring(21, 27)));
        setStats({ atoms: atomLines.length, residues: residueSet.size });
      } catch (err) {
        console.error("Molstar error:", err);
      }
    })();

    return () => {
      cancelled = true;
      if (pluginRef.current) {
        try {
          (pluginRef.current as any)._clickSub?.unsubscribe?.();
        } catch {}
        pluginRef.current.dispose();
        pluginRef.current = null;
      }
    };
  }, [rebuildKey, repMode]);

  // In-place frame swap for trajectory scrubbing: replace the current structure's
  // data without tearing down the plugin, so playback is smooth.
  useEffect(() => {
    if (!hasTraj) return;
    const plugin = pluginRef.current;
    if (!plugin) return;
    let cancelled = false;
    (async () => {
      try {
        const frame = trajectoryFrames![frameIdx];
        if (!frame) return;

        let pdbForViewer = frame;
        if (colorMode === "confidence") {
          pdbForViewer = frame
            .split("\n")
            .map((line) => {
              if ((line.startsWith("ATOM") || line.startsWith("HETATM")) && line.length >= 66) {
                const bfStr = line.substring(60, 66);
                const bf = parseFloat(bfStr.trim());
                if (!isNaN(bf) && bf <= 1.0) {
                  const scaled = (bf * 100).toFixed(2).padStart(6);
                  return line.substring(0, 60) + scaled + line.substring(66);
                }
              }
              return line;
            })
            .join("\n");
        }

        await plugin.clear();
        if (cancelled) return;
        const data = await plugin.builders.data.rawData({
          data: pdbForViewer,
          label: `Trajectory frame ${frameIdx + 1}`,
        });
        if (cancelled) return;
        const traj = await plugin.builders.structure.parseTrajectory(data, "pdb");
        if (cancelled) return;

        const colorTheme = colorMode === "confidence" ? "plddt-confidence" : "chain-id";
        try {
          await plugin.builders.structure.hierarchy.applyPreset(traj, "default", {
            representationPresetParams: {
              theme: { globalName: colorTheme, focus: { name: colorTheme } },
            },
          } as any);
        } catch {
          await plugin.builders.structure.hierarchy.applyPreset(traj, "default");
        }
      } catch (e) {
        console.debug("trajectory frame swap failed:", e);
      }
    })();
    return () => {
      cancelled = true;
    };
    // Intentionally exclude trajectoryFrames identity from deps — we only want
    // frame index + color changes to drive the in-place swap. A full trajectory
    // swap-out is handled by rebuildKey in the main effect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasTraj, frameIdx, colorMode]);

  // Dedicated effect: when only colorMode changes, re-theme in place without
  // tearing down the plugin. This is what actually drives live color switches.
  useEffect(() => {
    const plugin = pluginRef.current;
    if (!plugin || !pdbData) return;
    (async () => {
      try {
        const colorTheme = colorMode === "confidence" ? "plddt-confidence" : "chain-id";
        const struct = plugin.managers?.structure?.hierarchy?.current?.structures?.[0];
        if (!struct?.components) return;
        await plugin.managers.structure.component.updateRepresentationsTheme(
          struct.components as any,
          { color: colorTheme as any },
        );
      } catch (e) {
        console.debug("color re-theme failed:", e);
      }
    })();
  }, [colorMode, pdbData]);

  // Compare structure viewer
  useEffect(() => {
    if (!compareData || !compareRef.current) return;
    let cancelled = false;

    (async () => {
      try {
        const { createPluginUI } = await import("molstar/lib/mol-plugin-ui/index");
        const { renderReact18 } = await import("molstar/lib/mol-plugin-ui/react18");
        const { DefaultPluginUISpec } = await import("molstar/lib/mol-plugin-ui/spec");
        const { PluginConfig } = await import("molstar/lib/mol-plugin/config");
        const { ColorNames } = await import("molstar/lib/mol-util/color/names");

        if (cancelled || !compareRef.current) return;

        if (comparePluginRef.current) {
          comparePluginRef.current.dispose();
          comparePluginRef.current = null;
        }
        compareRef.current.innerHTML = "";

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
          target: compareRef.current,
          spec,
          render: renderReact18,
        });
        comparePluginRef.current = plugin;
        plugin.canvas3d?.setProps({
          renderer: { backgroundColor: ColorNames.black },
        });

        const data = await plugin.builders.data.rawData({
          data: compareData,
          label: "Compare",
        });
        const traj = await plugin.builders.structure.parseTrajectory(data, "pdb");
        await plugin.builders.structure.hierarchy.applyPreset(traj, "default");
      } catch (err) {
        console.error("Compare Molstar error:", err);
      }
    })();

    return () => {
      cancelled = true;
      if (comparePluginRef.current) {
        comparePluginRef.current.dispose();
        comparePluginRef.current = null;
      }
    };
  }, [compareData]);

  if (score) {
    const pct = Math.round(score.overall * 100);
    return (
      <div className="protein-viewer">
        <div className="score-card">
          <div className="score-header">
            <div className="score-circle">
              <div className="score-pct">{pct}</div>
              <div className="score-label">/ 100</div>
            </div>
            <div className="score-summary">
              <h2>
                Protein Evaluation{" "}
                <ExplainButton
                  context={`Overall score: ${Math.round(score.overall * 100)}/100. Summary: ${score.summary}. Breakdown: ${Object.entries(
                    score.breakdown
                  )
                    .map(([k, v]) => `${k}=${(v * 100).toFixed(0)}`)
                    .join(", ")}. Recommendations: ${(score.recommendations || []).join("; ")}.`}
                  prompt="Explain this protein score breakdown in plain language:"
                  title="Explain this score"
                />
              </h2>
              <p>{score.summary}</p>
            </div>
          </div>

          <div className="score-breakdown">
            {Object.entries(score.breakdown).map(([key, val]) => (
              <div key={key} className="score-row">
                <span className="score-name">{key}</span>
                <div className="score-bar">
                  <div
                    className="score-bar-fill"
                    style={{ width: `${val * 100}%` }}
                  />
                </div>
                <span className="score-val">{(val * 100).toFixed(0)}</span>
              </div>
            ))}
          </div>

          <div className="score-recommendations">
            <h3>Recommendations</h3>
            <ul>
              {score.recommendations.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    );
  }

  if (pdbData) {
    return (
      <div className="protein-viewer-3d">
        {designResults && (
          <div className="design-overlay">
            <div className="design-header">
              <h3>Designed Sequences</h3>
              <button className="design-close" onClick={onCloseDesign}>
                ×
              </button>
            </div>
            <p className="design-subtitle">
              {designResults.length} alternative sequences for this backbone, sorted by quality.
            </p>
            <div className="design-list">
              {designResults.map((c) => (
                <div key={c.rank} className="design-item">
                  <div className="design-rank">#{c.rank}</div>
                  <div className="design-info">
                    <div className="design-seq">{c.sequence}</div>
                    <div className="design-meta">
                      Recovery: {(c.recovery * 100).toFixed(0)}% · Score:{" "}
                      {c.score.toFixed(3)}
                    </div>
                  </div>
                  <button
                    className="design-use"
                    onClick={() => onUseCandidate?.(c.sequence)}
                    title="Fold this sequence"
                  >
                    Fold
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
        <div className={`viewer-split ${compareData ? "split" : ""}`}>
          <div className="viewer-pane">
            <div className="viewer-3d-container" ref={containerRef} />
            {stats && (
              <div className="viewer-3d-stats">
                <span>{stats.atoms} atoms</span>
                <span>{stats.residues} residues</span>
              </div>
            )}
          </div>
          {compareData && (
            <div className="viewer-pane">
              <div className="viewer-3d-container" ref={compareRef} />
              <div className="viewer-3d-stats">
                <span>compare</span>
              </div>
            </div>
          )}
        </div>
        <div className="viewer-controls">
          <div className="vc-group">
            <span className="vc-label">Color:</span>
            <button
              className={`vc-btn ${colorMode === "confidence" ? "active" : ""}`}
              onClick={() => setColorMode("confidence")}
            >
              pLDDT
            </button>
            <button
              className={`vc-btn ${colorMode === "chain" ? "active" : ""}`}
              onClick={() => setColorMode("chain")}
            >
              Chain
            </button>
            <ExplainButton
              context={`3D protein structure currently displayed. Coloring: ${colorMode === "confidence" ? "pLDDT confidence" : "per-chain"}. Stats: ${stats?.atoms ?? "?"} atoms, ${stats?.residues ?? "?"} residues. Representation: ${repMode}.`}
              prompt="Explain this structure's confidence/coloring and what it tells us about the model:"
              title="Explain confidence & coloring"
            />
          </div>
          <div className="vc-group">
            <span className="vc-label">Style:</span>
            <button
              className={`vc-btn ${repMode === "cartoon" ? "active" : ""}`}
              onClick={() => setRepMode("cartoon")}
              title="Cartoon"
            >
              Cartoon
            </button>
            <button
              className={`vc-btn ${repMode === "ball-and-stick" ? "active" : ""}`}
              onClick={() => setRepMode("ball-and-stick")}
              title="Ball & Stick"
            >
              Ball+Stick
            </button>
            <button
              className={`vc-btn ${repMode === "spacefill" ? "active" : ""}`}
              onClick={() => setRepMode("spacefill")}
              title="Spacefill"
            >
              Spacefill
            </button>
            <button
              className={`vc-btn ${repMode === "surface" ? "active" : ""}`}
              onClick={() => setRepMode("surface")}
              title="Surface"
            >
              Surface
            </button>
          </div>
          {pdbData && (
            <div className="vc-group">
              <button
                className="vc-btn"
                onClick={runFoldseek}
                title="Search Foldseek for structural neighbors"
              >
                🔎 Foldseek
              </button>
              <button
                className="vc-btn"
                onClick={() => setPresentationOpen(true)}
                title="Open presentation mode"
              >
                🎬 Present
              </button>
            </div>
          )}
        </div>

        {presentationOpen && (
          <PresentationMode
            pdb_string={hasTraj ? trajectoryFrames![frameIdx] : pdbData}
            trajectoryFrames={hasTraj ? trajectoryFrames : undefined}
            onClose={() => setPresentationOpen(false)}
          />
        )}

        {foldseekOpen && (
          <div className="modal-backdrop" onClick={() => setFoldseekOpen(false)}>
            <div
              onClick={(e) => e.stopPropagation()}
              style={{
                background: "var(--panel-bg, #1a1a1a)",
                color: "#e8e8e8",
                padding: 18,
                borderRadius: 10,
                minWidth: 520,
                maxWidth: 720,
                maxHeight: "85vh",
                overflowY: "auto",
                boxShadow: "0 8px 40px rgba(0,0,0,0.5)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <h3 style={{ margin: 0 }}>Foldseek: Structural Neighbors</h3>
                <button className="header-btn small" onClick={() => setFoldseekOpen(false)}>Close</button>
              </div>
              {foldseekBusy && <div style={{ color: "#aaa", padding: "8px 0" }}>Searching Foldseek (this may take up to ~90s)...</div>}
              {foldseekResult?.error && <div style={{ background: "#3a0a0a", color: "#f88", padding: 8, borderRadius: 4 }}>{foldseekResult.error}</div>}
              {foldseekResult && !foldseekResult.error && foldseekResult.hits.length === 0 && !foldseekBusy && (
                <div style={{ color: "#888" }}>No hits returned.</div>
              )}
              {foldseekResult && foldseekResult.hits.length > 0 && (
                <div>
                  <div style={{ fontSize: 12, color: "#888", marginBottom: 8 }}>
                    Top {Math.min(20, foldseekResult.hits.length)} of {foldseekResult.hits.length} hits
                    {foldseekResult.database && ` in ${foldseekResult.database}`}
                  </div>
                  <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ color: "#888", textAlign: "left", borderBottom: "1px solid #333" }}>
                        <th style={{ padding: 4 }}>Target</th>
                        <th style={{ padding: 4 }}>E-value</th>
                        <th style={{ padding: 4 }}>Score</th>
                        <th style={{ padding: 4 }}>Len</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {foldseekResult.hits.slice(0, 20).map((h, i) => (
                        <tr key={i} style={{ borderBottom: "1px solid #222" }}>
                          <td style={{ padding: 4, fontFamily: "monospace" }}>{h.target_id}</td>
                          <td style={{ padding: 4 }}>{h.evalue.toExponential(1)}</td>
                          <td style={{ padding: 4 }}>{h.score.toFixed(1)}</td>
                          <td style={{ padding: 4 }}>{h.length}</td>
                          <td style={{ padding: 4 }}>
                            <button
                              className="vc-btn"
                              style={{ fontSize: 10 }}
                              onClick={() => loadFoldseekHit(h.target_id)}
                            >
                              Load
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {hoverInfo && (() => {
          const oldAA = THREE_TO_ONE[hoverInfo.residue.toUpperCase()] || "X";
          return (
            <div className="residue-popup" style={{ left: hoverInfo.x, top: hoverInfo.y }}>
              <div className="rp-row">
                <strong>{hoverInfo.residue}{hoverInfo.residueNum} ({oldAA})</strong>
                <span className="rp-chain">Chain {hoverInfo.chain}</span>
                <ExplainButton
                  context={`Residue ${hoverInfo.residue}${hoverInfo.residueNum} (${oldAA}) on chain ${hoverInfo.chain} of the currently displayed protein.`}
                  prompt="Explain what this residue typically does (chemistry, common roles in proteins, notable features):"
                  title="Explain this residue"
                />
                <button
                  className="rp-close"
                  onClick={() => setHoverInfo(null)}
                  title="Close"
                >×</button>
              </div>
              {onMutate && oldAA !== "X" && (
                <div className="rp-mutate">
                  <div className="rp-mutate-label">Mutate to...</div>
                  <div className="rp-aa-grid">
                    {AA_LIST.map((aa) => (
                      <button
                        key={aa.code}
                        className={`rp-aa-btn ${aa.code === oldAA ? "current" : ""}`}
                        disabled={aa.code === oldAA}
                        title={`${aa.name} (${aa.code})`}
                        onClick={() => {
                          onMutate(hoverInfo.chain, hoverInfo.residueNum, aa.code, oldAA);
                          setHoverInfo(null);
                        }}
                      >{aa.code}</button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })()}
      </div>
    );
  }

  return (
    <div className="protein-viewer">
      <div className="viewer-empty">
        <div className="empty-icon">&#x1F9EC;</div>
        <h3>No Protein Loaded</h3>
        <p>
          Paste a sequence and click "Score Protein" for instant results, or
          "Predict Structure" to see a 3D fold.
        </p>
      </div>
    </div>
  );
}

export default ProteinViewer;
