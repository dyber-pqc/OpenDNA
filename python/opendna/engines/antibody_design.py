"""Antibody numbering, humanization and immunogenicity heuristics.

These are lightweight approximations intended for exploratory work. For
production antibody engineering use ANARCI / AbNumber / NetMHC-class tools.
"""

from __future__ import annotations

import re
from typing import Dict, List

# ---------------------------------------------------------------------------
# Hardcoded human germline framework sequences (VH / VK)
# ---------------------------------------------------------------------------
HUMAN_GERMLINES: Dict[str, str] = {
    # IGHV1-46 (heavy, typical VH framework)
    "IGHV1-46": (
        "QVQLVQSGAEVKKPGASVKVSCKASGYTFTSYYMHWVRQAPGQGLEWMGIINPSGGSTSYAQ"
        "KFQGRVTMTRDTSTSTVYMELSSLRSEDTAVYYCAR"
    ),
    # IGHV3-23 (heavy, very common)
    "IGHV3-23": (
        "EVQLLESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYAD"
        "SVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAK"
    ),
    # IGKV1-39 (kappa light, common)
    "IGKV1-39": (
        "DIQMTQSPSSLSASVGDRVTITCRASQSISSYLNWYQQKPGKAPKLLIYAASSLQSGVPSRF"
        "SGSGSGTDFTLTISSLQPEDFATYYC"
    ),
}

# Tiny hardcoded set of "immunogenic" 9-mer motifs (illustrative only).
IMMUNOGENIC_MOTIFS: List[str] = [
    "YMFPGPVTA",
    "FLPSDFFPS",
    "ILKEPVHGV",
    "GILGFVFTL",
    "NLVPMVATV",
    "GLCTLVAML",
    "KAFSPEVIP",
    "LLFGYPVYV",
    "RLLQETELV",
    "SLYNTVATL",
]


# ---------------------------------------------------------------------------
# Numbering
# ---------------------------------------------------------------------------
def number_antibody(sequence: str, scheme: str = "kabat") -> dict:
    """Identify framework / CDR regions of a VH or VL sequence.

    Uses the existing :mod:`opendna.engines.antibody` CDR finder if available
    and augments its output with framework regions so the whole sequence is
    covered. Returns a dict with ``scheme`` and ``regions``.
    """
    seq = (sequence or "").strip().upper()
    if not seq:
        return {"scheme": scheme, "regions": [], "error": "empty sequence"}

    cdrs: List[dict] = []
    chain_type = "unknown"
    try:
        from opendna.engines.antibody import find_cdrs  # type: ignore

        parsed = find_cdrs(seq, scheme=scheme)
        cdrs = parsed.get("cdrs", [])
        chain_type = parsed.get("chain_type", "unknown")
    except Exception:
        cdrs = _fallback_cdrs(seq)

    # Sort CDRs by start and stitch in framework regions.
    cdrs = sorted(cdrs, key=lambda c: c.get("start", 0))
    regions: List[dict] = []
    cursor = 1
    fw_idx = 1
    for cdr in cdrs:
        start = int(cdr.get("start", 0))
        end = int(cdr.get("end", 0))
        if start > cursor:
            regions.append(
                {
                    "name": f"FR{fw_idx}",
                    "start": cursor,
                    "end": start - 1,
                    "residues": seq[cursor - 1 : start - 1],
                }
            )
            fw_idx += 1
        regions.append(
            {
                "name": cdr.get("name", f"CDR{len(regions) + 1}"),
                "start": start,
                "end": end,
                "residues": cdr.get("sequence", seq[start - 1 : end]),
            }
        )
        cursor = end + 1
    if cursor <= len(seq):
        regions.append(
            {
                "name": f"FR{fw_idx}",
                "start": cursor,
                "end": len(seq),
                "residues": seq[cursor - 1 :],
            }
        )

    return {
        "scheme": scheme,
        "chain_type": chain_type,
        "length": len(seq),
        "regions": regions,
        "n_cdrs": sum(1 for r in regions if r["name"].startswith("CDR")),
    }


def _fallback_cdrs(seq: str) -> List[dict]:
    """Very simple CDR detector anchored on conserved C/W/F residues."""
    cdrs: List[dict] = []
    c1 = re.search(r"C", seq[:40])
    w1 = re.search(r"W", seq[30:70])
    if c1 and w1:
        s = c1.start() + 2
        e = 30 + w1.start()
        if e > s:
            cdrs.append({"name": "CDR1", "start": s, "end": e, "sequence": seq[s - 1 : e]})
    # CDR2: arbitrary 17 residues after CDR1
    if cdrs:
        s = cdrs[-1]["end"] + 15
        e = min(s + 16, len(seq))
        if e > s:
            cdrs.append({"name": "CDR2", "start": s, "end": e, "sequence": seq[s - 1 : e]})
    c2 = re.search(r"C(?=[A-Z]{3,25}[WF]G[QKG]G)", seq[70:])
    if c2:
        s = 70 + c2.start() + 2
        m = re.search(r"[WF]G[QKG]G", seq[s:])
        if m:
            e = s + m.start()
            cdrs.append({"name": "CDR3", "start": s, "end": e, "sequence": seq[s - 1 : e]})
    return cdrs


# ---------------------------------------------------------------------------
# Humanization (CDR grafting)
# ---------------------------------------------------------------------------
def _identity(a: str, b: str) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    matches = sum(1 for i in range(n) if a[i] == b[i])
    return matches / n


def humanize(sequence: str, target_germline: str = "IGHV1-46") -> dict:
    """Graft the parent CDRs onto a human germline framework.

    The result is not a validated therapeutic candidate; it is a toy graft
    that preserves CDR residues and replaces the frameworks with the chosen
    germline's framework sequence.
    """
    parent = (sequence or "").strip().upper()
    if not parent:
        return {"error": "empty sequence", "humanized": "", "identity": 0.0}

    # Pick nearest germline if the requested one doesn't exist.
    if target_germline not in HUMAN_GERMLINES:
        best = max(
            HUMAN_GERMLINES.keys(),
            key=lambda k: _identity(parent, HUMAN_GERMLINES[k]),
        )
        target_germline = best
    framework = HUMAN_GERMLINES[target_germline]

    parent_regions = number_antibody(parent).get("regions", [])
    grafted_chunks: List[str] = []
    fw_cursor = 0
    for region in parent_regions:
        if region["name"].startswith("CDR"):
            grafted_chunks.append(region["residues"])
        else:
            span = region["end"] - region["start"] + 1
            chunk = framework[fw_cursor : fw_cursor + span]
            if len(chunk) < span:
                # Ran out of germline; pad from the parent to keep length.
                chunk = chunk + region["residues"][len(chunk) :]
            grafted_chunks.append(chunk)
            fw_cursor += span
    grafted = "".join(grafted_chunks) if grafted_chunks else parent

    identity = _identity(parent, grafted)
    human_similarity = _identity(grafted, framework)

    return {
        "target_germline": target_germline,
        "parent": parent,
        "humanized": grafted,
        "identity_to_parent": round(identity, 4),
        "identity_to_germline": round(human_similarity, 4),
        "n_mutations": sum(1 for i in range(min(len(parent), len(grafted))) if parent[i] != grafted[i]),
    }


# ---------------------------------------------------------------------------
# Immunogenicity delta
# ---------------------------------------------------------------------------
def _count_motifs(seq: str) -> int:
    seq = (seq or "").upper()
    total = 0
    for motif in IMMUNOGENIC_MOTIFS:
        # Approximate match: allow 1 mismatch across the 9-mer window.
        L = len(motif)
        for i in range(len(seq) - L + 1):
            window = seq[i : i + L]
            mm = sum(1 for a, b in zip(window, motif) if a != b)
            if mm <= 1:
                total += 1
    return total


def immunogenicity_delta(parent: str, humanized: str) -> float:
    """Return ``parent - humanized`` motif count (positive = improvement)."""
    p = _count_motifs(parent)
    h = _count_motifs(humanized)
    return float(p - h)
