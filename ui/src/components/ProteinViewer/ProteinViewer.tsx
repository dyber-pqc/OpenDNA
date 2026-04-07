import { useEffect, useRef, useState } from "react";
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
}

function ProteinViewer({
  pdbData,
  compareData,
  score,
  designResults,
  onUseCandidate,
  onCloseDesign,
}: ProteinViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const compareRef = useRef<HTMLDivElement>(null);
  const pluginRef = useRef<any>(null);
  const comparePluginRef = useRef<any>(null);
  const [stats, setStats] = useState<{ atoms: number; residues: number } | null>(null);
  const [colorMode, setColorMode] = useState<"chain" | "confidence">("confidence");
  const [repMode, setRepMode] = useState<"cartoon" | "ball-and-stick" | "spacefill" | "surface">("cartoon");
  const [hoverInfo, _setHoverInfo] = useState<{
    residue: string;
    residueNum: number;
    chain: string;
    x: number;
    y: number;
  } | null>(null);

  useEffect(() => {
    if (!pdbData || !containerRef.current) return;
    let cancelled = false;

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
        let pdbForViewer = pdbData;
        if (colorMode === "confidence") {
          pdbForViewer = pdbData
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

        // Map our repMode to the appropriate Molstar preset
        const presetMap: Record<string, string> = {
          "cartoon": "default",
          "ball-and-stick": "atomic-detail",
          "spacefill": "atomic-detail",
          "surface": "default",
        };
        const presetName = presetMap[repMode] || "default";

        try {
          await plugin.builders.structure.hierarchy.applyPreset(traj, presetName as any);
        } catch {
          await plugin.builders.structure.hierarchy.applyPreset(traj, "default");
        }

        // Add additional representations on top for surface/spacefill modes
        if (repMode === "surface" || repMode === "spacefill") {
          try {
            const struct = plugin.managers.structure.hierarchy.current.structures[0];
            if (struct?.components && struct.components.length > 0) {
              const reprType = repMode === "surface" ? "molecular-surface" : "spacefill";
              const builder = plugin.builders.structure.representation;
              for (const comp of struct.components) {
                await (builder as any).addRepresentation(comp.cell, {
                  type: reprType,
                  color: colorMode === "confidence" ? "plddt-confidence" : "chain-id",
                });
              }
            }
          } catch (e) {
            console.warn("Could not add representation:", e);
          }
        }

        // Apply color theme: AlphaFold-style pLDDT or chain-id
        const themeName = colorMode === "confidence" ? "plddt-confidence" : "chain-id";
        try {
          const struct = plugin.managers.structure.hierarchy.current.structures[0];
          if (struct?.components) {
            for (const comp of struct.components) {
              await plugin.managers.structure.component.updateRepresentationsTheme(
                [comp],
                { color: themeName as any }
              );
            }
          }
        } catch (e) {
          // Fallback to uncertainty (b-factor based) if plddt theme fails
          try {
            const struct = plugin.managers.structure.hierarchy.current.structures[0];
            if (struct?.components) {
              for (const comp of struct.components) {
                await plugin.managers.structure.component.updateRepresentationsTheme(
                  [comp],
                  { color: "uncertainty" as any }
                );
              }
            }
          } catch (e2) {
            console.warn("Color theme failed:", e, e2);
          }
        }

        // Stats
        const lines = pdbData.split("\n");
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
        pluginRef.current.dispose();
        pluginRef.current = null;
      }
    };
  }, [pdbData, colorMode, repMode]);

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
              <h2>Protein Evaluation</h2>
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
        </div>

        {hoverInfo && (
          <div className="residue-popup" style={{ left: hoverInfo.x, top: hoverInfo.y }}>
            <div className="rp-row">
              <strong>{hoverInfo.residue}{hoverInfo.residueNum}</strong>
              <span className="rp-chain">Chain {hoverInfo.chain}</span>
            </div>
          </div>
        )}
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
