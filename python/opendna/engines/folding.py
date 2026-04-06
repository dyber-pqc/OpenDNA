"""Protein structure prediction engine using ESMFold."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from opendna.models.protein import Protein, Sequence, Structure

logger = logging.getLogger(__name__)


@dataclass
class FoldResult:
    """Result of a folding prediction."""

    structure: Structure
    sequence: Sequence
    confidence: list[float]
    mean_confidence: float
    method: str
    explanation: str

    @property
    def pdb_string(self) -> str:
        return self.structure.to_pdb()

    def save(self, path: str | Path) -> None:
        self.structure.save(path)


def fold(
    sequence: str | Sequence,
    method: str = "auto",
    device: str | None = None,
    on_progress: Optional[Callable[[str, float], None]] = None,
) -> FoldResult:
    """Predict the 3D structure of a protein from its sequence.

    Args:
        sequence: Amino acid sequence string or Sequence object.
        method: Folding method ("auto", "esmfold"). Auto selects based on hardware.
        device: PyTorch device ("cuda", "cpu", "mps"). Auto-detected if None.
        on_progress: Optional callback(stage, progress_fraction).

    Returns:
        FoldResult with predicted structure and confidence scores.
    """
    if isinstance(sequence, str):
        sequence = Sequence(sequence)

    if not sequence.is_valid:
        raise ValueError(
            f"Invalid amino acid sequence. "
            f"Must contain only standard amino acids (ACDEFGHIKLMNPQRSTVWY). "
            f"Got: {sequence.residues[:50]}..."
        )

    if on_progress:
        on_progress("Initializing", 0.0)

    if device is None:
        from opendna.hardware.detect import get_torch_device
        device = get_torch_device()

    if method == "auto":
        method = "esmfold"

    if method == "esmfold":
        return _fold_esmfold(sequence, device, on_progress)
    else:
        raise ValueError(f"Unknown folding method: {method}. Available: esmfold")


def _fold_esmfold(
    sequence: Sequence,
    device: str,
    on_progress: Optional[Callable[[str, float], None]] = None,
) -> FoldResult:
    """Fold using ESMFold."""
    import torch

    if on_progress:
        on_progress("Loading ESMFold model", 0.1)

    model = _get_esmfold_model(device)

    if on_progress:
        on_progress("Predicting structure", 0.4)

    with torch.no_grad():
        output = model.infer_pdb(sequence.residues)

    if on_progress:
        on_progress("Processing results", 0.8)

    # Parse the output PDB string
    structure = Structure.from_pdb_string(output)
    structure.pdb_string = output

    # Extract pLDDT confidence from B-factors
    confidence = []
    seen_residues = set()
    for atom in structure.atoms:
        if atom.name == "CA" and atom.residue_seq not in seen_residues:
            confidence.append(atom.temp_factor / 100.0)  # pLDDT is stored as B-factor
            seen_residues.add(atom.residue_seq)

    structure.confidence = confidence
    mean_conf = sum(confidence) / len(confidence) if confidence else 0.0

    if on_progress:
        on_progress("Complete", 1.0)

    # Generate explanation
    if mean_conf > 0.9:
        explanation = "High confidence prediction. The model is very sure about this structure."
    elif mean_conf > 0.7:
        explanation = "Good confidence prediction. Most of the structure is reliable."
    elif mean_conf > 0.5:
        explanation = "Moderate confidence. Some regions may be flexible or disordered."
    else:
        explanation = "Low confidence. This protein may be intrinsically disordered or the sequence may be unusual."

    return FoldResult(
        structure=structure,
        sequence=sequence,
        confidence=confidence,
        mean_confidence=mean_conf,
        method="esmfold",
        explanation=explanation,
    )


# Cache the model to avoid reloading
_esmfold_model = None
_esmfold_device = None


def _get_esmfold_model(device: str):
    """Load ESMFold model with caching."""
    global _esmfold_model, _esmfold_device

    if _esmfold_model is not None and _esmfold_device == device:
        return _esmfold_model

    import torch
    from transformers import EsmForProteinFolding

    logger.info("Loading ESMFold model (this may take a minute on first run)...")
    model = EsmForProteinFolding.from_pretrained("facebook/esmfold_v1")

    if device == "cuda" and torch.cuda.is_available():
        model = model.cuda()
        # Use FP16 if we have enough VRAM
        try:
            vram_gb = torch.cuda.get_device_properties(0).total_mem / (1024**3)
            if vram_gb < 16:
                model = model.half()
                logger.info("Using FP16 for memory efficiency")
        except Exception:
            pass
    else:
        model = model.to(device)

    model.eval()

    _esmfold_model = model
    _esmfold_device = device
    return model
