"""Real heavy-model backends (Phase 3).

Each function detects whether the underlying package is importable, and if so
runs the real model. Otherwise raises NotInstalledError so callers can fall
back to the existing CPU/heuristic implementations.

Supported:
  - DiffDock           protein-ligand docking
  - RFdiffusion        de novo backbone generation
  - Boltz-1            multimer folding
  - ColabFold/AF2      multimer folding (alternate)
  - xTB                semiempirical QM single-points
  - TorchANI (ANI-2x)  ML potential energies / minimization
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class NotInstalledError(RuntimeError):
    """Raised when a real model package is not importable."""


def _require(mod: str, friendly: str) -> Any:
    try:
        return __import__(mod)
    except Exception as e:
        raise NotInstalledError(
            f"{friendly} is not installed. Install it from the Component Manager."
        ) from e


# ---------- DiffDock ----------

def diffdock_dock(
    pdb_string: str,
    ligand_smiles: str,
    num_poses: int = 10,
) -> Dict[str, Any]:
    """Run DiffDock. Returns {poses: [{pose_pdb, score, rank}], engine: 'diffdock'}."""
    _require("diffdock", "DiffDock")
    # DiffDock's public API varies by version; provide a thin call wrapper.
    try:
        from diffdock import dock as _dock  # type: ignore
        result = _dock(protein_pdb=pdb_string, ligand=ligand_smiles, num_poses=num_poses)
        poses = []
        for i, p in enumerate(result):
            poses.append({
                "rank": i + 1,
                "score": float(getattr(p, "score", 0.0)),
                "pose_pdb": getattr(p, "pdb", ""),
            })
        return {"engine": "diffdock", "poses": poses}
    except ImportError as e:
        raise NotInstalledError("DiffDock importable but API missing") from e


# ---------- RFdiffusion ----------

def rfdiffusion_design(
    length: int = 100,
    contigs: Optional[str] = None,
    num_designs: int = 1,
) -> Dict[str, Any]:
    """Generate de novo backbones with RFdiffusion."""
    _require("rfdiffusion", "RFdiffusion")
    try:
        from rfdiffusion.inference import run_inference  # type: ignore
        cfg = {
            "contigmap.contigs": contigs or f"[{length}-{length}]",
            "inference.num_designs": num_designs,
        }
        designs = run_inference(cfg)
        return {
            "engine": "rfdiffusion",
            "designs": [
                {"index": i, "pdb": d} for i, d in enumerate(designs)
            ],
        }
    except Exception as e:
        raise NotInstalledError(f"RFdiffusion call failed: {e}") from e


# ---------- Boltz-1 multimer ----------

def boltz_multimer(
    sequences: List[str],
) -> Dict[str, Any]:
    """Fold a complex with Boltz-1."""
    _require("boltz", "Boltz-1")
    try:
        # Boltz ships a CLI; we invoke its python runner when available.
        from boltz.main import predict  # type: ignore
        result = predict(sequences=sequences)
        return {
            "engine": "boltz",
            "pdb": getattr(result, "pdb", ""),
            "ptm": float(getattr(result, "ptm", 0.0)),
            "iptm": float(getattr(result, "iptm", 0.0)),
            "plddt_mean": float(getattr(result, "plddt_mean", 0.0)),
        }
    except Exception as e:
        raise NotInstalledError(f"Boltz call failed: {e}") from e


# ---------- ColabFold / AF2 multimer ----------

def colabfold_multimer(
    sequences: List[str],
) -> Dict[str, Any]:
    _require("colabfold", "ColabFold")
    try:
        from colabfold.batch import run as cf_run  # type: ignore
        joined = ":".join(sequences)
        result = cf_run([(f"query", joined)])
        return {
            "engine": "colabfold",
            "pdb": getattr(result[0], "unrelaxed_pdb", "") if result else "",
        }
    except Exception as e:
        raise NotInstalledError(f"ColabFold call failed: {e}") from e


# ---------- xTB (semiempirical QM) ----------

def xtb_single_point(pdb_string: str) -> Dict[str, Any]:
    """Compute GFN2-xTB single-point energy for a small molecule or peptide."""
    xtb = _require("xtb", "xTB")
    try:
        from xtb.interface import Calculator, Param  # type: ignore
        # Parse PDB → atomic numbers + coords
        numbers: List[int] = []
        coords: List[List[float]] = []
        PT = {"H": 1, "C": 6, "N": 7, "O": 8, "S": 16, "P": 15, "F": 9, "CL": 17, "BR": 35}
        for line in pdb_string.splitlines():
            if line.startswith(("ATOM", "HETATM")):
                elem = line[76:78].strip().upper() or line[12:14].strip().upper()
                z = PT.get(elem[:2], PT.get(elem[:1]))
                if z is None:
                    continue
                numbers.append(z)
                coords.append([float(line[30:38]), float(line[38:46]), float(line[46:54])])
        if not numbers:
            raise NotInstalledError("No parseable atoms in PDB for xTB")
        import numpy as np  # type: ignore
        arr = np.array(coords) * 1.8897259886  # Å → Bohr
        calc = Calculator(Param.GFN2xTB, np.array(numbers), arr)
        res = calc.singlepoint()
        return {
            "engine": "xtb",
            "energy_hartree": float(res.get_energy()),
            "energy_kj_mol": float(res.get_energy()) * 2625.5,
            "n_atoms": len(numbers),
        }
    except NotInstalledError:
        raise
    except Exception as e:
        raise NotInstalledError(f"xTB call failed: {e}") from e


# ---------- TorchANI (ANI-2x) ----------

def ani_energy(pdb_string: str) -> Dict[str, Any]:
    """ANI-2x ML potential energy for an organic molecule."""
    _require("torchani", "TorchANI")
    try:
        import torch  # type: ignore
        import torchani  # type: ignore
        model = torchani.models.ANI2x(periodic_table_index=True)
        PT = {"H": 1, "C": 6, "N": 7, "O": 8, "F": 9, "S": 16, "CL": 17}
        numbers, coords = [], []
        for line in pdb_string.splitlines():
            if line.startswith(("ATOM", "HETATM")):
                elem = line[76:78].strip().upper() or line[12:14].strip().upper()
                z = PT.get(elem[:2], PT.get(elem[:1]))
                if z is None:
                    continue
                numbers.append(z)
                coords.append([float(line[30:38]), float(line[38:46]), float(line[46:54])])
        if not numbers:
            raise NotInstalledError("No ANI-supported atoms in PDB")
        species = torch.tensor([numbers], dtype=torch.long)
        coordinates = torch.tensor([coords], dtype=torch.float32, requires_grad=False)
        energy = model((species, coordinates)).energies
        return {
            "engine": "ani-2x",
            "energy_hartree": float(energy.item()),
            "energy_kj_mol": float(energy.item()) * 2625.5,
            "n_atoms": len(numbers),
        }
    except NotInstalledError:
        raise
    except Exception as e:
        raise NotInstalledError(f"TorchANI call failed: {e}") from e


# ---------- Dispatch helpers ----------

def available_backends() -> Dict[str, bool]:
    """Report which real model backends are importable right now."""
    def _chk(m: str) -> bool:
        try:
            __import__(m)
            return True
        except Exception:
            return False
    return {
        "diffdock": _chk("diffdock"),
        "rfdiffusion": _chk("rfdiffusion"),
        "boltz": _chk("boltz"),
        "colabfold": _chk("colabfold"),
        "xtb": _chk("xtb"),
        "torchani": _chk("torchani"),
    }
