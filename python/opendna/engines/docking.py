"""Docking engine: protein-ligand binding prediction.

Uses the real DiffDock model when available (via the diffdock-pip package
or the official diffdock GitHub installation). Falls back to a heuristic
pocket-based estimator otherwise.

To enable real DiffDock:
    pip install diffdock-pp  # or follow https://github.com/gcorso/DiffDock setup
"""

from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class DockResult:
    affinity_kcal_mol: float
    confidence: float
    pocket_residues: list[int] = field(default_factory=list)
    poses: list[dict] = field(default_factory=list)
    method: str = "heuristic"
    explanation: str = ""


def dock_ligand(
    pdb_string: str,
    ligand_smiles: str,
    on_progress: Optional[callable] = None,
) -> DockResult:
    """Dock a ligand into a protein structure.

    Tries DiffDock first (if installed), falls back to heuristic.
    """
    # Try real DiffDock implementations
    for impl in (_diffdock_pp, _diffdock_official, _diffdock_pip):
        try:
            result = impl(pdb_string, ligand_smiles, on_progress)
            if result is not None:
                return result
        except ImportError:
            continue
        except Exception as e:
            logger.warning(f"DiffDock implementation {impl.__name__} failed: {e}")
            continue

    logger.info("No DiffDock implementation available, using heuristic")
    return _heuristic_dock(pdb_string, ligand_smiles, on_progress)


def _diffdock_pp(pdb_string, ligand_smiles, on_progress):
    """Try the diffdock_pp package (https://github.com/Yangtao-Wang/DiffDockPP)."""
    try:
        from diffdock_pp import DiffDockPP  # type: ignore
    except ImportError:
        return None

    if on_progress:
        on_progress("Loading DiffDock-PP", 0.1)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".pdb", delete=False) as f:
        f.write(pdb_string)
        pdb_path = f.name

    try:
        if on_progress:
            on_progress("Running DiffDock-PP inference", 0.4)
        model = DiffDockPP.from_pretrained()
        result = model.dock(pdb_path, ligand_smiles)
        return DockResult(
            affinity_kcal_mol=float(result.get("affinity", -7.0)),
            confidence=float(result.get("confidence", 0.7)),
            poses=result.get("poses", []),
            method="diffdock-pp",
            explanation="Real DiffDock-PP prediction.",
        )
    finally:
        try:
            Path(pdb_path).unlink()
        except OSError:
            pass


def _diffdock_official(pdb_string, ligand_smiles, on_progress):
    """Try the official DiffDock package."""
    try:
        from diffdock import inference  # type: ignore
    except ImportError:
        return None

    if on_progress:
        on_progress("Loading official DiffDock", 0.1)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".pdb", delete=False) as f:
        f.write(pdb_string)
        pdb_path = f.name

    try:
        if on_progress:
            on_progress("Running DiffDock inference", 0.4)
        result = inference.run(pdb_path, ligand_smiles)
        return DockResult(
            affinity_kcal_mol=float(result.get("affinity", -7.0)),
            confidence=float(result.get("confidence", 0.7)),
            poses=result.get("poses", []),
            method="diffdock-official",
            explanation="Real DiffDock prediction (official model).",
        )
    finally:
        try:
            Path(pdb_path).unlink()
        except OSError:
            pass


def _diffdock_pip(pdb_string, ligand_smiles, on_progress):
    """Try the diffdock pip-installable package."""
    try:
        import diffdock as dd  # type: ignore
    except ImportError:
        return None

    if on_progress:
        on_progress("Loading DiffDock", 0.1)

    if hasattr(dd, "dock"):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pdb", delete=False) as f:
            f.write(pdb_string)
            pdb_path = f.name
        try:
            result = dd.dock(pdb_path, ligand_smiles)
            return DockResult(
                affinity_kcal_mol=float(result.get("score", -7.0)),
                confidence=float(result.get("confidence", 0.7)),
                method="diffdock-pip",
                explanation="DiffDock prediction.",
            )
        finally:
            try:
                Path(pdb_path).unlink()
            except OSError:
                pass
    return None


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

    n_heavy_atoms = sum(1 for c in ligand_smiles if c.isupper() and c in "CNOSPFI")
    affinity = -3.0 - (n_heavy_atoms * 0.3) + (len(ligand_smiles) * 0.05)
    affinity = max(-15.0, min(-1.0, affinity))

    if on_progress:
        on_progress("Complete", 1.0)

    return DockResult(
        affinity_kcal_mol=round(affinity, 2),
        confidence=0.3,
        pocket_residues=[p["residue_index"] for p in pockets],
        method="heuristic",
        explanation=(
            f"Found {len(pockets)} putative binding pockets. "
            f"Estimated binding affinity: {affinity:.2f} kcal/mol. "
            "Heuristic only - install DiffDock for production accuracy: "
            "https://github.com/gcorso/DiffDock"
        ),
    )


def virtual_screen(pdb_string: str, ligand_smiles_list: list[str]) -> list[dict]:
    """Screen multiple ligands and rank by affinity."""
    results = []
    for i, smiles in enumerate(ligand_smiles_list):
        try:
            r = dock_ligand(pdb_string, smiles)
            results.append({
                "rank": 0,
                "smiles": smiles,
                "affinity": r.affinity_kcal_mol,
                "confidence": r.confidence,
                "method": r.method,
            })
        except Exception as e:
            logger.warning(f"Dock failed for {smiles}: {e}")

    results.sort(key=lambda x: x["affinity"])
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return results
