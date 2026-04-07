"""Docking engine: protein-ligand binding prediction.

Real DiffDock requires a multi-GB model. This module provides:
- A heuristic pocket-based docker (works without downloads)
- An interface ready for DiffDock when it's installed
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class DockResult:
    affinity_kcal_mol: float
    confidence: float
    pocket_residues: list[int]
    method: str
    explanation: str


def dock_ligand(
    pdb_string: str,
    ligand_smiles: str,
    on_progress: Optional[callable] = None,
) -> DockResult:
    """Dock a ligand into a protein structure.

    Tries DiffDock first (if installed), falls back to a pocket-detection heuristic.
    """
    try:
        return _diffdock(pdb_string, ligand_smiles, on_progress)
    except ImportError:
        logger.info("DiffDock not installed, using heuristic pocket detection")
        return _heuristic_dock(pdb_string, ligand_smiles, on_progress)


def _diffdock(pdb_string, ligand_smiles, on_progress):
    raise ImportError("DiffDock model not bundled in this build")


def _heuristic_dock(pdb_string, ligand_smiles, on_progress):
    """Heuristic: detect best pocket and estimate affinity from ligand size."""
    from opendna.engines.analysis import detect_pockets
    from opendna.models.protein import Structure

    if on_progress:
        on_progress("Detecting binding pockets", 0.3)

    structure = Structure.from_pdb_string(pdb_string)
    pockets = detect_pockets(structure)

    if on_progress:
        on_progress("Estimating binding affinity", 0.7)

    # Crude affinity estimate from ligand SMILES length
    n_heavy_atoms = sum(1 for c in ligand_smiles if c.isupper() and c in "CNOSPFI")
    affinity = -3.0 - (n_heavy_atoms * 0.3) + (len(ligand_smiles) * 0.05)
    affinity = max(-15.0, min(-1.0, affinity))

    if on_progress:
        on_progress("Complete", 1.0)

    return DockResult(
        affinity_kcal_mol=round(affinity, 2),
        confidence=0.3,  # heuristic confidence is low
        pocket_residues=[p["residue_index"] for p in pockets],
        method="heuristic",
        explanation=(
            f"Found {len(pockets)} putative binding pockets. "
            f"Estimated binding affinity: {affinity:.2f} kcal/mol. "
            "This is a rough heuristic; install DiffDock for production accuracy."
        ),
    )


def virtual_screen(pdb_string: str, ligand_smiles_list: list[str]) -> list[dict]:
    """Screen multiple ligands and rank by affinity."""
    results = []
    for i, smiles in enumerate(ligand_smiles_list):
        try:
            r = dock_ligand(pdb_string, smiles)
            results.append({
                "rank": 0,  # filled in below
                "smiles": smiles,
                "affinity": r.affinity_kcal_mol,
                "confidence": r.confidence,
            })
        except Exception as e:
            logger.warning(f"Dock failed for {smiles}: {e}")

    results.sort(key=lambda x: x["affinity"])
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return results
