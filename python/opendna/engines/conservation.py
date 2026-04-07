"""Per-residue conservation analysis using ESM language model perplexity.

For each position in the sequence, mask it and ask the ESM model what amino
acid it would predict. The probability of the actual amino acid is a measure
of conservation:
- High probability = the model is confident this residue belongs here = conserved
- Low probability = surprising = variable

This is the Frazer et al. (2021) "EVE" approach simplified.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConservationResult:
    scores: list[float]  # Per-residue conservation 0-1
    most_conserved: list[int]  # Top 10 positions
    most_variable: list[int]  # Top 10 positions
    method: str
    note: str


def analyze_conservation(sequence: str) -> ConservationResult:
    """Compute per-residue conservation using ESM perplexity.

    Returns a per-residue score (0-1) where 1 = highly conserved.
    """
    try:
        return _esm_conservation(sequence)
    except Exception as e:
        logger.warning(f"ESM conservation failed: {e}, using composition-based fallback")
        return _composition_conservation(sequence)


def _esm_conservation(sequence: str) -> ConservationResult:
    """Use ESM language model perplexity for conservation."""
    import torch
    import esm

    # Use ESM-2 8M for speed (already loaded if user has used folding)
    model, alphabet = esm.pretrained.esm2_t6_8M_UR50D()
    model.eval()
    batch_converter = alphabet.get_batch_converter()

    seq = sequence.upper()
    n = len(seq)
    if n > 1024:
        seq = seq[:1024]
        n = 1024

    # One forward pass per position with that position masked
    # For efficiency we mask all positions in batches
    scores = [0.0] * n
    batch_size = 16

    for start in range(0, n, batch_size):
        end = min(n, start + batch_size)
        batch_data = []
        for pos in range(start, end):
            masked = seq[:pos] + "<mask>" + seq[pos + 1:]
            batch_data.append((f"seq_{pos}", masked))

        _, _, batch_tokens = batch_converter(batch_data)

        with torch.no_grad():
            out = model(batch_tokens, repr_layers=[6])
            logits = out["logits"]  # [batch, seq_len, vocab]

        # For each item in batch, get the probability of the true amino acid at the masked position
        for i, pos in enumerate(range(start, end)):
            true_aa = seq[pos]
            true_idx = alphabet.get_idx(true_aa)
            # +1 because ESM tokenization adds <cls> at position 0
            mask_pos = pos + 1
            probs = torch.softmax(logits[i, mask_pos], dim=-1)
            scores[pos] = probs[true_idx].item()

    # Sort to find most conserved/variable
    indexed = [(i, s) for i, s in enumerate(scores)]
    indexed_by_conservation = sorted(indexed, key=lambda x: -x[1])
    most_conserved = [i + 1 for i, _ in indexed_by_conservation[:10]]
    most_variable = [i + 1 for i, _ in indexed_by_conservation[-10:]]

    return ConservationResult(
        scores=[round(s, 4) for s in scores],
        most_conserved=most_conserved,
        most_variable=most_variable,
        method="esm-2-8m-perplexity",
        note="Per-residue probability from ESM-2. Higher = more conserved evolutionarily.",
    )


def _composition_conservation(sequence: str) -> ConservationResult:
    """Fallback: use amino acid abundance as a proxy for conservation."""
    # Rare amino acids tend to be functional/conserved (W, C, M, H)
    rarity = {
        "A": 0.3, "R": 0.4, "N": 0.4, "D": 0.4, "C": 0.7, "E": 0.4, "Q": 0.4,
        "G": 0.3, "H": 0.6, "I": 0.4, "L": 0.3, "K": 0.4, "M": 0.7, "F": 0.5,
        "P": 0.4, "S": 0.3, "T": 0.4, "W": 0.8, "Y": 0.5, "V": 0.4,
    }
    seq = sequence.upper()
    scores = [rarity.get(a, 0.5) for a in seq]

    indexed = [(i, s) for i, s in enumerate(scores)]
    indexed_by_conservation = sorted(indexed, key=lambda x: -x[1])
    most_conserved = [i + 1 for i, _ in indexed_by_conservation[:10]]
    most_variable = [i + 1 for i, _ in indexed_by_conservation[-10:]]

    return ConservationResult(
        scores=scores,
        most_conserved=most_conserved,
        most_variable=most_variable,
        method="composition-fallback",
        note="Composition-based heuristic. Install ESM for real perplexity-based scoring.",
    )
