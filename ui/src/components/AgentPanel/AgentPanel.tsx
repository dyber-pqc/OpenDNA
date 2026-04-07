import { useState, useEffect } from "react";
import * as api from "../../api/client";
import "./AgentPanel.css";

interface AgentPanelProps {
  onClose: () => void;
  onSequenceFound: (seq: string) => void;
}

const PRESET_GOALS = [
  {
    label: "Analyze ubiquitin",
    goal: "Import ubiquitin from UniProt and run a complete analysis. Tell me about its size, charge, stability, and any notable features.",
  },
  {
    label: "Design stable insulin variant",
    goal: "Import insulin from UniProt, then suggest 3 mutations that might improve its stability. Predict the ddG of each.",
  },
  {
    label: "Compare two famous proteins",
    goal: "Compare ubiquitin and lysozyme. What are the key differences in their properties?",
  },
  {
    label: "Find a drug-like peptide",
    goal: "Score the sequence MKTVRQERLK for drug-likeness using Lipinski's rule. Is it a good drug candidate? Why or why not?",
  },
  {
    label: "Detect antibody CDRs",
    goal: "Find the CDRs in this antibody heavy chain: EVQLVESGGGLVQPGGSLRLSCAASGFNIKDTYIHWVRQAPGKGLEWVARIYPTNGYTRYADSVKGRFTISADTSKNTAYLQMNSLRAEDTAVYYCSRWGGDGFYAMDYWGQGTLVTVSS",
  },
  {
    label: "Estimate protein cost",
    goal: "How much would it cost to chemically synthesize the gene for ubiquitin? Use the cheapest vendor.",
  },
];

export default function AgentPanel({ onClose, onSequenceFound }: AgentPanelProps) {
  const [goal, setGoal] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [providers, setProviders] = useState<any[]>([]);

  useEffect(() => {
    api.llmProviders().then((d) => setProviders(d.providers)).catch(() => {});
  }, []);

  const handleRun = async () => {
    if (!goal.trim() || running) return;
    setRunning(true);
    setResult(null);
    try {
      const r = await api.runAgent(goal.trim(), 8);
      setResult(r);
      // If a sequence appeared in any tool result, surface it
      for (const step of r.steps || []) {
        if (step.result?.sequence_preview && !step.result.sequence_preview.includes("...")) {
          onSequenceFound(step.result.sequence_preview);
        }
      }
    } catch (e: any) {
      setResult({ error: e.message });
    } finally {
      setRunning(false);
    }
  };

  const usedProvider = result?.provider || providers[0]?.name || "none";

  return (
    <div className="agent-panel">
      <div className="agent-header">
        <div>
          <h2>OpenDNA Agent</h2>
          <span className="agent-sub">AI-powered protein engineering assistant</span>
        </div>
        <button className="agent-close" onClick={onClose}>×</button>
      </div>

      <div className="agent-providers">
        {providers.map((p) => (
          <span
            key={p.name}
            className={`provider-badge ${p.name === usedProvider ? "active" : ""}`}
            title={
              p.supports_tools === false
                ? `${p.model} does not support tool calling — agent will use plain chat only`
                : ""
            }
          >
            {p.name === "ollama" && "🦙 "}
            {p.name === "anthropic" && "✦ "}
            {p.name === "openai" && "○ "}
            {p.name === "heuristic" && "⚙ "}
            {p.name} {p.model && p.name !== "heuristic" && `(${p.model})`}
            {p.supports_tools === false && " ⚠"}
          </span>
        ))}
      </div>
      {providers.find((p) => p.name === "ollama" && p.supports_tools === false) && (
        <div className="agent-tip">
          ⚠ Your Ollama model does not support tool calling. The agent can still
          chat but cannot execute actions. For full tool support, run:{" "}
          <code>ollama pull llama3.2:3b</code>
        </div>
      )}

      <div className="agent-input-row">
        <input
          className="agent-input"
          placeholder="What do you want to do? e.g. 'Analyze p53 and find its CDRs'"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !running && handleRun()}
        />
        <button className="agent-run" onClick={handleRun} disabled={running || !goal.trim()}>
          {running ? "Thinking..." : "Run"}
        </button>
      </div>

      <div className="agent-presets">
        <span>Try:</span>
        {PRESET_GOALS.map((p, i) => (
          <button key={i} className="preset-btn" onClick={() => setGoal(p.goal)}>
            {p.label}
          </button>
        ))}
      </div>

      <div className="agent-results">
        {!result && !running && (
          <div className="agent-empty">
            Type a goal above and click Run. The agent will plan, execute tools,
            and report back with results.
          </div>
        )}

        {running && (
          <div className="agent-running">
            <div className="agent-spinner"></div>
            <p>Agent is working...</p>
          </div>
        )}

        {result?.error && (
          <div className="agent-error">Error: {result.error}</div>
        )}

        {result?.steps?.length > 0 && (
          <div className="agent-steps">
            <h3>Execution Trace</h3>
            {result.steps.map((step: any, i: number) => (
              <div key={i} className="agent-step">
                <div className="step-num">Step {step.step}</div>
                {step.thought && (
                  <div className="step-thought">{step.thought}</div>
                )}
                {step.tool && (
                  <div className="step-tool">
                    <span className="tool-name">→ {step.tool}</span>
                    <pre className="tool-args">
                      {JSON.stringify(step.arguments, null, 2)}
                    </pre>
                  </div>
                )}
                {step.result && (
                  <div className="step-result">
                    <pre>{JSON.stringify(step.result, null, 2)}</pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {result?.final_answer && (
          <div className="agent-final">
            <h3>Final Answer</h3>
            <div className="final-text">{result.final_answer}</div>
          </div>
        )}
      </div>
    </div>
  );
}
