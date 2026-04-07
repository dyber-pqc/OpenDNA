"""Multi-objective optimization with Pareto fronts (NSGA-II style)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class ParetoCandidate:
    sequence: str
    objectives: dict[str, float]  # name -> value (higher is better)
    rank: int  # 1 = first Pareto front
    crowding: float


def pareto_optimize(
    candidates: list[dict],
    objectives: list[str],
) -> list[ParetoCandidate]:
    """Compute Pareto fronts on a set of candidates with multiple objectives.

    Each candidate is a dict with 'sequence' and the objective values.
    Returns the same candidates ranked by Pareto front membership.
    """
    if not candidates:
        return []

    # Extract objective vectors
    n = len(candidates)
    obj_vecs = []
    for c in candidates:
        obj_vecs.append([c.get(obj, 0.0) for obj in objectives])

    # Compute domination: a dominates b if a >= b in all objectives AND a > b in at least one
    def dominates(a: list[float], b: list[float]) -> bool:
        better_or_equal = all(ai >= bi for ai, bi in zip(a, b))
        strictly_better = any(ai > bi for ai, bi in zip(a, b))
        return better_or_equal and strictly_better

    # Fast non-dominated sort (NSGA-II)
    fronts: list[list[int]] = [[]]
    domination_count = [0] * n
    dominated_by_me = [[] for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if dominates(obj_vecs[i], obj_vecs[j]):
                dominated_by_me[i].append(j)
            elif dominates(obj_vecs[j], obj_vecs[i]):
                domination_count[i] += 1
        if domination_count[i] == 0:
            fronts[0].append(i)

    front_idx = 0
    while fronts[front_idx]:
        next_front = []
        for i in fronts[front_idx]:
            for j in dominated_by_me[i]:
                domination_count[j] -= 1
                if domination_count[j] == 0:
                    next_front.append(j)
        front_idx += 1
        fronts.append(next_front)
    fronts.pop()  # remove the empty trailing list

    # Assign Pareto rank (1-indexed)
    rank_of = [0] * n
    for r, front in enumerate(fronts):
        for i in front:
            rank_of[i] = r + 1

    # Crowding distance per front
    crowding = [0.0] * n
    for front in fronts:
        if len(front) < 3:
            for i in front:
                crowding[i] = float("inf")
            continue
        for k, obj in enumerate(objectives):
            sorted_front = sorted(front, key=lambda i: obj_vecs[i][k])
            crowding[sorted_front[0]] = float("inf")
            crowding[sorted_front[-1]] = float("inf")
            obj_min = obj_vecs[sorted_front[0]][k]
            obj_max = obj_vecs[sorted_front[-1]][k]
            obj_range = obj_max - obj_min
            if obj_range == 0:
                continue
            for j in range(1, len(sorted_front) - 1):
                idx = sorted_front[j]
                next_v = obj_vecs[sorted_front[j + 1]][k]
                prev_v = obj_vecs[sorted_front[j - 1]][k]
                crowding[idx] += (next_v - prev_v) / obj_range

    # Build result
    out = []
    for i, c in enumerate(candidates):
        out.append(ParetoCandidate(
            sequence=c["sequence"],
            objectives={obj: c.get(obj, 0.0) for obj in objectives},
            rank=rank_of[i],
            crowding=round(crowding[i], 3) if crowding[i] != float("inf") else 999.0,
        ))

    out.sort(key=lambda c: (c.rank, -c.crowding))
    return out


def design_multi_objective(
    sequence: str,
    objectives: list[str],
    num_candidates: int = 20,
) -> dict:
    """Design candidates and rank by Pareto fronts on multiple objectives.

    Available objectives: stability, solubility, immunogenicity, developability,
    hydropathy, charge, length.
    """
    from opendna.engines.scoring import evaluate
    from opendna.engines.analysis import compute_properties
    from opendna.engines.design import DesignConstraints, design as design_protein
    from opendna.engines.folding import fold

    # Need a structure to design from
    fold_result = fold(sequence)

    # Generate candidates
    constraints = DesignConstraints(num_candidates=num_candidates, temperature=0.3)
    design_result = design_protein(fold_result.pdb_string, constraints=constraints)

    # Score each candidate on all requested objectives
    scored = []
    for c in design_result.candidates:
        seq_str = str(c.sequence)
        eval_result = evaluate(seq_str)
        props = compute_properties(seq_str)

        objective_values = {}
        for obj in objectives:
            if obj == "stability":
                objective_values[obj] = eval_result.breakdown.stability
            elif obj == "solubility":
                objective_values[obj] = eval_result.breakdown.solubility
            elif obj == "immunogenicity":
                objective_values[obj] = eval_result.breakdown.immunogenicity
            elif obj == "developability":
                objective_values[obj] = eval_result.breakdown.developability
            elif obj == "hydropathy":
                # Want negative GRAVY (more soluble = "better")
                objective_values[obj] = -props.gravy
            elif obj == "charge":
                # Higher absolute charge for some applications
                objective_values[obj] = abs(props.charge_at_ph7)
            else:
                objective_values[obj] = 0.0

        scored.append({"sequence": seq_str, **objective_values})

    pareto = pareto_optimize(scored, objectives)

    return {
        "objectives": objectives,
        "candidates": [
            {
                "sequence": p.sequence,
                "objectives": p.objectives,
                "pareto_rank": p.rank,
                "crowding": p.crowding,
            }
            for p in pareto
        ],
        "n_pareto_optimal": sum(1 for p in pareto if p.rank == 1),
        "method": "nsga-ii-style",
    }
