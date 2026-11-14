"""Auto paper-writer.

Walks a project's provenance DAG and composes a markdown draft of a research
paper (methods, abstract, or full scaffold). Methods draft is deterministic;
abstract uses the local Ollama provider when available, otherwise falls back
to a templated abstract.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

_TOOL_CITATIONS: Dict[str, str] = {
    "esmfold": "ESMFold (Lin et al., 2023)",
    "fold": "ESMFold (Lin et al., 2023)",
    "alphafold": "AlphaFold2 (Jumper et al., 2021)",
    "esm-if1": "ESM-IF1 (Hsu et al., 2022)",
    "design": "ESM-IF1 inverse folding (Hsu et al., 2022)",
    "openmm": "OpenMM (Eastman et al., 2017)",
    "md": "OpenMM MD (Eastman et al., 2017)",
    "rosetta": "Rosetta (Leaver-Fay et al., 2011)",
    "dssp": "DSSP (Kabsch & Sander, 1983)",
    "pymol": "PyMOL (Schrodinger LLC)",
    "mmgbsa": "MM-GBSA (Genheden & Ryde, 2015)",
    "smina": "smina/AutoDock Vina (Trott & Olson, 2010)",
}

_OPENDNA_VERSION = "OpenDNA v0.5.0"


def _collect_project_info(project_id: str) -> Dict[str, Any]:
    """Pull tools and final scores from the provenance store if available."""
    info: Dict[str, Any] = {
        "project_id": project_id,
        "tools": [],
        "nodes": [],
        "final_scores": {},
    }
    try:
        from opendna.provenance.graph import get_provenance_store

        store = get_provenance_store()
        nodes = store.project_nodes(project_id)
        seen: List[str] = []
        for n in nodes:
            try:
                d = n.to_dict() if hasattr(n, "to_dict") else dict(n.__dict__)
            except Exception:
                d = {"kind": getattr(n, "kind", "unknown")}
            info["nodes"].append(d)
            kind = (d.get("kind") or "").lower()
            if kind and kind not in seen:
                seen.append(kind)
            outs = d.get("outputs") or {}
            if isinstance(outs, dict):
                for k, v in outs.items():
                    if isinstance(v, (int, float)) and "score" in k.lower():
                        info["final_scores"][k] = v
        info["tools"] = seen
    except Exception:
        # Provenance store unavailable or empty — return empty scaffold.
        pass
    return info


def _cite(tool_kind: str) -> str:
    key = (tool_kind or "").lower()
    for k, v in _TOOL_CITATIONS.items():
        if k in key:
            return v
    return f"{tool_kind} (OpenDNA v0.5.0)"


def draft_methods_section(project_id: str) -> str:
    """Return a markdown-formatted Methods section for the project."""
    info = _collect_project_info(project_id)
    tools: List[str] = info.get("tools", [])
    lines: List[str] = ["## Methods", ""]
    if not tools:
        lines.append(
            "No recorded pipeline steps were found for this project. "
            "All computations were performed using default settings in "
            f"{_OPENDNA_VERSION}."
        )
        return "\n".join(lines)

    sentences: List[str] = []
    for t in tools:
        citation = _cite(t)
        if "fold" in t:
            sentences.append(
                f"Sequences were folded with {citation} using {_OPENDNA_VERSION} "
                "with default chunking and half-precision weights on CPU."
            )
        elif "design" in t or "if1" in t:
            sentences.append(
                f"Alternative sequences were designed by inverse folding "
                f"with {citation} as integrated in {_OPENDNA_VERSION}."
            )
        elif "md" in t or "openmm" in t:
            sentences.append(
                f"Molecular dynamics was performed with {citation}; "
                "short equilibration runs were used as a fast stability proxy."
            )
        elif "mmgbsa" in t:
            sentences.append(
                f"Binding free energies were estimated with {citation}."
            )
        elif "dock" in t or "smina" in t:
            sentences.append(
                f"Docking was carried out with {citation}."
            )
        else:
            sentences.append(
                f"The {t} step used {citation} via {_OPENDNA_VERSION}."
            )
    lines.extend(sentences)
    lines.append("")
    lines.append(
        "All analyses were reproducible from provenance records stored by "
        f"{_OPENDNA_VERSION}."
    )
    return "\n".join(lines)


def _fallback_abstract(project_id: str, research_question: str, info: Dict[str, Any]) -> str:
    n = len(info.get("nodes", []))
    scores = info.get("final_scores", {})
    score_txt = ""
    if scores:
        score_txt = " Final scores: " + ", ".join(
            f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}" for k, v in scores.items()
        ) + "."
    return (
        f"**Abstract.** We investigated: {research_question}. "
        f"Using {_OPENDNA_VERSION}, we ran {n} recorded pipeline steps combining "
        "folding, scoring, and design modules. Our results illustrate how an "
        "end-to-end in-browser protein-engineering workflow can address the "
        f"question above.{score_txt}"
    )


def draft_abstract(project_id: str, research_question: str) -> str:
    """Generate an abstract using Ollama streaming if available."""
    info = _collect_project_info(project_id)
    try:
        from opendna.llm.providers import get_provider  # type: ignore

        provider = get_provider("ollama")
        prompt = (
            "Write a concise ~180-word scientific paper abstract in markdown. "
            f"Research question: {research_question}. "
            f"Project id: {project_id}. "
            f"Tools used: {', '.join(info.get('tools', [])) or 'unspecified'}. "
            f"Final scores: {info.get('final_scores', {})}. "
            "Do not invent experimental results not implied by the inputs."
        )
        chunks: List[str] = []
        try:
            for tok in provider.stream(prompt):  # type: ignore[attr-defined]
                chunks.append(tok)
        except AttributeError:
            # Providers without stream: try a plain call.
            chunks.append(provider.complete(prompt))  # type: ignore[attr-defined]
        text = "".join(chunks).strip()
        if text:
            return text
    except Exception:
        pass
    return _fallback_abstract(project_id, research_question, info)


def draft_full_paper(
    project_id: str,
    title: str,
    research_question: str,
    author_names: List[str],
) -> str:
    """Assemble methods + abstract + intro + results table + discussion prompts."""
    info = _collect_project_info(project_id)
    methods = draft_methods_section(project_id)
    abstract = draft_abstract(project_id, research_question)
    authors = ", ".join(author_names) if author_names else "Anonymous"

    # Results table from provenance nodes with any numeric output.
    rows: List[str] = ["| Step | Metric | Value |", "| --- | --- | --- |"]
    for n in info.get("nodes", []):
        kind = n.get("kind", "")
        outs = n.get("outputs") or {}
        if isinstance(outs, dict):
            for k, v in outs.items():
                if isinstance(v, (int, float)):
                    rows.append(f"| {kind} | {k} | {v} |")
    if len(rows) == 2:
        rows.append("| (no numeric outputs recorded) | — | — |")

    parts: List[str] = [
        f"# {title}",
        "",
        f"*{authors}*",
        "",
        abstract,
        "",
        "## Introduction",
        "",
        f"The central question of this study is: **{research_question}** "
        f"We approach it using {_OPENDNA_VERSION}, an open-source, in-browser "
        "protein engineering platform. This section should be expanded with "
        "background literature, the gap in the state-of-the-art, and the "
        "hypothesis being tested.",
        "",
        methods,
        "",
        "## Results",
        "",
        "\n".join(rows),
        "",
        "## Discussion",
        "",
        "- How do these scores compare to baselines or wild-type references?",
        "- What are the limitations of the in silico models used above?",
        "- What wet-lab experiment would most decisively test the main claim?",
        "- How generalizable is the approach to adjacent protein families?",
        "",
        "## Data availability",
        "",
        f"All pipeline steps are recorded in the OpenDNA provenance DAG under "
        f"project id `{project_id}` and can be replayed with `opendna provenance replay`.",
        "",
    ]
    return "\n".join(parts)
