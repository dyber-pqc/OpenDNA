"""Time machine, diff/blame/bisect on the provenance DAG."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .graph import Node, get_provenance_store


@dataclass
class TimeMachine:
    project_id: str

    def at(self, ts: float) -> List[Node]:
        """Return all nodes at-or-before timestamp `ts`."""
        store = get_provenance_store()
        return [n for n in store.project_nodes(self.project_id) if n.ts <= ts]

    def latest(self, kind: Optional[str] = None) -> Optional[Node]:
        store = get_provenance_store()
        nodes = store.project_nodes(self.project_id)
        if kind:
            nodes = [n for n in nodes if n.kind == kind]
        return nodes[-1] if nodes else None

    def history(self, kind: Optional[str] = None) -> List[Node]:
        store = get_provenance_store()
        nodes = store.project_nodes(self.project_id)
        if kind:
            nodes = [n for n in nodes if n.kind == kind]
        return nodes


def diff_steps(node_a_id: str, node_b_id: str) -> Dict[str, Any]:
    """Diff two provenance nodes — outputs and per-residue if possible."""
    store = get_provenance_store()
    a = store.get(node_a_id)
    b = store.get(node_b_id)
    if a is None or b is None:
        return {"error": "node not found"}
    out: Dict[str, Any] = {
        "a": {"id": a.id, "kind": a.kind, "score": a.score, "ts": a.ts},
        "b": {"id": b.id, "kind": b.kind, "score": b.score, "ts": b.ts},
        "delta_score": (b.score or 0.0) - (a.score or 0.0) if a.score is not None and b.score is not None else None,
    }
    seq_a = a.outputs.get("sequence")
    seq_b = b.outputs.get("sequence")
    if isinstance(seq_a, str) and isinstance(seq_b, str):
        muts: List[Dict[str, Any]] = []
        L = min(len(seq_a), len(seq_b))
        for i in range(L):
            if seq_a[i] != seq_b[i]:
                muts.append({"pos": i + 1, "from": seq_a[i], "to": seq_b[i]})
        if len(seq_a) != len(seq_b):
            out["length_change"] = len(seq_b) - len(seq_a)
        out["mutations"] = muts
    pdb_a = a.outputs.get("pdb")
    pdb_b = b.outputs.get("pdb")
    if isinstance(pdb_a, str) and isinstance(pdb_b, str):
        out["pdb_size_delta"] = len(pdb_b) - len(pdb_a)
    return out


def blame_residue(project_id: str, residue_position: int) -> List[Dict[str, Any]]:
    """Walk history of `project_id`, return every step that mutated `residue_position`."""
    store = get_provenance_store()
    nodes = store.project_nodes(project_id)
    history: List[Dict[str, Any]] = []
    prev_seq: Optional[str] = None
    for n in nodes:
        seq = n.outputs.get("sequence")
        if not isinstance(seq, str):
            continue
        if prev_seq is None:
            history.append({
                "node": n.id, "ts": n.ts, "kind": n.kind,
                "residue": seq[residue_position - 1] if residue_position - 1 < len(seq) else "?",
                "event": "introduced",
            })
        else:
            if (residue_position - 1 < len(seq) and residue_position - 1 < len(prev_seq)
                    and prev_seq[residue_position - 1] != seq[residue_position - 1]):
                history.append({
                    "node": n.id, "ts": n.ts, "kind": n.kind,
                    "residue": seq[residue_position - 1],
                    "from": prev_seq[residue_position - 1],
                    "event": "mutation",
                    "score": n.score, "actor": n.actor,
                })
        prev_seq = seq
    return history


def bisect_regression(
    project_id: str,
    metric_key: str = "score",
    threshold: float = 0.0,
) -> Optional[Dict[str, Any]]:
    """Find the first node where `score` dropped below `threshold` (or below the
    previous best score, if threshold==0)."""
    store = get_provenance_store()
    nodes = [n for n in store.project_nodes(project_id) if n.score is not None]
    if not nodes:
        return None
    best = nodes[0].score or 0.0
    for n in nodes[1:]:
        s = n.score or 0.0
        if threshold > 0:
            if s < threshold:
                return {
                    "regression_node": n.id,
                    "ts": n.ts,
                    "score": s,
                    "threshold": threshold,
                    "kind": n.kind,
                    "parent_ids": n.parent_ids,
                }
        else:
            if s < best - 0.01:
                return {
                    "regression_node": n.id,
                    "ts": n.ts,
                    "score": s,
                    "previous_best": best,
                    "kind": n.kind,
                    "parent_ids": n.parent_ids,
                }
            best = max(best, s)
    return None
