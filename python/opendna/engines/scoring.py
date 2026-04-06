"""Protein scoring and validation engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from opendna.models.protein import Protein, Sequence, Structure


@dataclass
class ScoreBreakdown:
    """Individual scoring components."""

    stability: float = 0.0
    binding: float = 0.0
    solubility: float = 0.0
    immunogenicity: float = 0.0
    developability: float = 0.0
    novelty: float = 0.0


@dataclass
class ScoreResult:
    """Composite protein evaluation result."""

    overall: float
    breakdown: ScoreBreakdown
    summary: str
    recommendations: list[str]
    confidence: float

    def __repr__(self) -> str:
        return f"ScoreResult(overall={self.overall:.2f}, confidence={self.confidence:.2f})"


def evaluate(
    protein: Protein | str | Sequence,
    structure: Optional[Structure] = None,
) -> ScoreResult:
    """Evaluate a protein's quality with a composite score.

    Args:
        protein: Protein object, sequence string, or Sequence object.
        structure: Optional pre-computed structure.

    Returns:
        ScoreResult with overall score, breakdown, and recommendations.
    """
    if isinstance(protein, str):
        protein = Protein(name="query", sequence=protein)
    elif isinstance(protein, Sequence):
        protein = Protein(name="query", sequence=protein.residues)

    if structure is None:
        structure = protein.structure

    breakdown = _compute_scores(protein, structure)
    overall = _compute_overall(breakdown)
    confidence = _estimate_confidence(protein, structure)
    summary = _generate_summary(overall, breakdown, protein)
    recommendations = _generate_recommendations(breakdown, protein)

    return ScoreResult(
        overall=overall,
        breakdown=breakdown,
        summary=summary,
        recommendations=recommendations,
        confidence=confidence,
    )


def _compute_scores(protein: Protein, structure: Optional[Structure]) -> ScoreBreakdown:
    """Compute individual quality scores."""
    seq = str(protein.sequence)
    breakdown = ScoreBreakdown()

    # Stability estimate from sequence composition
    breakdown.stability = _estimate_stability(seq)

    # Solubility estimate
    breakdown.solubility = _estimate_solubility(seq)

    # Immunogenicity (lower is better, we invert for scoring)
    breakdown.immunogenicity = 1.0 - _estimate_immunogenicity(seq)

    # Developability
    breakdown.developability = _estimate_developability(seq)

    # Novelty (how different from known sequences)
    breakdown.novelty = _estimate_novelty(seq)

    # Structure-based scores
    if structure and structure.confidence:
        mean_conf = structure.mean_confidence or 0.0
        breakdown.stability = max(breakdown.stability, mean_conf)

    return breakdown


def _compute_overall(breakdown: ScoreBreakdown) -> float:
    """Compute weighted overall score."""
    weights = {
        "stability": 0.25,
        "solubility": 0.20,
        "immunogenicity": 0.20,
        "developability": 0.20,
        "novelty": 0.05,
        "binding": 0.10,
    }
    total = sum(
        getattr(breakdown, k) * v for k, v in weights.items()
    )
    return min(1.0, max(0.0, total))


def _estimate_confidence(protein: Protein, structure: Optional[Structure]) -> float:
    """Estimate how confident we are in the scores."""
    confidence = 0.3  # Base confidence for sequence-only
    if structure:
        confidence = 0.6
        if structure.confidence:
            confidence = 0.8
    return confidence


def _estimate_stability(seq: str) -> float:
    """Simple stability estimate based on amino acid composition."""
    # Hydrophobic residues contribute to core packing
    hydrophobic = set("AILMFWV")
    hydro_frac = sum(1 for c in seq if c in hydrophobic) / len(seq)

    # Charged residues on surface
    charged = set("DEKR")
    charge_frac = sum(1 for c in seq if c in charged) / len(seq)

    # Cysteines can form disulfide bonds
    cys_frac = seq.count("C") / len(seq)

    # Prolines in loops
    pro_frac = seq.count("P") / len(seq)

    score = 0.5
    if 0.25 < hydro_frac < 0.45:
        score += 0.2
    if 0.15 < charge_frac < 0.35:
        score += 0.1
    if cys_frac > 0:
        score += 0.05
    if pro_frac < 0.10:
        score += 0.05

    return min(1.0, score)


def _estimate_solubility(seq: str) -> float:
    """Estimate solubility from sequence."""
    # High charge and low hydrophobicity = more soluble
    charged = set("DEKR")
    hydrophobic = set("AILMFWV")

    charge_frac = sum(1 for c in seq if c in charged) / len(seq)
    hydro_frac = sum(1 for c in seq if c in hydrophobic) / len(seq)

    score = 0.5
    if charge_frac > 0.2:
        score += 0.2
    if hydro_frac < 0.35:
        score += 0.2
    if len(seq) < 300:
        score += 0.1

    return min(1.0, score)


def _estimate_immunogenicity(seq: str) -> float:
    """Estimate immunogenicity risk (0=safe, 1=high risk)."""
    # Very rough heuristic - real implementation would use NetMHCpan etc.
    # Longer proteins have more potential epitopes
    length_risk = min(0.5, len(seq) / 1000)

    # Many aromatic residues can be immunogenic
    aromatic = set("FWY")
    aromatic_frac = sum(1 for c in seq if c in aromatic) / len(seq)

    return min(1.0, length_risk + aromatic_frac)


def _estimate_developability(seq: str) -> float:
    """Estimate how easy the protein is to manufacture."""
    score = 0.7

    # Reasonable length
    if len(seq) > 500:
        score -= 0.2
    elif len(seq) < 50:
        score -= 0.1

    # Not too many cysteines (aggregation risk)
    if seq.count("C") / len(seq) > 0.05:
        score -= 0.1

    # Not too many methionines (oxidation risk)
    if seq.count("M") / len(seq) > 0.05:
        score -= 0.1

    return max(0.0, min(1.0, score))


def _estimate_novelty(seq: str) -> float:
    """Estimate how novel the sequence is. Placeholder."""
    # Without a database lookup, we can only estimate based on composition
    return 0.5


def _generate_summary(overall: float, breakdown: ScoreBreakdown, protein: Protein) -> str:
    """Generate a plain-English summary."""
    score_pct = int(overall * 100)

    if overall > 0.8:
        verdict = "looks excellent"
    elif overall > 0.6:
        verdict = "looks promising"
    elif overall > 0.4:
        verdict = "has potential but needs improvement"
    else:
        verdict = "needs significant optimization"

    parts = [f"This protein {verdict} ({score_pct}/100)."]

    # Highlight strengths
    strengths = []
    if breakdown.stability > 0.7:
        strengths.append("good predicted stability")
    if breakdown.solubility > 0.7:
        strengths.append("good solubility")
    if breakdown.immunogenicity > 0.7:
        strengths.append("low immunogenicity risk")

    if strengths:
        parts.append(f"Strengths: {', '.join(strengths)}.")

    # Highlight concerns
    concerns = []
    if breakdown.stability < 0.5:
        concerns.append("stability may be an issue")
    if breakdown.solubility < 0.5:
        concerns.append("solubility could be problematic")
    if breakdown.immunogenicity < 0.5:
        concerns.append("immunogenicity risk is elevated")

    if concerns:
        parts.append(f"Concerns: {', '.join(concerns)}.")

    return " ".join(parts)


def _generate_recommendations(breakdown: ScoreBreakdown, protein: Protein) -> list[str]:
    """Generate actionable recommendations."""
    recs = []

    if breakdown.stability < 0.6:
        recs.append("Consider adding disulfide bonds or salt bridges to improve stability")
    if breakdown.solubility < 0.6:
        recs.append("Try replacing surface hydrophobic residues with charged residues")
    if breakdown.immunogenicity < 0.6:
        recs.append("Screen for T-cell epitopes and consider humanization")
    if breakdown.developability < 0.6:
        recs.append("Optimize for expression by reducing rare codons and aggregation-prone regions")
    if not protein.structure:
        recs.append("Note: this score is sequence-only. Folding the structure provides additional confidence data.")

    if not recs:
        recs.append("Protein looks good! Consider running molecular dynamics for final validation")

    return recs
