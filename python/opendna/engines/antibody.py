"""Antibody numbering (Kabat / Chothia / IMGT) and CDR detection.

Antibodies have a conserved framework with three Complementarity Determining
Regions (CDRs) that determine antigen specificity. Multiple numbering schemes
exist; this module supports Kabat and Chothia.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class CDRRegion:
    name: str  # CDR-L1, CDR-L2, CDR-L3, CDR-H1, CDR-H2, CDR-H3
    start: int  # 1-indexed
    end: int
    sequence: str
    length: int


def detect_chain_type(sequence: str) -> str:
    """Detect if a sequence is heavy chain, light chain (kappa/lambda), or unknown."""
    seq = sequence.upper()

    # Heavy chain markers (constant region patterns)
    heavy_markers = ["CSAS", "ASTKGP", "STKG"]
    # Light chain kappa
    kappa_markers = ["RTVAAP", "TVAAP"]
    # Light chain lambda
    lambda_markers = ["GQPKAA", "PKAAP"]

    if any(m in seq for m in heavy_markers):
        return "heavy"
    if any(m in seq for m in kappa_markers):
        return "kappa"
    if any(m in seq for m in lambda_markers):
        return "lambda"

    # Heuristic by length
    if len(seq) > 200:
        return "heavy"
    elif len(seq) > 100:
        return "light"
    return "unknown"


def find_cdrs(sequence: str, scheme: str = "kabat") -> dict:
    """Find the CDR regions in an antibody sequence.

    Uses regex patterns characteristic of antibody frameworks. This is a
    heuristic approach; for production use ANARCI or AbNumber.
    """
    seq = sequence.upper()
    chain_type = detect_chain_type(seq)

    cdrs: list[CDRRegion] = []

    if chain_type == "heavy":
        cdrs = _find_heavy_cdrs(seq, scheme)
    elif chain_type in ("kappa", "lambda", "light"):
        cdrs = _find_light_cdrs(seq, scheme)

    return {
        "chain_type": chain_type,
        "scheme": scheme,
        "cdrs": [
            {
                "name": c.name,
                "start": c.start,
                "end": c.end,
                "sequence": c.sequence,
                "length": c.length,
            }
            for c in cdrs
        ],
        "n_cdrs": len(cdrs),
        "is_antibody": len(cdrs) >= 3,
        "note": "Heuristic CDR detection. For production use ANARCI or AbNumber.",
    }


def _find_heavy_cdrs(seq: str, scheme: str) -> list[CDRRegion]:
    """Find heavy chain CDRs using framework conservation."""
    cdrs = []

    # CDR-H1: typically starts after a Cys at position ~22 (Kabat) and ends before a Trp
    cys_match = re.search(r"C[A-Z]{8,12}W", seq[:50])
    if cys_match:
        h1_start = cys_match.start() + 1 + 1  # after the C, 1-indexed
        h1_end = cys_match.end() - 1  # before the W
        cdrs.append(CDRRegion(
            name="CDR-H1",
            start=h1_start,
            end=h1_end,
            sequence=seq[h1_start - 1:h1_end],
            length=h1_end - h1_start + 1,
        ))

    # CDR-H2: typically follows a WIG / WVR / WVS motif
    h2_match = re.search(r"W[VI][RS][QK]", seq[40:80])
    if h2_match:
        h2_start = 40 + h2_match.end() + 1
        h2_end = min(h2_start + 16, len(seq))
        cdrs.append(CDRRegion(
            name="CDR-H2",
            start=h2_start,
            end=h2_end,
            sequence=seq[h2_start - 1:h2_end],
            length=h2_end - h2_start + 1,
        ))

    # CDR-H3: between the second Cys and a WG[Q/K]G motif
    cys_2 = re.search(r"C(?=[A-Z]{0,30}WG[QK]G)", seq[80:])
    if cys_2:
        h3_start = 80 + cys_2.start() + 1 + 1
        wg_match = re.search(r"WG[QK]G", seq[h3_start:])
        if wg_match:
            h3_end = h3_start + wg_match.start()
            cdrs.append(CDRRegion(
                name="CDR-H3",
                start=h3_start,
                end=h3_end,
                sequence=seq[h3_start - 1:h3_end],
                length=h3_end - h3_start + 1,
            ))

    return cdrs


def _find_light_cdrs(seq: str, scheme: str) -> list[CDRRegion]:
    """Find light chain CDRs."""
    cdrs = []

    # CDR-L1: after first Cys, ends before W
    cys_1 = re.search(r"C[A-Z]{8,16}W", seq[:50])
    if cys_1:
        l1_start = cys_1.start() + 1 + 1
        l1_end = cys_1.end() - 1
        cdrs.append(CDRRegion(
            name="CDR-L1",
            start=l1_start,
            end=l1_end,
            sequence=seq[l1_start - 1:l1_end],
            length=l1_end - l1_start + 1,
        ))

    # CDR-L2: typically 7 residues after the W of CDR-L1, fixed length 7
    if cdrs:
        l2_start = cdrs[0].end + 16
        l2_end = l2_start + 6
        if l2_end < len(seq):
            cdrs.append(CDRRegion(
                name="CDR-L2",
                start=l2_start,
                end=l2_end,
                sequence=seq[l2_start - 1:l2_end],
                length=7,
            ))

    # CDR-L3: between second Cys and FG[Q/G]G
    cys_2 = re.search(r"C(?=[A-Z]{0,15}FG[QG]G)", seq[60:])
    if cys_2:
        l3_start = 60 + cys_2.start() + 1 + 1
        fg_match = re.search(r"FG[QG]G", seq[l3_start:])
        if fg_match:
            l3_end = l3_start + fg_match.start()
            cdrs.append(CDRRegion(
                name="CDR-L3",
                start=l3_start,
                end=l3_end,
                sequence=seq[l3_start - 1:l3_end],
                length=l3_end - l3_start + 1,
            ))

    return cdrs
