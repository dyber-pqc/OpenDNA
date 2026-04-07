"""QSAR (Quantitative Structure-Activity Relationship) descriptors for peptides.

Computes molecular descriptors useful for QSAR modeling:
- Constitutional (counts, MW)
- Topological (connectivity)
- Geometric (shape)
- Electronic (charge, dipole)
- Hydrophobicity
"""

from __future__ import annotations

from opendna.engines.analysis import compute_properties, KD_HYDROPATHY


def compute_qsar_descriptors(sequence: str) -> dict:
    """Compute QSAR descriptors for a peptide sequence."""
    seq = sequence.upper()
    n = len(seq)
    if n == 0:
        return {}

    props = compute_properties(seq)

    # Constitutional descriptors
    constitutional = {
        "length": n,
        "mw": props.molecular_weight,
        "n_atoms_estimated": n * 7,  # rough avg per residue
        "n_carbon_estimated": n * 3,
        "n_nitrogen_estimated": n + sum(1 for a in seq if a in "NQRKHWY"),
        "n_oxygen_estimated": n + sum(1 for a in seq if a in "DESTNQYW"),
        "n_sulfur_estimated": sum(1 for a in seq if a in "CM"),
    }

    # Hydrophobicity descriptors
    hydropathy_values = [KD_HYDROPATHY.get(a, 0) for a in seq]
    hydrophobic = {
        "logp_estimate": props.gravy * 0.5,
        "gravy": props.gravy,
        "hydrophobic_residue_pct": sum(1 for a in seq if a in "AILMFWVP") / n * 100,
        "polar_residue_pct": sum(1 for a in seq if a in "STNQH") / n * 100,
        "max_hydrophobicity": max(hydropathy_values),
        "min_hydrophobicity": min(hydropathy_values),
        "hydrophobic_moment": _hydrophobic_moment(seq),
    }

    # Charge / electronic
    electronic = {
        "isoelectric_point": props.isoelectric_point,
        "net_charge_ph7": props.charge_at_ph7,
        "positive_residue_pct": sum(1 for a in seq if a in "KRH") / n * 100,
        "negative_residue_pct": sum(1 for a in seq if a in "DE") / n * 100,
        "abs_charge_ph7": abs(props.charge_at_ph7),
    }

    # Geometric / shape descriptors (rough peptide proxies)
    geometric = {
        "estimated_length_angstrom": n * 3.6,  # avg residue spacing
        "aspect_ratio_proxy": n / max(props.gravy + 5, 1),
        "compactness_proxy": props.aliphatic_index / 100,
    }

    # Topological / structure proxies
    topological = {
        "aromaticity": props.aromaticity,
        "sp3_carbon_pct": sum(1 for a in seq if a in "AILVPGCTSM") / n * 100,
        "rotatable_bonds_estimate": (n - 1) * 2,
        "ring_count_estimate": sum(1 for a in seq if a in "FWYHP"),
    }

    return {
        "constitutional": constitutional,
        "hydrophobic": hydrophobic,
        "electronic": electronic,
        "geometric": geometric,
        "topological": topological,
        "n_descriptors": (
            len(constitutional) + len(hydrophobic) + len(electronic)
            + len(geometric) + len(topological)
        ),
    }


def _hydrophobic_moment(seq: str, period_deg: float = 100.0) -> float:
    """Compute the hydrophobic moment (Eisenberg 1982).

    Measures how amphipathic the sequence is, assuming alpha-helix geometry.
    High value = one face hydrophobic, the other hydrophilic (membrane-active).
    """
    import math
    if len(seq) == 0:
        return 0.0
    period_rad = math.radians(period_deg)
    sum_sin = 0.0
    sum_cos = 0.0
    for i, aa in enumerate(seq):
        h = KD_HYDROPATHY.get(aa, 0)
        sum_sin += h * math.sin(i * period_rad)
        sum_cos += h * math.cos(i * period_rad)
    return round(math.sqrt(sum_sin ** 2 + sum_cos ** 2) / len(seq), 4)
