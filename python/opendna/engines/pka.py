"""pKa prediction for ionizable residues (PROPKA-style heuristic).

For each ionizable residue (Asp, Glu, His, Cys, Tyr, Lys, Arg) computes a pKa
shift from the standard reference value based on:
- Local desolvation (buried vs exposed)
- Hydrogen bonds with nearby residues
- Coulombic interactions with other charged residues
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from opendna.models.protein import Structure

# Standard pKa values
STANDARD_PKA = {
    "ASP": 3.80, "GLU": 4.50, "HIS": 6.50, "CYS": 8.30,
    "TYR": 10.00, "LYS": 10.50, "ARG": 12.50, "N+": 8.00, "C-": 3.10,
}

# Charged "titratable" residues
IONIZABLE = set(STANDARD_PKA.keys())


@dataclass
class PkaPrediction:
    residue: str
    residue_num: int
    standard_pka: float
    predicted_pka: float
    shift: float
    status_at_ph7: str  # "deprotonated" / "protonated" / "neutral"


def predict_pka(structure: Structure) -> dict:
    """Predict per-residue pKa for ionizable residues."""
    atoms = structure.atoms

    # Group by residue
    residues_atoms: dict[tuple, list] = {}
    for a in atoms:
        residues_atoms.setdefault((a.chain_id, a.residue_seq), []).append(a)

    predictions: list[PkaPrediction] = []

    for (chain, seq_num), res_atoms in residues_atoms.items():
        if not res_atoms:
            continue
        res_name = res_atoms[0].residue_name
        if res_name not in IONIZABLE:
            continue

        std = STANDARD_PKA[res_name]

        # Compute desolvation: count atoms within 8 Å of the side-chain centroid
        side_chain_atoms = [a for a in res_atoms if a.name not in ("N", "CA", "C", "O")]
        if not side_chain_atoms:
            continue
        cx = sum(a.x for a in side_chain_atoms) / len(side_chain_atoms)
        cy = sum(a.y for a in side_chain_atoms) / len(side_chain_atoms)
        cz = sum(a.z for a in side_chain_atoms) / len(side_chain_atoms)

        neighbors = 0
        for other in atoms:
            if (other.chain_id, other.residue_seq) == (chain, seq_num):
                continue
            d2 = (other.x - cx) ** 2 + (other.y - cy) ** 2 + (other.z - cz) ** 2
            if d2 < 64:  # 8 Å
                neighbors += 1

        # Buried-ness factor (more neighbors = more buried)
        buried_factor = min(1.0, neighbors / 60)

        # Desolvation shift: buried acids become harder to deprotonate (pKa up)
        # buried bases become harder to protonate (pKa down)
        if res_name in ("ASP", "GLU", "CYS", "TYR"):
            shift = buried_factor * 2.0  # acid pKa up
        elif res_name in ("HIS", "LYS", "ARG"):
            shift = -buried_factor * 1.5  # base pKa down
        else:
            shift = 0.0

        # Coulombic interactions: nearby opposite charges shift pKa
        for other in atoms:
            if (other.chain_id, other.residue_seq) == (chain, seq_num):
                continue
            if other.name not in ("NZ", "NH1", "NH2", "OD1", "OD2", "OE1", "OE2"):
                continue
            d2 = (other.x - cx) ** 2 + (other.y - cy) ** 2 + (other.z - cz) ** 2
            if 9 < d2 < 100:  # 3-10 Å
                d = math.sqrt(d2)
                # Salt bridge: shift the acid down (easier to deprotonate)
                if res_name in ("ASP", "GLU") and other.residue_name in ("LYS", "ARG"):
                    shift -= 0.5 / max(d, 3.0)
                elif res_name in ("LYS", "ARG") and other.residue_name in ("ASP", "GLU"):
                    shift += 0.5 / max(d, 3.0)

        predicted = std + shift

        # Status at pH 7
        if res_name in ("ASP", "GLU", "CYS", "TYR"):
            status = "deprotonated" if 7.0 > predicted else "protonated"
        elif res_name in ("HIS", "LYS", "ARG"):
            status = "protonated" if 7.0 < predicted else "deprotonated"
        else:
            status = "neutral"

        predictions.append(PkaPrediction(
            residue=res_name,
            residue_num=seq_num,
            standard_pka=std,
            predicted_pka=round(predicted, 2),
            shift=round(shift, 2),
            status_at_ph7=status,
        ))

    predictions.sort(key=lambda p: p.residue_num)

    # Compute net charge at pH 7
    n_pos = sum(1 for p in predictions if p.status_at_ph7 == "protonated" and p.residue in ("LYS", "ARG", "HIS"))
    n_neg = sum(1 for p in predictions if p.status_at_ph7 == "deprotonated" and p.residue in ("ASP", "GLU"))
    net_charge = n_pos - n_neg

    return {
        "predictions": [
            {
                "residue": p.residue,
                "residue_num": p.residue_num,
                "standard_pka": p.standard_pka,
                "predicted_pka": p.predicted_pka,
                "shift": p.shift,
                "status_at_ph7": p.status_at_ph7,
            }
            for p in predictions
        ],
        "n_ionizable": len(predictions),
        "net_charge_at_ph7": net_charge,
        "method": "PROPKA-style heuristic",
        "note": "Heuristic predictions. For accurate pKa use PROPKA3, H++, or DelPhi-pKa.",
    }
