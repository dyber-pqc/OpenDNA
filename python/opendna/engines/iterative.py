"""Iterative design loop: fold -> design -> fold -> score -> keep best -> repeat.

This is the killer feature: automated protein optimization.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from opendna.engines.design import DesignConstraints, design as design_protein
from opendna.engines.folding import fold as fold_protein
from opendna.engines.scoring import evaluate
from opendna.models.protein import Sequence

logger = logging.getLogger(__name__)


@dataclass
class IterationResult:
    round: int
    sequence: str
    score: float
    confidence: float
    pdb: str
    parent_round: Optional[int]


@dataclass
class IterativeDesignResult:
    initial_sequence: str
    initial_score: float
    final_sequence: str
    final_score: float
    improvement: float
    rounds: list[IterationResult]
    history: list[dict]
    method: str = "iterative"


def iterative_design(
    starting_sequence: str,
    n_rounds: int = 5,
    candidates_per_round: int = 5,
    temperature: float = 0.2,
    on_progress: Optional[Callable[[str, float], None]] = None,
) -> IterativeDesignResult:
    """Run an iterative design loop.

    Each round:
      1. Fold the current best sequence
      2. Design N candidate alternatives via ESM-IF1
      3. Score each candidate
      4. Keep the highest-scoring candidate as the new best
      5. Repeat
    """
    if on_progress:
        on_progress("Starting iterative design", 0.0)

    history = []
    rounds = []

    # Round 0: fold the initial sequence
    if on_progress:
        on_progress("Round 0: folding initial sequence", 0.05)

    initial_fold = fold_protein(starting_sequence)
    initial_score_obj = evaluate(starting_sequence)
    initial_score = initial_score_obj.overall

    current_best = IterationResult(
        round=0,
        sequence=starting_sequence,
        score=initial_score,
        confidence=initial_fold.mean_confidence,
        pdb=initial_fold.pdb_string,
        parent_round=None,
    )
    rounds.append(current_best)
    history.append({
        "round": 0,
        "best_score": initial_score,
        "candidates_evaluated": 1,
        "best_sequence": starting_sequence[:30] + "...",
    })

    for round_num in range(1, n_rounds + 1):
        if on_progress:
            base = 0.05 + 0.9 * (round_num - 1) / n_rounds
            on_progress(
                f"Round {round_num}/{n_rounds}: designing {candidates_per_round} variants",
                base,
            )

        # Design new candidates from the current best structure
        try:
            constraints = DesignConstraints(
                num_candidates=candidates_per_round,
                temperature=temperature,
            )
            design_result = design_protein(current_best.pdb, constraints=constraints)
        except Exception as e:
            logger.warning(f"Design failed at round {round_num}: {e}")
            break

        # Evaluate each candidate
        round_best = current_best
        for i, candidate in enumerate(design_result.candidates):
            seq_str = str(candidate.sequence)
            try:
                cand_score = evaluate(seq_str).overall
            except Exception:
                continue

            if cand_score > round_best.score:
                # Fold to confirm
                if on_progress:
                    on_progress(
                        f"Round {round_num}: candidate {i + 1} promising, folding to verify",
                        base + 0.05,
                    )
                try:
                    cand_fold = fold_protein(seq_str)
                    round_best = IterationResult(
                        round=round_num,
                        sequence=seq_str,
                        score=cand_score,
                        confidence=cand_fold.mean_confidence,
                        pdb=cand_fold.pdb_string,
                        parent_round=current_best.round,
                    )
                except Exception as e:
                    logger.warning(f"Fold failed for candidate: {e}")

        if round_best.score > current_best.score:
            current_best = round_best
            rounds.append(current_best)
            improved = True
        else:
            improved = False

        history.append({
            "round": round_num,
            "best_score": current_best.score,
            "improved": improved,
            "candidates_evaluated": candidates_per_round,
            "best_sequence": current_best.sequence[:30] + "...",
        })

    if on_progress:
        on_progress("Complete", 1.0)

    return IterativeDesignResult(
        initial_sequence=starting_sequence,
        initial_score=initial_score,
        final_sequence=current_best.sequence,
        final_score=current_best.score,
        improvement=current_best.score - initial_score,
        rounds=rounds,
        history=history,
    )
