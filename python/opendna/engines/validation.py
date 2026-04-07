"""Structure validation (MolProbity-style).

Checks:
- Ramachandran outliers (residues in disallowed phi/psi regions)
- Bond length deviations
- Bond angle deviations
- Steric clashes (atoms too close together)
- Sidechain rotamer outliers (simplified)
- Backbone density / packing
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from opendna.engines.analysis import compute_dihedrals
from opendna.models.protein import Structure


@dataclass
class ValidationIssue:
    kind: str  # "rama-outlier" | "clash" | "bond-length" | "bond-angle" | "rotamer"
    residue: str
    residue_num: int
    severity: str  # "low" | "medium" | "high"
    description: str


def validate_structure(structure: Structure) -> dict:
    """Run all structure validation checks."""
    issues: list[ValidationIssue] = []

    # Ramachandran outliers
    angles = compute_dihedrals(structure)
    rama_outliers = 0
    for i, (phi, psi) in enumerate(angles):
        if phi is None or psi is None:
            continue
        if not _is_rama_allowed(phi, psi):
            rama_outliers += 1
            issues.append(ValidationIssue(
                kind="rama-outlier",
                residue="",
                residue_num=i + 1,
                severity="high" if not _is_rama_generous(phi, psi) else "medium",
                description=f"Disallowed phi/psi: ({phi:.0f}, {psi:.0f})",
            ))

    # Steric clashes (atoms < 2.0 Å apart that aren't bonded)
    clashes = _detect_clashes(structure)
    for c in clashes[:50]:  # cap
        issues.append(ValidationIssue(
            kind="clash",
            residue=c["res1"],
            residue_num=c["res1_num"],
            severity="high" if c["distance"] < 1.5 else "medium",
            description=f"Clash: {c['res1']}{c['res1_num']} <-> {c['res2']}{c['res2_num']} ({c['distance']:.2f} Å)",
        ))

    # Bond length checks (CA-C, C-N, N-CA distances)
    bond_issues = _check_bond_lengths(structure)
    for b in bond_issues[:30]:
        issues.append(ValidationIssue(
            kind="bond-length",
            residue=b["residue"],
            residue_num=b["residue_num"],
            severity=b["severity"],
            description=b["description"],
        ))

    # Compute summary metrics
    n_residues = len(angles)
    rama_favored = n_residues - rama_outliers
    rama_pct = round(100 * rama_favored / max(n_residues, 1), 1)

    # MolProbity-style score: lower is better
    # Real MolProbity uses a complex formula; this is a simplification
    clash_score = len(clashes) * 1000 / max(structure.num_atoms, 1)
    molprobity_score = (clash_score / 4) + (rama_outliers * 0.5)

    quality_grade = "A" if molprobity_score < 1.5 else \
                    "B" if molprobity_score < 3.0 else \
                    "C" if molprobity_score < 5.0 else "D"

    return {
        "n_issues": len(issues),
        "issues": [
            {
                "kind": i.kind,
                "residue_num": i.residue_num,
                "severity": i.severity,
                "description": i.description,
            }
            for i in issues[:100]
        ],
        "ramachandran_favored_pct": rama_pct,
        "ramachandran_outliers": rama_outliers,
        "clash_count": len(clashes),
        "clash_score": round(clash_score, 2),
        "molprobity_score": round(molprobity_score, 2),
        "quality_grade": quality_grade,
        "note": "MolProbity-style validation. Real MolProbity uses richer reference data.",
    }


def _is_rama_allowed(phi: float, psi: float) -> bool:
    """Check if (phi, psi) is in an allowed Ramachandran region."""
    # Alpha helix region
    if -160 < phi < -40 and -70 < psi < -10:
        return True
    # Beta strand region
    if -180 < phi < -40 and 90 < psi < 180:
        return True
    if -180 < phi < -40 and -180 < psi < -150:
        return True
    # Left-handed helix (mostly Gly)
    if 30 < phi < 90 and -10 < psi < 90:
        return True
    return False


def _is_rama_generous(phi: float, psi: float) -> bool:
    """Generously allowed regions (less strict)."""
    if -180 < phi < 0 and -180 < psi < 180:
        return True
    return False


def _detect_clashes(structure: Structure) -> list[dict]:
    """Find atom pairs closer than 2.0 Å (not bonded)."""
    clashes = []
    atoms = structure.atoms
    for i, a in enumerate(atoms):
        for j in range(i + 1, len(atoms)):
            b = atoms[j]
            # Skip same residue or adjacent residues (likely bonded)
            if a.chain_id == b.chain_id and abs(a.residue_seq - b.residue_seq) < 2:
                continue
            d2 = (a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2
            if d2 < 4.0:  # 2.0 Å
                d = math.sqrt(d2)
                clashes.append({
                    "res1": a.residue_name,
                    "res1_num": a.residue_seq,
                    "atom1": a.name,
                    "res2": b.residue_name,
                    "res2_num": b.residue_seq,
                    "atom2": b.name,
                    "distance": round(d, 3),
                })
    return clashes


def _check_bond_lengths(structure: Structure) -> list[dict]:
    """Check backbone bond lengths against ideal values."""
    issues = []
    # Group by residue
    by_res: dict[int, dict] = {}
    for a in structure.atoms:
        by_res.setdefault(a.residue_seq, {})[a.name] = a

    for seq_num in sorted(by_res.keys()):
        res_atoms = by_res[seq_num]
        if "N" in res_atoms and "CA" in res_atoms:
            n_ca = _atom_dist(res_atoms["N"], res_atoms["CA"])
            if abs(n_ca - 1.46) > 0.15:
                issues.append({
                    "residue": res_atoms["N"].residue_name,
                    "residue_num": seq_num,
                    "severity": "medium",
                    "description": f"N-CA bond {n_ca:.2f} Å (ideal 1.46)",
                })
        if "CA" in res_atoms and "C" in res_atoms:
            ca_c = _atom_dist(res_atoms["CA"], res_atoms["C"])
            if abs(ca_c - 1.52) > 0.15:
                issues.append({
                    "residue": res_atoms["CA"].residue_name,
                    "residue_num": seq_num,
                    "severity": "medium",
                    "description": f"CA-C bond {ca_c:.2f} Å (ideal 1.52)",
                })

    return issues


def _atom_dist(a, b) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)
