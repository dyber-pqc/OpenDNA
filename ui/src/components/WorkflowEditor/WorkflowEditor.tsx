import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ReactFlow, Background, Controls, MiniMap,
  addEdge, useNodesState, useEdgesState,
  type Node, type Edge, type Connection,
} from "@xyflow/react";
import yaml from "js-yaml";
import "@xyflow/react/dist/style.css";
import "./WorkflowEditor.css";

interface TemplateNode { kind: string; label: string; params?: any; }
interface Template { name: string; description: string; chain: TemplateNode[]; }

const TEMPLATES: Template[] = [
  {
    name: "Fold and score",
    description: "Fetch a UniProt entry, fold with ESMFold, then score.",
    chain: [
      { kind: "fetch_uniprot", label: "Fetch UniProt" },
      { kind: "fold", label: "Fold" },
      { kind: "evaluate", label: "Evaluate" },
    ],
  },
  {
    name: "Design variants",
    description: "Fetch, fold, design alternative sequences, then evaluate.",
    chain: [
      { kind: "fetch_uniprot", label: "Fetch UniProt" },
      { kind: "fold", label: "Fold" },
      { kind: "design", label: "Design" },
      { kind: "evaluate", label: "Evaluate" },
    ],
  },
  {
    name: "Dock a ligand",
    description: "Fetch a PDB structure and run a docking pass.",
    chain: [
      { kind: "fetch_pdb", label: "Fetch PDB" },
      { kind: "dock", label: "Dock" },
    ],
  },
  {
    name: "MD stability check",
    description: "Fetch, fold, then run a quick molecular-dynamics check.",
    chain: [
      { kind: "fetch_uniprot", label: "Fetch UniProt" },
      { kind: "fold", label: "Fold" },
      { kind: "md", label: "MD" },
    ],
  },
  {
    name: "Multimer fold",
    description: "Provide constant sequences and fold as a multimer.",
    chain: [
      { kind: "constant", label: "Constant (sequences)", params: { value: ["SEQ1", "SEQ2"] } },
      { kind: "multimer", label: "Multimer fold" },
    ],
  },
];

interface NodeType {
  kind: string;
  category: string;
  label: string;
  inputs: string[];
  outputs: string[];
}

interface Props {
  onClose?: () => void;
}

const API_BASE = "http://localhost:8765";

export default function WorkflowEditor({ onClose }: Props) {
  const [nodeTypes, setNodeTypes] = useState<NodeType[]>([]);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [jobLog, setJobLog] = useState<string[]>([]);
  const [templatesOpen, setTemplatesOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const applyTemplate = useCallback((tpl: Template) => {
    const newNodes: Node[] = tpl.chain.map((n, i) => ({
      id: `${n.kind}-${i}-${Date.now().toString(36)}`,
      type: "default",
      position: { x: 80 + i * 220, y: 120 + (i % 2) * 60 },
      data: { label: `${n.label}\n(${n.kind})`, kind: n.kind, params: n.params || {} },
      style: { padding: 8, fontSize: 12 },
    }));
    const newEdges: Edge[] = [];
    for (let i = 0; i < newNodes.length - 1; i++) {
      newEdges.push({
        id: `e-${newNodes[i].id}-${newNodes[i + 1].id}`,
        source: newNodes[i].id,
        target: newNodes[i + 1].id,
        label: "→",
      });
    }
    setNodes(newNodes);
    setEdges(newEdges);
    setResults(null);
    setJobLog([]);
    setTemplatesOpen(false);
  }, [setNodes, setEdges]);

  const saveYaml = useCallback(() => {
    const wfNodes = nodes.map(n => ({
      id: n.id,
      kind: (n.data as any).kind,
      params: (n.data as any).params || {},
    }));
    const wfEdges = edges.map(e => {
      const src = nodes.find(x => x.id === e.source);
      const dst = nodes.find(x => x.id === e.target);
      const srcType = nodeTypes.find(t => t.kind === (src?.data as any)?.kind);
      const dstType = nodeTypes.find(t => t.kind === (dst?.data as any)?.kind);
      return {
        source: e.source,
        target: e.target,
        out_key: srcType?.outputs?.[0] || "value",
        in_key: dstType?.inputs?.[0] || "value",
      };
    });
    const text = yaml.dump({ nodes: wfNodes, edges: wfEdges });
    const blob = new Blob([text], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `workflow-${Date.now()}.yaml`;
    a.click();
    URL.revokeObjectURL(url);
  }, [nodes, edges, nodeTypes]);

  const loadYaml = useCallback((file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = yaml.load(String(reader.result)) as any;
        if (!parsed || !Array.isArray(parsed.nodes)) {
          alert("Invalid YAML: missing nodes array");
          return;
        }
        const newNodes: Node[] = parsed.nodes.map((n: any, i: number) => ({
          id: n.id || `${n.kind}-${i}`,
          type: "default",
          position: { x: 80 + i * 220, y: 120 + (i % 2) * 60 },
          data: { label: `${n.kind}\n(${n.kind})`, kind: n.kind, params: n.params || {} },
          style: { padding: 8, fontSize: 12 },
        }));
        const newEdges: Edge[] = (parsed.edges || []).map((e: any, i: number) => ({
          id: `e-${i}-${e.source}-${e.target}`,
          source: e.source,
          target: e.target,
          label: "→",
        }));
        setNodes(newNodes);
        setEdges(newEdges);
        setResults(null);
        setJobLog([]);
      } catch (err: any) {
        alert(`Failed to parse YAML: ${err.message}`);
      }
    };
    reader.readAsText(file);
  }, [setNodes, setEdges]);

  useEffect(() => {
    fetch(`${API_BASE}/v1/workflow/node_types`)
      .then(r => r.json())
      .then(d => setNodeTypes(d.node_types))
      .catch(() => {});
  }, []);

  const addNodeOfKind = useCallback((kind: string, label: string) => {
    const id = `${kind}-${Date.now().toString(36)}`;
    setNodes((nds) => nds.concat({
      id,
      type: "default",
      position: { x: 80 + Math.random() * 400, y: 80 + Math.random() * 300 },
      data: { label: `${label}\n(${kind})`, kind, params: {} },
      style: { padding: 8, fontSize: 12 },
    }));
  }, [setNodes]);

  const onConnect = useCallback((params: Connection) => {
    setEdges((eds) => addEdge({ ...params, label: "→" } as Edge, eds));
  }, [setEdges]);

  const runWorkflow = useCallback(async () => {
    setRunning(true);
    setJobLog([]);
    setResults(null);
    const wfNodes = nodes.map(n => ({
      id: n.id,
      kind: (n.data as any).kind,
      params: (n.data as any).params || {},
    }));
    const wfEdges = edges.map(e => {
      // Find out_key / in_key by asking sourceNode kind's outputs[0] and targetNode inputs[0]
      const src = nodes.find(x => x.id === e.source);
      const dst = nodes.find(x => x.id === e.target);
      const srcType = nodeTypes.find(t => t.kind === (src?.data as any)?.kind);
      const dstType = nodeTypes.find(t => t.kind === (dst?.data as any)?.kind);
      return {
        source: e.source, target: e.target,
        out_key: srcType?.outputs?.[0] || "value",
        in_key: dstType?.inputs?.[0] || "value",
      };
    });
    try {
      const resp = await fetch(`${API_BASE}/v1/workflow/run_graph`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workflow: { nodes: wfNodes, edges: wfEdges } }),
      });
      const { job_id } = await resp.json();
      // Stream via WS
      const ws = new WebSocket(`${API_BASE.replace("http", "ws")}/v1/ws/jobs/${job_id}`);
      ws.onmessage = (m) => {
        try {
          const evt = JSON.parse(m.data);
          if (evt.event === "progress") {
            setJobLog(l => [...l, `${evt.stage}: ${evt.message || ""}`]);
          } else if (evt.event === "finished" || evt.event === "final") {
            setResults(evt.job.result);
            setRunning(false);
            ws.close();
          }
        } catch { /* swallow */ }
      };
      ws.onerror = () => setRunning(false);
    } catch (e: any) {
      setJobLog(l => [...l, `ERROR: ${e.message}`]);
      setRunning(false);
    }
  }, [nodes, edges, nodeTypes]);

  const byCategory = useMemo(() => {
    const m: Record<string, NodeType[]> = {};
    for (const t of nodeTypes) (m[t.category] ||= []).push(t);
    return m;
  }, [nodeTypes]);

  return (
    <div className="wf-editor">
      <div className="wf-header">
        <h2>Visual Workflow Editor</h2>
        <div className="wf-actions">
          <button disabled={running || nodes.length === 0} onClick={runWorkflow}>
            {running ? "Running…" : "▶ Run workflow"}
          </button>
          <button onClick={() => { setNodes([]); setEdges([]); setResults(null); setJobLog([]); }}>
            Clear
          </button>
          <button onClick={() => setTemplatesOpen(true)} title="Built-in workflow templates">
            📋 Templates
          </button>
          <button onClick={saveYaml} disabled={nodes.length === 0} title="Download workflow as YAML">
            ⬇ Save YAML
          </button>
          <button onClick={() => fileInputRef.current?.click()} title="Load workflow from YAML file">
            ⬆ Load YAML
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".yaml,.yml,text/yaml"
            style={{ display: "none" }}
            onChange={e => {
              const f = e.target.files?.[0];
              if (f) loadYaml(f);
              e.target.value = "";
            }}
          />
          {onClose && <button onClick={onClose}>✕</button>}
        </div>
      </div>
      {templatesOpen && (
        <div className="wf-templates-backdrop" onClick={() => setTemplatesOpen(false)}>
          <div className="wf-templates-dialog" onClick={e => e.stopPropagation()}>
            <div className="wf-templates-head">
              <h3>Workflow templates</h3>
              <button onClick={() => setTemplatesOpen(false)}>✕</button>
            </div>
            <div className="wf-templates-list">
              {TEMPLATES.map(tpl => (
                <button key={tpl.name} className="wf-template-card" onClick={() => applyTemplate(tpl)}>
                  <div className="wf-template-name">{tpl.name}</div>
                  <div className="wf-template-desc">{tpl.description}</div>
                  <div className="wf-template-chain">
                    {tpl.chain.map((n, i) => (
                      <span key={i}>
                        {i > 0 && " → "}
                        <code>{n.kind}</code>
                      </span>
                    ))}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
      <div className="wf-body">
        <aside className="wf-palette">
          <h3>Nodes</h3>
          {Object.entries(byCategory).map(([cat, items]) => (
            <div key={cat} className="wf-pal-group">
              <div className="wf-pal-label">{cat}</div>
              {items.map(t => (
                <button key={t.kind} className="wf-pal-item" onClick={() => addNodeOfKind(t.kind, t.label)}>
                  + {t.label}
                </button>
              ))}
            </div>
          ))}
        </aside>
        <div className="wf-canvas">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            fitView
          >
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </div>
        <aside className="wf-sidebar">
          <h3>Run log</h3>
          <div className="wf-log">
            {jobLog.length === 0 ? <em>(not run yet)</em> : jobLog.map((l, i) => <div key={i}>{l}</div>)}
          </div>
          {results && (
            <>
              <h3>Results</h3>
              <pre className="wf-results">{JSON.stringify(results, null, 2).slice(0, 4000)}</pre>
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
