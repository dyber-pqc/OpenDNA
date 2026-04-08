"""Visual workflow graph runner (Phase 9).

A workflow is a JSON DAG:
    {
      "nodes": [{"id": "n1", "kind": "fold", "params": {"sequence": "..."}}, ...],
      "edges": [{"source": "n1", "target": "n2", "out_key": "pdb", "in_key": "pdb_string"}],
    }

We do a topological sort, then execute each node, threading outputs of upstream
nodes into downstream nodes via the edge mapping. Each step is recorded in the
provenance graph so the resulting workflow runs are bisectable + diffable.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


_NODE_REGISTRY: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}


def register_node(kind: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
    _NODE_REGISTRY[kind] = fn


def list_node_types() -> List[Dict[str, Any]]:
    return [
        {"kind": "fold",         "category": "structure",  "label": "Fold (ESMFold)",
         "inputs": ["sequence"], "outputs": ["pdb"]},
        {"kind": "design",       "category": "design",     "label": "Design (ESM-IF1)",
         "inputs": ["pdb_string"], "outputs": ["candidates"]},
        {"kind": "evaluate",     "category": "score",      "label": "Evaluate sequence",
         "inputs": ["sequence"], "outputs": ["score"]},
        {"kind": "analyze",      "category": "score",      "label": "Analyze (50 metrics)",
         "inputs": ["sequence", "pdb_string"], "outputs": ["analysis"]},
        {"kind": "dock",         "category": "ligand",     "label": "Dock ligand",
         "inputs": ["pdb_string", "ligand_smiles"], "outputs": ["poses"]},
        {"kind": "md",           "category": "dynamics",   "label": "Quick MD",
         "inputs": ["pdb_string"], "outputs": ["trajectory"]},
        {"kind": "multimer",     "category": "structure",  "label": "Multimer fold",
         "inputs": ["sequences"], "outputs": ["pdb"]},
        {"kind": "fetch_uniprot","category": "io",         "label": "Fetch UniProt",
         "inputs": ["accession"], "outputs": ["sequence"]},
        {"kind": "fetch_pdb",    "category": "io",         "label": "Fetch RCSB PDB",
         "inputs": ["pdb_id"], "outputs": ["pdb"]},
        {"kind": "constant",     "category": "io",         "label": "Constant value",
         "inputs": [], "outputs": ["value"]},
    ]


# ---- node implementations ----

def _fold(params):
    from opendna.engines.folding import fold_sequence
    r = fold_sequence(params["sequence"])
    return {"pdb": getattr(r, "pdb_string", str(r))}


def _design(params):
    from opendna.engines.design import design_sequences
    return {"candidates": design_sequences(params["pdb_string"], num_candidates=int(params.get("num_candidates", 5)))}


def _evaluate(params):
    from opendna.engines.scoring import evaluate
    s = evaluate(params["sequence"])
    if hasattr(s, "__dict__"):
        try:
            from dataclasses import asdict
            return {"score": asdict(s)}
        except Exception:
            return {"score": vars(s)}
    return {"score": s if isinstance(s, dict) else {"value": s}}


def _analyze(params):
    from opendna.engines.analysis import compute_basic_properties
    return {"analysis": compute_basic_properties(params["sequence"])}


def _dock(params):
    from opendna.engines.real_models import diffdock_dock, NotInstalledError
    try:
        return diffdock_dock(params["pdb_string"], params["ligand_smiles"])
    except NotInstalledError:
        from opendna.engines.docking import dock_ligand
        r = dock_ligand(params["pdb_string"], params["ligand_smiles"])
        return {"poses": getattr(r, "poses", []) if hasattr(r, "poses") else r}


def _md(params):
    from opendna.engines.dynamics import quick_md
    r = quick_md(params["pdb_string"], duration_ps=float(params.get("duration_ps", 100)))
    return {"trajectory": str(r)}


def _multimer(params):
    from opendna.engines.multimer import fold_multimer
    r = fold_multimer(params["sequences"])
    return {"pdb": r.pdb_string, "method": r.method}


def _fetch_uniprot(params):
    import urllib.request
    url = f"https://rest.uniprot.org/uniprotkb/{params['accession']}.fasta"
    txt = urllib.request.urlopen(url, timeout=15).read().decode()
    seq = "".join(line for line in txt.splitlines() if not line.startswith(">"))
    return {"sequence": seq}


def _fetch_pdb(params):
    import urllib.request
    url = f"https://files.rcsb.org/download/{params['pdb_id'].upper()}.pdb"
    return {"pdb": urllib.request.urlopen(url, timeout=15).read().decode()}


def _constant(params):
    return {"value": params.get("value")}


for kind, fn in [
    ("fold", _fold), ("design", _design), ("evaluate", _evaluate),
    ("analyze", _analyze), ("dock", _dock), ("md", _md),
    ("multimer", _multimer), ("fetch_uniprot", _fetch_uniprot),
    ("fetch_pdb", _fetch_pdb), ("constant", _constant),
]:
    register_node(kind, fn)


# ---- runner ----

def _topo_sort(nodes: List[Dict], edges: List[Dict]) -> List[str]:
    in_deg: Dict[str, int] = {n["id"]: 0 for n in nodes}
    children: Dict[str, List[str]] = {n["id"]: [] for n in nodes}
    for e in edges:
        in_deg[e["target"]] = in_deg.get(e["target"], 0) + 1
        children.setdefault(e["source"], []).append(e["target"])
    ready = [nid for nid, d in in_deg.items() if d == 0]
    out: List[str] = []
    while ready:
        nid = ready.pop(0)
        out.append(nid)
        for c in children.get(nid, []):
            in_deg[c] -= 1
            if in_deg[c] == 0:
                ready.append(c)
    if len(out) != len(nodes):
        raise ValueError("workflow contains a cycle")
    return out


def run_workflow(
    workflow: Dict[str, Any],
    project_id: Optional[str] = None,
    actor: Optional[str] = None,
    on_progress: Optional[Callable[[str, float, str], None]] = None,
) -> Dict[str, Any]:
    nodes = workflow.get("nodes", [])
    edges = workflow.get("edges", [])
    by_id = {n["id"]: n for n in nodes}
    order = _topo_sort(nodes, edges)
    outputs: Dict[str, Dict[str, Any]] = {}
    prov_node_ids: Dict[str, str] = {}

    n_total = max(1, len(order))
    for i, nid in enumerate(order):
        node = by_id[nid]
        kind = node["kind"]
        fn = _NODE_REGISTRY.get(kind)
        if fn is None:
            raise ValueError(f"unknown node kind: {kind}")
        # Resolve params from edges + static params
        params = dict(node.get("params", {}))
        parent_prov_ids: List[str] = []
        for e in edges:
            if e["target"] == nid:
                upstream = outputs.get(e["source"], {})
                params[e["in_key"]] = upstream.get(e["out_key"])
                if e["source"] in prov_node_ids:
                    parent_prov_ids.append(prov_node_ids[e["source"]])
        if on_progress:
            on_progress(kind, i / n_total, f"Running {nid} ({kind})")
        try:
            result = fn(params)
        except Exception as e:
            outputs[nid] = {"error": str(e)}
            if on_progress:
                on_progress(kind, (i + 1) / n_total, f"FAILED {nid}: {e}")
            continue
        outputs[nid] = result
        # Record provenance step
        if project_id:
            try:
                from opendna.provenance import record_step
                p = record_step(
                    project_id=project_id, kind=kind,
                    inputs=params, outputs=result,
                    parent_ids=parent_prov_ids, actor=actor,
                )
                prov_node_ids[nid] = p.id
            except Exception:
                pass
        if on_progress:
            on_progress(kind, (i + 1) / n_total, f"OK {nid}")
    return {
        "outputs": outputs,
        "order": order,
        "provenance_node_ids": prov_node_ids,
    }
