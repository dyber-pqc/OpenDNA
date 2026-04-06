"""Protein sequence design engine using ESM-IF1 (inverse folding)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from opendna.models.protein import Sequence, Structure

logger = logging.getLogger(__name__)


@dataclass
class DesignConstraints:
    fixed_positions: list[int] = field(default_factory=list)
    temperature: float = 0.1
    num_candidates: int = 10


@dataclass
class DesignCandidate:
    sequence: Sequence
    score: float
    recovery: float
    rank: int

    def __repr__(self) -> str:
        return (
            f"DesignCandidate(rank={self.rank}, score={self.score:.3f}, "
            f"recovery={self.recovery:.1%}, length={len(self.sequence)})"
        )


@dataclass
class DesignResult:
    candidates: list[DesignCandidate]
    backbone_source: str
    method: str
    explanation: str

    @property
    def best(self) -> DesignCandidate:
        return self.candidates[0]

    def top(self, n: int = 5) -> list[DesignCandidate]:
        return self.candidates[:n]

    def to_fasta(self, path: str | Path) -> None:
        lines = []
        for c in self.candidates:
            lines.append(f">candidate_{c.rank}_score_{c.score:.3f}")
            lines.append(str(c.sequence))
        Path(path).write_text("\n".join(lines) + "\n")


def design(
    structure: Structure | str | Path,
    constraints: DesignConstraints | None = None,
    method: str = "auto",
    device: str | None = None,
    on_progress: Optional[Callable[[str, float], None]] = None,
) -> DesignResult:
    """Design protein sequences for a given backbone structure using inverse folding."""
    if constraints is None:
        constraints = DesignConstraints()

    if isinstance(structure, (str, Path)):
        if isinstance(structure, str) and ("ATOM" in structure[:1000] or "HETATM" in structure[:1000]):
            # Looks like PDB content (may have header lines like PARENT)
            structure = Structure.from_pdb_string(structure)
        else:
            try:
                path = Path(structure)
                if path.exists():
                    structure = Structure.from_pdb_file(path)
                else:
                    raise ValueError(f"Cannot load structure: not a valid path or PDB content")
            except (OSError, ValueError) as e:
                raise ValueError(f"Cannot load structure: {e}")

    if on_progress:
        on_progress("Initializing", 0.0)

    if device is None:
        from opendna.hardware.detect import get_torch_device
        device = get_torch_device()

    return _design_esm_if(structure, constraints, device, on_progress)


def _design_esm_if(
    structure: Structure,
    constraints: DesignConstraints,
    device: str,
    on_progress: Optional[Callable[[str, float], None]] = None,
) -> DesignResult:
    """Design sequences using ESM-IF1 inverse folding."""
    try:
        import esm
        import esm.inverse_folding
        import torch
    except ImportError as e:
        logger.warning(f"ESM-IF not available: {e}. Falling back to heuristic stub.")
        return _design_heuristic_stub(structure, constraints, on_progress)

    if on_progress:
        on_progress("Loading ESM-IF1 model (first run downloads ~600MB)", 0.05)

    try:
        model, alphabet = _get_esm_if_model(device)
    except Exception as e:
        logger.warning(f"Failed to load ESM-IF1: {e}. Using fallback.")
        return _design_heuristic_stub(structure, constraints, on_progress)

    if on_progress:
        on_progress("Preparing structure", 0.2)

    import tempfile
    import os
    fd, pdb_path = tempfile.mkstemp(suffix=".pdb")
    os.close(fd)
    Path(pdb_path).write_text(structure.to_pdb())

    try:
        chain_id = "A"
        loaded_structure = esm.inverse_folding.util.load_structure(pdb_path, chain_id)
        coords, native_seq = esm.inverse_folding.util.extract_coords_from_structure(
            loaded_structure
        )
    except Exception as e:
        logger.warning(f"Failed to load coords: {e}. Using fallback.")
        return _design_heuristic_stub(structure, constraints, on_progress)
    finally:
        try:
            Path(pdb_path).unlink()
        except OSError:
            pass

    if on_progress:
        on_progress("Generating sequences", 0.4)

    candidates = []
    for i in range(constraints.num_candidates):
        if on_progress:
            progress = 0.4 + 0.55 * (i / constraints.num_candidates)
            on_progress(
                f"Sampling candidate {i + 1}/{constraints.num_candidates}",
                progress,
            )

        with torch.no_grad():
            sampled_seq = model.sample(
                coords, temperature=max(constraints.temperature, 1e-3), device=device
            )

        if isinstance(sampled_seq, tuple):
            sampled_seq = sampled_seq[0]

        recovery = (
            sum(1 for a, b in zip(sampled_seq, native_seq) if a == b)
            / max(len(native_seq), 1)
        )
        score = -recovery  # Lower is better; high recovery = low (good) score

        candidates.append(
            DesignCandidate(
                sequence=Sequence(sampled_seq),
                score=score,
                recovery=recovery,
                rank=i + 1,
            )
        )

    candidates.sort(key=lambda c: c.score)
    for i, c in enumerate(candidates):
        c.rank = i + 1

    if on_progress:
        on_progress("Complete", 1.0)

    explanation = (
        f"Generated {len(candidates)} candidate sequences using ESM-IF1 inverse folding. "
        f"Best recovery: {candidates[0].recovery:.1%}. "
        f"These sequences are predicted to fold into the input backbone."
    )

    return DesignResult(
        candidates=candidates,
        backbone_source="input_structure",
        method="esm-if1",
        explanation=explanation,
    )


def _design_heuristic_stub(
    structure: Structure,
    constraints: DesignConstraints,
    on_progress: Optional[Callable[[str, float], None]] = None,
) -> DesignResult:
    """Fallback heuristic design when ESM-IF unavailable."""
    import random

    aa_map = {
        "ALA": "A", "CYS": "C", "ASP": "D", "GLU": "E", "PHE": "F",
        "GLY": "G", "HIS": "H", "ILE": "I", "LYS": "K", "LEU": "L",
        "MET": "M", "ASN": "N", "PRO": "P", "GLN": "Q", "ARG": "R",
        "SER": "S", "THR": "T", "VAL": "V", "TRP": "W", "TYR": "Y",
    }

    seen = set()
    original = []
    for atom in structure.atoms:
        key = (atom.chain_id, atom.residue_seq)
        if key not in seen:
            seen.add(key)
            original.append(aa_map.get(atom.residue_name, "A"))
    original_seq = "".join(original)
    n = len(original_seq)

    weights = "AAAAALLLLLIIIIVVVVGGGSSSSTTTTPPPDDDDEEEEKKKKRRRRNNNNQQQQHHFFYYWWCCMM"
    candidates = []
    rng = random.Random(42)
    for i in range(constraints.num_candidates):
        if on_progress:
            on_progress(
                f"Sampling {i + 1}/{constraints.num_candidates}",
                0.2 + 0.7 * (i / constraints.num_candidates),
            )
        seq = "".join(rng.choice(weights) for _ in range(n))
        recovery = sum(1 for a, b in zip(seq, original_seq) if a == b) / n if n else 0
        score = rng.uniform(-2.0, -0.5)
        candidates.append(
            DesignCandidate(sequence=Sequence(seq), score=score, recovery=recovery, rank=i + 1)
        )

    candidates.sort(key=lambda c: c.score)
    for i, c in enumerate(candidates):
        c.rank = i + 1

    return DesignResult(
        candidates=candidates,
        backbone_source="input_structure",
        method="heuristic_stub",
        explanation=f"Generated {len(candidates)} sequences (heuristic fallback - install fair-esm for ESM-IF1).",
    )


_esm_if_model = None
_esm_if_alphabet = None
_esm_if_device = None


def _get_esm_if_model(device: str):
    global _esm_if_model, _esm_if_alphabet, _esm_if_device
    if _esm_if_model is not None and _esm_if_device == device:
        return _esm_if_model, _esm_if_alphabet

    import esm
    logger.info("Loading ESM-IF1 model (first run downloads ~600MB)...")
    model, alphabet = esm.pretrained.esm_if1_gvp4_t16_142M_UR50()
    model = model.to(device)
    model.eval()
    _esm_if_model = model
    _esm_if_alphabet = alphabet
    _esm_if_device = device
    return model, alphabet


# --- Mutation utilities ---

def apply_mutation(sequence: str, mutation: str) -> str:
    """Apply a mutation in standard format like 'G45D' (1-indexed)."""
    import re
    m = re.match(r"^([A-Z])(\d+)([A-Z])$", mutation.strip().upper())
    if not m:
        raise ValueError(f"Invalid mutation format '{mutation}'. Expected e.g. 'G45D'.")
    from_aa, pos_str, to_aa = m.groups()
    pos = int(pos_str) - 1
    if pos < 0 or pos >= len(sequence):
        raise ValueError(f"Position {pos + 1} out of range for sequence of length {len(sequence)}.")
    if sequence[pos] != from_aa:
        raise ValueError(
            f"Position {pos + 1} is '{sequence[pos]}', not '{from_aa}'. "
            f"Did you mean {sequence[pos]}{pos + 1}{to_aa}?"
        )
    return sequence[:pos] + to_aa + sequence[pos + 1:]
