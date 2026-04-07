"""Pharmacophore feature extraction.

A pharmacophore is the 3D arrangement of features (H-bond donors, acceptors,
positive/negative charges, hydrophobic centers, aromatic rings) that a ligand
needs to bind a receptor.

This module extracts these features from a protein binding pocket.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from opendna.models.protein import Structure


@dataclass
class PharmacophoreFeature:
    feature_type: str  # "donor" | "acceptor" | "positive" | "negative" | "hydrophobic" | "aromatic"
    residue: str
    residue_num: int
    position: tuple[float, float, float]  # x, y, z


@dataclass
class Pharmacophore:
    features: list[dict]
    n_donors: int
    n_acceptors: int
    n_positive: int
    n_negative: int
    n_hydrophobic: int
    n_aromatic: int
    center: tuple[float, float, float]


# Pharmacophore feature definitions per amino acid
DONOR_ATOMS = {
    "ASN": ["ND2"],
    "GLN": ["NE2"],
    "HIS": ["ND1", "NE2"],
    "LYS": ["NZ"],
    "ARG": ["NE", "NH1", "NH2"],
    "SER": ["OG"],
    "THR": ["OG1"],
    "TYR": ["OH"],
    "TRP": ["NE1"],
}

ACCEPTOR_ATOMS = {
    "ASP": ["OD1", "OD2"],
    "GLU": ["OE1", "OE2"],
    "ASN": ["OD1"],
    "GLN": ["OE1"],
    "SER": ["OG"],
    "THR": ["OG1"],
    "TYR": ["OH"],
    "HIS": ["ND1", "NE2"],
}

POSITIVE_ATOMS = {
    "LYS": ["NZ"],
    "ARG": ["NH1", "NH2"],
    "HIS": ["ND1", "NE2"],
}

NEGATIVE_ATOMS = {
    "ASP": ["OD1", "OD2"],
    "GLU": ["OE1", "OE2"],
}

HYDROPHOBIC_RESIDUES = {"ALA", "VAL", "LEU", "ILE", "MET", "PHE", "TRP", "PRO"}
AROMATIC_RESIDUES = {"PHE", "TRP", "TYR", "HIS"}


def extract_pharmacophore(structure: Structure, pocket_residues: Optional[list[int]] = None) -> Pharmacophore:
    """Extract pharmacophore features from a structure (or specific pocket residues).

    If pocket_residues is None, extracts features from the entire structure.
    """
    features: list[PharmacophoreFeature] = []

    for atom in structure.atoms:
        if pocket_residues and atom.residue_seq not in pocket_residues:
            continue

        res = atom.residue_name
        atom_name = atom.name
        pos = (atom.x, atom.y, atom.z)

        # Donors
        if res in DONOR_ATOMS and atom_name in DONOR_ATOMS[res]:
            features.append(PharmacophoreFeature("donor", res, atom.residue_seq, pos))

        # Acceptors
        if res in ACCEPTOR_ATOMS and atom_name in ACCEPTOR_ATOMS[res]:
            features.append(PharmacophoreFeature("acceptor", res, atom.residue_seq, pos))

        # Positive
        if res in POSITIVE_ATOMS and atom_name in POSITIVE_ATOMS[res]:
            features.append(PharmacophoreFeature("positive", res, atom.residue_seq, pos))

        # Negative
        if res in NEGATIVE_ATOMS and atom_name in NEGATIVE_ATOMS[res]:
            features.append(PharmacophoreFeature("negative", res, atom.residue_seq, pos))

        # Hydrophobic centers (CB or beyond)
        if res in HYDROPHOBIC_RESIDUES and atom_name == "CB":
            features.append(PharmacophoreFeature("hydrophobic", res, atom.residue_seq, pos))

        # Aromatic centers (CG of aromatic residues)
        if res in AROMATIC_RESIDUES and atom_name == "CG":
            features.append(PharmacophoreFeature("aromatic", res, atom.residue_seq, pos))

    # Compute center of mass
    if features:
        cx = sum(f.position[0] for f in features) / len(features)
        cy = sum(f.position[1] for f in features) / len(features)
        cz = sum(f.position[2] for f in features) / len(features)
        center = (round(cx, 2), round(cy, 2), round(cz, 2))
    else:
        center = (0.0, 0.0, 0.0)

    return Pharmacophore(
        features=[
            {
                "type": f.feature_type,
                "residue": f.residue,
                "residue_num": f.residue_num,
                "x": round(f.position[0], 2),
                "y": round(f.position[1], 2),
                "z": round(f.position[2], 2),
            }
            for f in features
        ],
        n_donors=sum(1 for f in features if f.feature_type == "donor"),
        n_acceptors=sum(1 for f in features if f.feature_type == "acceptor"),
        n_positive=sum(1 for f in features if f.feature_type == "positive"),
        n_negative=sum(1 for f in features if f.feature_type == "negative"),
        n_hydrophobic=sum(1 for f in features if f.feature_type == "hydrophobic"),
        n_aromatic=sum(1 for f in features if f.feature_type == "aromatic"),
        center=center,
    )
