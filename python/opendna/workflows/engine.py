"""YAML workflow engine.

A workflow is a YAML file that defines a sequence of steps. Each step has a
name, an action (corresponding to an OpenDNA function), and input parameters.
Outputs from earlier steps can be referenced via ${step_name.field}.

Example workflow:

```yaml
name: cancer_binder_pipeline
description: Design and validate a binder against KRAS G12D
inputs:
  target_uniprot: P01116

steps:
  - name: load_target
    action: fetch_uniprot
    accession: ${inputs.target_uniprot}

  - name: fold_target
    action: fold
    sequence: ${load_target.sequence}

  - name: analyze_target
    action: analyze
    sequence: ${load_target.sequence}
    pdb_string: ${fold_target.pdb}

  - name: design_binders
    action: design
    pdb_string: ${fold_target.pdb}
    num_candidates: 20
    temperature: 0.2

outputs:
  best_candidate: ${design_binders.candidates[0].sequence}
  target_pi: ${analyze_target.properties.isoelectric_point}
```
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class WorkflowStep:
    name: str
    action: str
    params: dict
    output: Any = None


@dataclass
class WorkflowResult:
    name: str
    description: str
    inputs: dict
    steps: list[WorkflowStep] = field(default_factory=list)
    outputs: dict = field(default_factory=dict)
    success: bool = False
    error: str = ""


VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


def parse_workflow(path: str | Path) -> dict:
    """Parse a workflow YAML file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Workflow file not found: {path}")
    return yaml.safe_load(p.read_text())


def _resolve_value(value: Any, context: dict) -> Any:
    """Resolve ${var.path} references in a value against the context."""
    if isinstance(value, str):
        def resolve_match(m):
            path = m.group(1)
            return str(_get_path(context, path))
        # If the entire string is just one variable, return the resolved object
        match = VAR_PATTERN.fullmatch(value)
        if match:
            return _get_path(context, match.group(1))
        return VAR_PATTERN.sub(resolve_match, value)
    elif isinstance(value, dict):
        return {k: _resolve_value(v, context) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_value(v, context) for v in value]
    return value


def _get_path(context: dict, path: str) -> Any:
    """Walk a dot-path like 'design_binders.candidates[0].sequence' through context."""
    parts = re.findall(r"[^.\[\]]+", path)
    current = context
    for part in parts:
        if part.isdigit():
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current.get(part, "")
        else:
            current = getattr(current, part, "")
    return current


def run_workflow(path: str | Path) -> WorkflowResult:
    """Execute a YAML workflow.

    Returns a WorkflowResult with all step outputs and resolved final outputs.
    """
    spec = parse_workflow(path)

    result = WorkflowResult(
        name=spec.get("name", "untitled"),
        description=spec.get("description", ""),
        inputs=spec.get("inputs", {}),
    )

    context = {"inputs": result.inputs}

    try:
        for step_spec in spec.get("steps", []):
            name = step_spec.get("name", f"step_{len(result.steps)}")
            action = step_spec.get("action")
            if not action:
                raise ValueError(f"Step '{name}' has no action")

            # Resolve all parameters
            params = {k: _resolve_value(v, context) for k, v in step_spec.items() if k not in ("name", "action")}

            # Execute the action
            output = _execute_action(action, params)

            step = WorkflowStep(name=name, action=action, params=params, output=output)
            result.steps.append(step)
            context[name] = output

        # Resolve final outputs
        for k, v in spec.get("outputs", {}).items():
            result.outputs[k] = _resolve_value(v, context)

        result.success = True
    except Exception as e:
        result.error = str(e)
        result.success = False

    return result


def _execute_action(action: str, params: dict) -> Any:
    """Dispatch an action name to the corresponding OpenDNA function."""
    if action == "fetch_uniprot":
        from opendna.data.sources import fetch_uniprot, FAMOUS_PROTEINS
        accession = params["accession"]
        if accession.lower() in FAMOUS_PROTEINS:
            accession = FAMOUS_PROTEINS[accession.lower()]
        entry = fetch_uniprot(accession)
        return {
            "accession": entry.accession,
            "name": entry.name,
            "sequence": entry.sequence,
            "organism": entry.organism,
            "length": entry.length,
        }

    elif action == "fetch_pdb":
        from opendna.data.sources import fetch_pdb
        return {"pdb": fetch_pdb(params["pdb_id"])}

    elif action == "fold":
        from opendna.engines.folding import fold
        r = fold(params["sequence"])
        return {
            "pdb": r.pdb_string,
            "mean_confidence": r.mean_confidence,
            "method": r.method,
        }

    elif action == "evaluate":
        from opendna.engines.scoring import evaluate
        r = evaluate(params["sequence"])
        return {
            "overall": r.overall,
            "summary": r.summary,
            "stability": r.breakdown.stability,
            "solubility": r.breakdown.solubility,
        }

    elif action == "analyze":
        from opendna.engines.analysis import compute_properties
        from opendna.engines.disorder import predict_disorder
        seq = params["sequence"]
        props = compute_properties(seq)
        dis = predict_disorder(seq)
        return {
            "properties": {
                "molecular_weight": props.molecular_weight,
                "isoelectric_point": props.isoelectric_point,
                "gravy": props.gravy,
                "stability": props.classification,
            },
            "disorder_pct": dis["disorder_percent"],
        }

    elif action == "design":
        from opendna.engines.design import DesignConstraints, design
        constraints = DesignConstraints(
            num_candidates=params.get("num_candidates", 10),
            temperature=params.get("temperature", 0.1),
        )
        r = design(params["pdb_string"], constraints=constraints)
        return {
            "candidates": [
                {"rank": c.rank, "sequence": str(c.sequence), "score": c.score, "recovery": c.recovery}
                for c in r.candidates
            ],
            "method": r.method,
        }

    elif action == "mutate":
        from opendna.engines.design import apply_mutation
        return {"mutated": apply_mutation(params["sequence"], params["mutation"])}

    elif action == "predict_ddg":
        from opendna.engines.predictors import predict_ddg
        return predict_ddg(params["sequence"], params["mutation"])

    elif action == "iterative_design":
        from opendna.engines.iterative import iterative_design
        r = iterative_design(
            params["sequence"],
            n_rounds=params.get("n_rounds", 3),
            candidates_per_round=params.get("candidates_per_round", 5),
        )
        return {
            "final_sequence": r.final_sequence,
            "improvement": r.improvement,
            "history": r.history,
        }

    else:
        raise ValueError(f"Unknown workflow action: {action}")
