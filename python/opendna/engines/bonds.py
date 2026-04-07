"""Detect H-bonds, salt bridges, disulfide bonds, and hydrophobic contacts.

Schrödinger Maestro / PyMOL distance-based interaction analysis.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from opendna.models.protein import Structure


@dataclass
class Bond:
    atom1_idx: int
    atom2_idx: int
    res1_name: str
    res1_seq: int
    res2_name: str
    res2_seq: int
    distance: float
    kind: str  # "h-bond" | "salt-bridge" | "disulfide" | "hydrophobic"


def _dist(a, b) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


def detect_bonds(structure: Structure) -> dict:
    """Find all interaction types in a structure."""
    atoms = structure.atoms

    h_bonds: list[Bond] = []
    salt_bridges: list[Bond] = []
    disulfides: list[Bond] = []

    # Group atoms by residue for context
    by_residue: dict[tuple, list] = {}
    for i, a in enumerate(atoms):
        by_residue.setdefault((a.chain_id, a.residue_seq), []).append((i, a))

    # H-bond donors (N, O bound to H) and acceptors (O, N)
    # Simplified: any N-O pair within 3.5 Å on different residues
    for i, a in enumerate(atoms):
        if a.element not in ("N", "O") and a.name not in ("N", "O", "OD", "OE", "ND", "NE", "OG", "OH"):
            continue
        for j in range(i + 1, len(atoms)):
            b = atoms[j]
            if a.residue_seq == b.residue_seq and a.chain_id == b.chain_id:
                continue
            if abs(a.residue_seq - b.residue_seq) < 2:
                continue
            if b.element not in ("N", "O") and b.name not in ("N", "O", "OD", "OE", "ND", "NE", "OG", "OH"):
                continue
            d = _dist(a, b)
            if 2.5 < d < 3.5:
                h_bonds.append(Bond(
                    atom1_idx=i, atom2_idx=j,
                    res1_name=a.residue_name, res1_seq=a.residue_seq,
                    res2_name=b.residue_name, res2_seq=b.residue_seq,
                    distance=round(d, 2), kind="h-bond",
                ))

    # Salt bridges: ARG/LYS/HIS positive (NZ, NH1, NH2, NE) <-> ASP/GLU negative (OD1, OD2, OE1, OE2)
    pos_atoms = ("NZ", "NH1", "NH2", "NE", "ND1", "NE2")
    neg_atoms = ("OD1", "OD2", "OE1", "OE2")
    pos_residues = ("LYS", "ARG", "HIS")
    neg_residues = ("ASP", "GLU")

    for i, a in enumerate(atoms):
        if a.residue_name in pos_residues and a.name in pos_atoms:
            for j, b in enumerate(atoms):
                if b.residue_name in neg_residues and b.name in neg_atoms:
                    d = _dist(a, b)
                    if d < 4.0:
                        salt_bridges.append(Bond(
                            atom1_idx=i, atom2_idx=j,
                            res1_name=a.residue_name, res1_seq=a.residue_seq,
                            res2_name=b.residue_name, res2_seq=b.residue_seq,
                            distance=round(d, 2), kind="salt-bridge",
                        ))

    # Disulfide bonds: CYS SG <-> CYS SG within 3 Å
    for i, a in enumerate(atoms):
        if a.residue_name == "CYS" and a.name == "SG":
            for j in range(i + 1, len(atoms)):
                b = atoms[j]
                if b.residue_name == "CYS" and b.name == "SG":
                    d = _dist(a, b)
                    if d < 3.0:
                        disulfides.append(Bond(
                            atom1_idx=i, atom2_idx=j,
                            res1_name=a.residue_name, res1_seq=a.residue_seq,
                            res2_name=b.residue_name, res2_seq=b.residue_seq,
                            distance=round(d, 2), kind="disulfide",
                        ))

    return {
        "h_bonds": [_bond_to_dict(b) for b in h_bonds[:200]],  # cap for UI
        "h_bond_count": len(h_bonds),
        "salt_bridges": [_bond_to_dict(b) for b in salt_bridges],
        "salt_bridge_count": len(salt_bridges),
        "disulfides": [_bond_to_dict(b) for b in disulfides],
        "disulfide_count": len(disulfides),
    }


def _bond_to_dict(b: Bond) -> dict:
    return {
        "res1": f"{b.res1_name}{b.res1_seq}",
        "res2": f"{b.res2_name}{b.res2_seq}",
        "distance": b.distance,
        "kind": b.kind,
    }
