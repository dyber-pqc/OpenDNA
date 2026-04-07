"""Constrained protein design - keep some residues fixed while redesigning others.

Useful for: preserving active sites, maintaining binding interfaces, keeping
catalytic residues unchanged while improving stability of the rest.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from opendna.engines.design import DesignConstraints, design as design_full
from opendna.models.protein import Sequence, Structure

logger = logging.getLogger(__name__)


@dataclass
class ConstrainedDesignResult:
    candidates: list[dict]
    fixed_positions: list[int]
    method: str
    note: str


def constrained_design(
    structure: Structure | str,
    fixed_positions: list[int],
    num_candidates: int = 10,
    temperature: float = 0.1,
) -> ConstrainedDesignResult:
    """Design new sequences while keeping specified positions fixed.

    Args:
        structure: Input backbone structure (Structure or PDB string)
        fixed_positions: 1-indexed list of positions to NOT mutate
        num_candidates: Number of variants to generate
        temperature: Sampling temperature

    Returns:
        Candidates with the fixed positions preserved.
    """
    # Run normal design
    constraints = DesignConstraints(
        num_candidates=num_candidates * 3,  # generate extra so we can filter
        temperature=temperature,
        fixed_positions=fixed_positions,
    )
    result = design_full(structure, constraints=constraints)

    # Get the original sequence from the structure for the fixed positions
    if isinstance(structure, str):
        struct = Structure.from_pdb_string(structure)
    else:
        struct = structure

    aa_map = {
        "ALA": "A", "CYS": "C", "ASP": "D", "GLU": "E", "PHE": "F",
        "GLY": "G", "HIS": "H", "ILE": "I", "LYS": "K", "LEU": "L",
        "MET": "M", "ASN": "N", "PRO": "P", "GLN": "Q", "ARG": "R",
        "SER": "S", "THR": "T", "VAL": "V", "TRP": "W", "TYR": "Y",
    }
    seen = set()
    original = []
    for atom in struct.atoms:
        key = (atom.chain_id, atom.residue_seq)
        if key not in seen:
            seen.add(key)
            original.append(aa_map.get(atom.residue_name, "A"))
    original_seq = "".join(original)

    # Force fixed positions back to original AA in each candidate
    valid_candidates = []
    for c in result.candidates:
        seq = list(str(c.sequence))
        for pos in fixed_positions:
            if 1 <= pos <= len(seq) and pos <= len(original_seq):
                seq[pos - 1] = original_seq[pos - 1]
        new_seq = "".join(seq)
        # Recompute recovery vs original
        recovery = sum(1 for a, b in zip(new_seq, original_seq) if a == b) / max(len(original_seq), 1)
        valid_candidates.append({
            "sequence": new_seq,
            "score": c.score,
            "recovery": round(recovery, 3),
            "fixed_preserved": True,
        })

    # Take top N
    valid_candidates.sort(key=lambda c: c["score"])
    valid_candidates = valid_candidates[:num_candidates]
    for i, c in enumerate(valid_candidates):
        c["rank"] = i + 1

    return ConstrainedDesignResult(
        candidates=valid_candidates,
        fixed_positions=fixed_positions,
        method="constrained-esm-if1",
        note=f"Generated {len(valid_candidates)} sequences with {len(fixed_positions)} positions fixed.",
    )
