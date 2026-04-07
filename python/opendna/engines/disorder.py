"""Intrinsic disorder prediction (IUPred-style heuristic)."""

from __future__ import annotations

# Disorder propensity scale (Linding et al., simplified)
DISORDER_PROPENSITY = {
    "A": 0.06, "R": 0.18, "N": 0.01, "D": 0.19, "C": -0.02,
    "E": 0.74, "Q": 0.32, "G": 0.17, "H": 0.30, "I": -0.49,
    "L": -0.33, "K": 0.59, "M": -0.40, "F": -0.70, "P": 0.99,
    "S": 0.34, "T": 0.06, "W": -0.88, "Y": -0.45, "V": -0.39,
}


def predict_disorder(sequence: str, window: int = 21) -> dict:
    """Predict intrinsic disorder regions in a protein sequence.

    Returns per-residue disorder probability and identified disordered regions.
    """
    seq = sequence.upper()
    n = len(seq)
    half = window // 2

    raw = []
    for i in range(n):
        start = max(0, i - half)
        end = min(n, i + half + 1)
        chunk = seq[start:end]
        score = sum(DISORDER_PROPENSITY.get(a, 0) for a in chunk) / len(chunk)
        # Sigmoid normalize to 0-1
        prob = 1.0 / (1.0 + 2.71828 ** (-3 * score))
        raw.append(prob)

    # Find continuous disordered regions (>= 0.5 for >= 5 residues)
    regions = []
    in_region = False
    start = 0
    for i, p in enumerate(raw):
        if p >= 0.5 and not in_region:
            in_region = True
            start = i
        elif p < 0.5 and in_region:
            if i - start >= 5:
                regions.append({"start": start + 1, "end": i, "length": i - start})
            in_region = False
    if in_region and n - start >= 5:
        regions.append({"start": start + 1, "end": n, "length": n - start})

    disorder_pct = sum(1 for p in raw if p >= 0.5) / max(n, 1) * 100

    return {
        "scores": [round(p, 3) for p in raw],
        "regions": regions,
        "disorder_percent": round(disorder_pct, 1),
        "is_mostly_disordered": disorder_pct > 30,
    }
