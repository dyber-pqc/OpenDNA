"""Sequence-based predictors:
- Transmembrane regions (TMHMM-like)
- Signal peptides (SignalP-like)
- Aggregation propensity (TANGO-like)
- Solubility (Camsol-like)
- Phosphorylation sites
- Glycosylation sites
- N-terminal acetylation
- B-cell epitopes
- Stability (DDG) prediction for mutations
"""

from __future__ import annotations

import math
import re

from opendna.engines.analysis import KD_HYDROPATHY


# =====================================================
# Transmembrane prediction (TMHMM-like)
# =====================================================

def predict_transmembrane(sequence: str, threshold: float = 1.4, min_length: int = 15) -> dict:
    """Predict transmembrane helices using sliding-window hydrophobicity."""
    seq = sequence.upper()
    n = len(seq)
    window = 19
    half = window // 2

    scores = []
    for i in range(n):
        chunk = seq[max(0, i - half):min(n, i + half + 1)]
        score = sum(KD_HYDROPATHY.get(a, 0) for a in chunk) / len(chunk)
        scores.append(score)

    regions = []
    in_region = False
    start = 0
    for i, s in enumerate(scores):
        if s >= threshold and not in_region:
            in_region = True
            start = i
        elif s < threshold and in_region:
            if i - start >= min_length:
                regions.append({"start": start + 1, "end": i, "length": i - start})
            in_region = False
    if in_region and n - start >= min_length:
        regions.append({"start": start + 1, "end": n, "length": n - start})

    return {
        "scores": [round(s, 3) for s in scores],
        "regions": regions,
        "n_helices": len(regions),
        "is_membrane_protein": len(regions) >= 1,
        "note": "TMHMM-like heuristic. Each region predicted as a transmembrane alpha-helix.",
    }


# =====================================================
# Signal peptide detection (SignalP-like)
# =====================================================

def predict_signal_peptide(sequence: str) -> dict:
    """Detect N-terminal signal peptides (secreted protein indicator)."""
    seq = sequence.upper()
    if len(seq) < 30:
        return {"has_signal": False, "cleavage_site": None, "score": 0.0}

    # Signal peptides typically:
    # - 15-30 residues at N-terminus
    # - Hydrophobic core (h-region)
    # - Charged N-terminus (n-region)
    # - Polar C-terminus with small residue at -3, -1 from cleavage

    n_region = seq[:5]
    h_region = seq[5:20]
    c_region = seq[20:30]

    n_charge = sum(1 for a in n_region if a in "KR") - sum(1 for a in n_region if a in "DE")
    h_hydro = sum(KD_HYDROPATHY.get(a, 0) for a in h_region) / max(len(h_region), 1)
    c_polar = sum(1 for a in c_region if a in "STNQGAVL") / max(len(c_region), 1)

    score = 0.0
    if n_charge >= 1:
        score += 0.3
    if h_hydro > 1.5:
        score += 0.4
    if c_polar > 0.5:
        score += 0.3

    has_signal = score >= 0.5

    # Find best cleavage site (usually after small residue like A, G, S, C, T)
    cleavage = None
    if has_signal:
        for i in range(15, min(30, len(seq))):
            if seq[i - 1] in "AGSCT" and seq[i] not in "AGSCT":
                cleavage = i
                break

    return {
        "has_signal": has_signal,
        "score": round(score, 2),
        "cleavage_site": cleavage,
        "mature_sequence": seq[cleavage:] if cleavage else None,
        "note": "SignalP-like heuristic. Real prediction needs neural network models.",
    }


# =====================================================
# Aggregation prediction (TANGO-like)
# =====================================================

# Aggregation propensity (Pawar et al. simplified)
AGG_PROPENSITY = {
    "I": 1.82, "F": 1.75, "V": 1.55, "L": 1.41, "Y": 1.16, "W": 1.04,
    "M": 0.91, "C": 0.87, "A": 0.50, "T": 0.40, "S": 0.30, "G": 0.27,
    "H": 0.10, "Q": -0.30, "N": -0.40, "P": -0.50, "K": -1.50, "R": -1.55,
    "D": -1.85, "E": -1.95,
}


def predict_aggregation(sequence: str, window: int = 5, threshold: float = 1.0) -> dict:
    """Predict aggregation-prone regions (APRs) - TANGO/Aggrescan-like."""
    seq = sequence.upper()
    n = len(seq)
    half = window // 2

    scores = []
    for i in range(n):
        chunk = seq[max(0, i - half):min(n, i + half + 1)]
        score = sum(AGG_PROPENSITY.get(a, 0) for a in chunk) / len(chunk)
        scores.append(score)

    regions = []
    in_region = False
    start = 0
    for i, s in enumerate(scores):
        if s >= threshold and not in_region:
            in_region = True
            start = i
        elif s < threshold and in_region:
            if i - start >= 5:
                regions.append({
                    "start": start + 1,
                    "end": i,
                    "length": i - start,
                    "sequence": seq[start:i],
                })
            in_region = False
    if in_region and n - start >= 5:
        regions.append({
            "start": start + 1,
            "end": n,
            "length": n - start,
            "sequence": seq[start:n],
        })

    overall = sum(max(0, s) for s in scores) / max(n, 1)

    return {
        "scores": [round(s, 3) for s in scores],
        "aggregation_prone_regions": regions,
        "n_apr": len(regions),
        "overall_aggregation_score": round(overall, 3),
        "risk_level": "high" if overall > 0.5 else ("medium" if overall > 0.2 else "low"),
        "note": "TANGO/Aggrescan-like heuristic.",
    }


# =====================================================
# Phosphorylation sites
# =====================================================

def predict_phosphorylation(sequence: str) -> dict:
    """Predict phosphorylation sites by motif matching (NetPhos-like)."""
    seq = sequence.upper()
    sites = []

    # Common kinase consensus motifs
    motifs = {
        "PKA": r"R[RK].[ST]",  # Protein kinase A
        "PKC": r"[ST].[RK]",   # Protein kinase C
        "CK2": r"[ST]..[DE]",   # Casein kinase 2
        "CDK": r"[ST]P.[KR]",   # Cyclin-dependent kinase
        "GSK3": r"[ST]...[ST]", # Glycogen synthase kinase 3
        "MAPK": r"P.[ST]P",    # MAP kinase
    }

    for kinase, pattern in motifs.items():
        for m in re.finditer(pattern, seq):
            # Find S/T position within match
            for j, c in enumerate(m.group()):
                if c in "ST":
                    pos = m.start() + j + 1
                    sites.append({
                        "position": pos,
                        "residue": c,
                        "kinase": kinase,
                        "context": seq[max(0, pos - 4):min(len(seq), pos + 3)],
                    })
                    break

    return {
        "sites": sites,
        "count": len(sites),
        "note": "Motif-based prediction. Real prediction uses ML models like NetPhos.",
    }


# =====================================================
# Glycosylation sites
# =====================================================

def predict_glycosylation(sequence: str) -> dict:
    """Predict N-glycosylation (Asn-X-Ser/Thr where X is not Pro) and O-glycosylation."""
    seq = sequence.upper()
    n_sites = []
    o_sites = []

    # N-glycosylation: N-X-S/T (X != P)
    for m in re.finditer(r"N[^P][ST]", seq):
        n_sites.append({
            "position": m.start() + 1,
            "context": m.group(),
            "type": "N-linked",
        })

    # O-glycosylation: roughly any S/T in mucin-like regions (simplified)
    for i, c in enumerate(seq):
        if c in "ST":
            window = seq[max(0, i - 3):min(len(seq), i + 4)]
            if window.count("S") + window.count("T") + window.count("P") >= 4:
                o_sites.append({
                    "position": i + 1,
                    "residue": c,
                    "type": "O-linked",
                })

    return {
        "n_glycosylation_sites": n_sites,
        "o_glycosylation_sites": o_sites[:20],  # cap
        "n_count": len(n_sites),
        "o_count": len(o_sites),
        "note": "Sequon-based prediction (NXS/T for N-linked).",
    }


# =====================================================
# Stability change (DDG) prediction
# =====================================================

# Mutation-induced stability change values (rough averages from FoldX studies)
DDG_TO_AA = {
    "A": -0.5, "G": -1.5, "P": -1.8, "C": -0.3,
    "S": -0.4, "T": -0.2, "V": 0.3, "I": 0.5,
    "L": 0.4, "M": 0.2, "F": 0.6, "W": 0.8,
    "Y": 0.4, "H": -0.1, "K": -0.6, "R": -0.4,
    "D": -0.7, "E": -0.6, "N": -0.5, "Q": -0.3,
}

DDG_FROM_AA = {k: -v for k, v in DDG_TO_AA.items()}


def predict_ddg(sequence: str, mutation: str) -> dict:
    """Estimate the stability change (ΔΔG) of a point mutation.

    Returns kcal/mol. Negative = destabilizing, positive = stabilizing.
    Very rough heuristic - real prediction needs FoldX/Rosetta/ProTSTaB.
    """
    m = re.match(r"^([A-Z])(\d+)([A-Z])$", mutation.upper().strip())
    if not m:
        return {"error": "Invalid mutation format. Use e.g. K48R"}

    from_aa, pos_str, to_aa = m.groups()
    pos = int(pos_str) - 1
    seq = sequence.upper()
    if pos >= len(seq):
        return {"error": "Position out of range"}
    if seq[pos] != from_aa:
        return {"error": f"Position {pos+1} is {seq[pos]}, not {from_aa}"}

    # Heuristic ΔΔG: difference in propensity scores
    ddg = DDG_TO_AA.get(to_aa, 0) - DDG_TO_AA.get(from_aa, 0)

    # Penalty for conservative vs radical
    same_class = (
        (from_aa in "AILMFWV" and to_aa in "AILMFWV") or  # both hydrophobic
        (from_aa in "DE" and to_aa in "DE") or  # both negative
        (from_aa in "KR" and to_aa in "KR") or  # both positive
        (from_aa in "STNQ" and to_aa in "STNQ")  # both polar
    )
    if not same_class:
        ddg -= 0.5  # radical change destabilizes more

    classification = (
        "highly stabilizing" if ddg > 1.0 else
        "stabilizing" if ddg > 0.3 else
        "neutral" if ddg > -0.3 else
        "destabilizing" if ddg > -1.0 else
        "highly destabilizing"
    )

    return {
        "mutation": mutation.upper(),
        "ddg_kcal_mol": round(ddg, 2),
        "classification": classification,
        "interpretation": (
            f"Mutating {from_aa} at position {pos + 1} to {to_aa} is predicted to be "
            f"{classification} (ΔΔG ≈ {ddg:+.2f} kcal/mol). "
            "Negative values suggest destabilization; positive values suggest stabilization."
        ),
        "note": "Heuristic prediction. Real ΔΔG requires FoldX, Rosetta, or trained ML models.",
    }
