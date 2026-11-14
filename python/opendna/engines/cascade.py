"""Multi-fidelity folding cascade.

Tries progressively more expensive structure predictors until a confidence
target is met. Cheap tiers run first so callers get something instantly and
only pay for heavy models when necessary.

Tier 0: Chou-Fasman secondary structure (instant, no 3D)
Tier 1: ESMFold single-sequence fold
Tier 2: ColabFold (if installed, monomers/multimers under 400 aa)
Tier 3: Boltz (multimers only, requires ':' in sequence)
"""

from __future__ import annotations

from typing import Callable, Optional

# Chou-Fasman alpha-helix and beta-sheet propensities (>1.0 favors the state)
_ALPHA = {
    "E": 1.53, "A": 1.45, "L": 1.34, "H": 1.24, "M": 1.20, "Q": 1.17,
    "W": 1.14, "V": 1.14, "F": 1.12, "K": 1.07, "I": 1.00, "D": 0.98,
    "T": 0.82, "S": 0.79, "R": 0.79, "C": 0.77, "N": 0.73, "Y": 0.61,
    "P": 0.59, "G": 0.53,
}
_BETA = {
    "V": 1.65, "I": 1.60, "Y": 1.29, "F": 1.28, "W": 1.19, "L": 1.22,
    "C": 1.30, "T": 1.20, "Q": 1.23, "M": 1.05, "R": 0.90, "N": 0.65,
    "H": 0.71, "A": 0.97, "S": 0.72, "G": 0.81, "K": 0.74, "P": 0.62,
    "D": 0.80, "E": 0.26,
}


def _chou_fasman(sequence: str) -> dict:
    """Assign H/E/C per residue by propensity; return ss string + stats."""
    clean = "".join(c for c in sequence.upper() if c.isalpha() and c != ":")
    ss = []
    for aa in clean:
        a = _ALPHA.get(aa, 1.0)
        b = _BETA.get(aa, 1.0)
        if a > b and a > 1.0:
            ss.append("H")
        elif b > a and b > 1.0:
            ss.append("E")
        else:
            ss.append("C")
    ss_str = "".join(ss)
    return {
        "ss": ss_str,
        "helix_frac": ss_str.count("H") / max(len(ss_str), 1),
        "sheet_frac": ss_str.count("E") / max(len(ss_str), 1),
        "coil_frac": ss_str.count("C") / max(len(ss_str), 1),
    }


def fold_cascade(
    sequence: str,
    target_confidence: float = 70,
    on_progress: Optional[Callable[[str, float], None]] = None,
) -> dict:
    """Run a multi-tier folding cascade until target confidence is met.

    Args:
        sequence: Protein sequence (use ':' to separate chains for multimers).
        target_confidence: Mean pLDDT threshold (0-100). Stops cascade once met.
        on_progress: Optional callback(stage, fraction).

    Returns:
        dict with keys: tier_used, pdb, confidence, tiers_attempted, reason.
    """
    def _p(stage: str, frac: float) -> None:
        if on_progress:
            try:
                on_progress(stage, frac)
            except Exception:
                pass

    tiers_attempted: list[str] = []
    is_multimer = ":" in sequence
    single_seq = sequence.replace(":", "")
    seq_len = len(single_seq)

    # Tier 0: Chou-Fasman (always runs, gives instant feedback)
    _p("tier0_chou_fasman", 0.05)
    ss_info = _chou_fasman(sequence)
    tiers_attempted.append("chou_fasman")
    result = {
        "tier_used": "chou_fasman",
        "pdb": None,
        "confidence": 0.0,
        "secondary_structure": ss_info,
        "tiers_attempted": list(tiers_attempted),
        "reason": "tier0_only",
    }

    # Tier 1: ESMFold
    _p("tier1_esmfold", 0.15)
    try:
        from opendna.engines.folding import fold as _fold
        fr = _fold(sequence.replace(":", ""), method="esmfold",
                   on_progress=lambda s, f: _p(f"esmfold:{s}", 0.15 + 0.5 * f))
        tiers_attempted.append("esmfold")
        mean_conf = float(getattr(fr, "mean_confidence", 0.0) or 0.0)
        pdb_str = fr.pdb_string if hasattr(fr, "pdb_string") else None
        result.update({
            "tier_used": "esmfold",
            "pdb": pdb_str,
            "confidence": mean_conf,
            "tiers_attempted": list(tiers_attempted),
            "reason": "esmfold_ok" if mean_conf >= target_confidence else "esmfold_below_target",
        })
        if mean_conf >= target_confidence:
            _p("done", 1.0)
            return result
    except Exception as e:
        tiers_attempted.append("esmfold_failed")
        result["reason"] = f"esmfold_error: {type(e).__name__}: {e}"

    # Tier 2: ColabFold (if short enough and installed)
    if seq_len < 400:
        _p("tier2_colabfold", 0.7)
        try:
            from opendna.engines.real_models import colabfold_multimer, NotInstalledError
            try:
                cf = colabfold_multimer([sequence] if is_multimer else [single_seq])
                tiers_attempted.append("colabfold")
                cf_conf = float(cf.get("confidence", cf.get("mean_plddt", 0.0)) or 0.0) if isinstance(cf, dict) else 0.0
                cf_pdb = cf.get("pdb") if isinstance(cf, dict) else None
                if cf_pdb:
                    result.update({
                        "tier_used": "colabfold",
                        "pdb": cf_pdb,
                        "confidence": cf_conf,
                        "tiers_attempted": list(tiers_attempted),
                        "reason": "colabfold_ok" if cf_conf >= target_confidence else "colabfold_below_target",
                    })
                    if cf_conf >= target_confidence:
                        _p("done", 1.0)
                        return result
            except NotInstalledError as e:
                tiers_attempted.append("colabfold_unavailable")
                result["reason"] = f"colabfold_unavailable: {e}"
        except Exception as e:
            tiers_attempted.append("colabfold_failed")
            result["reason"] = f"colabfold_error: {type(e).__name__}: {e}"
    else:
        tiers_attempted.append("colabfold_skipped_length")

    # Tier 3: Boltz (multimers)
    if is_multimer:
        _p("tier3_boltz", 0.85)
        try:
            from opendna.engines.real_models import boltz_multimer, NotInstalledError
            try:
                bz = boltz_multimer(sequence.split(":"))
                tiers_attempted.append("boltz")
                bz_conf = float(bz.get("confidence", bz.get("mean_plddt", 0.0)) or 0.0) if isinstance(bz, dict) else 0.0
                bz_pdb = bz.get("pdb") if isinstance(bz, dict) else None
                if bz_pdb:
                    result.update({
                        "tier_used": "boltz",
                        "pdb": bz_pdb,
                        "confidence": bz_conf,
                        "tiers_attempted": list(tiers_attempted),
                        "reason": "boltz_ok" if bz_conf >= target_confidence else "boltz_below_target",
                    })
            except NotInstalledError as e:
                tiers_attempted.append("boltz_unavailable")
                result["reason"] = f"boltz_unavailable: {e}"
        except Exception as e:
            tiers_attempted.append("boltz_failed")
            result["reason"] = f"boltz_error: {type(e).__name__}: {e}"
    else:
        tiers_attempted.append("boltz_skipped_monomer")

    result["tiers_attempted"] = list(tiers_attempted)
    _p("done", 1.0)
    return result
