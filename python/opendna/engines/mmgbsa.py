"""MMGBSA-style binding affinity estimation.

Real MMGBSA (Molecular Mechanics with Generalized Born Surface Area) requires
running molecular dynamics and decomposing the energy into:
- Van der Waals (E_vdW)
- Electrostatics (E_ele)
- Polar solvation (E_GB)
- Non-polar solvation (E_SA)

This module implements a heuristic estimator using:
- Pocket descriptors
- Ligand size and properties
- Knowledge-based shape complementarity
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from opendna.engines.analysis import detect_pockets
from opendna.models.protein import Structure


@dataclass
class MmgbsaResult:
    binding_energy_kcal_mol: float
    components: dict[str, float]
    confidence: str
    method: str
    note: str


def estimate_binding_energy(
    structure: Structure,
    ligand_smiles: str,
    pocket_residue: int = None,
) -> MmgbsaResult:
    """Estimate the binding energy of a ligand to a protein pocket.

    Heuristic approach using:
    - Ligand heavy atom count (proxy for size and contact area)
    - Aromatic ring count (proxy for pi-pi stacking)
    - H-bond donor/acceptor count
    - Pocket buriedness
    """
    # Find best pocket if not specified
    pockets = detect_pockets(structure)
    if not pockets:
        return MmgbsaResult(
            binding_energy_kcal_mol=0.0,
            components={},
            confidence="low",
            method="heuristic",
            note="No pocket detected",
        )

    if pocket_residue is None:
        pocket = pockets[0]
    else:
        pocket = next((p for p in pockets if p["residue_index"] == pocket_residue), pockets[0])

    # Parse ligand SMILES heuristically
    smiles = ligand_smiles.upper()
    n_heavy = sum(1 for c in smiles if c.isalpha() and c in "CNOSPFI")
    n_aromatic = smiles.count("c") + smiles.count("C1=") + smiles.count("=C")
    n_donors = smiles.count("OH") + smiles.count("NH") + smiles.count("N(")
    n_acceptors = smiles.count("O") + smiles.count("N") - n_donors
    has_carboxyl = "C(=O)O" in ligand_smiles or "COO" in smiles

    # Components (rough kcal/mol)
    e_vdw = -0.3 * n_heavy  # -0.3 per heavy atom contact
    e_ele = -0.5 if has_carboxyl else 0.0
    e_pi = -0.5 * n_aromatic  # pi-stacking
    e_hb = -0.7 * min(n_donors + n_acceptors, 6)  # H-bonds, capped
    e_sa = -0.005 * n_heavy * 10  # surface area term

    # Pocket buriedness adjustment
    pocket_factor = pocket.get("score", 0.5)
    e_solvation = -2.0 * pocket_factor

    total = e_vdw + e_ele + e_pi + e_hb + e_sa + e_solvation
    total = max(-15.0, min(-1.0, total))

    return MmgbsaResult(
        binding_energy_kcal_mol=round(total, 2),
        components={
            "vdw": round(e_vdw, 2),
            "electrostatic": round(e_ele, 2),
            "pi_stacking": round(e_pi, 2),
            "h_bonds": round(e_hb, 2),
            "surface_area": round(e_sa, 2),
            "solvation": round(e_solvation, 2),
        },
        confidence="low",  # heuristic
        method="heuristic-mmgbsa",
        note=(
            "Heuristic estimate. Real MMGBSA requires running MD and decomposing the energy. "
            "For production use AmberTools MMPBSA.py or Schrödinger Prime MM-GBSA."
        ),
    )
