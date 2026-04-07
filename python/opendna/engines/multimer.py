"""Multimer protein structure prediction.

Uses the Boltz model when available (https://github.com/jwohlwend/boltz)
which is an open-source AlphaFold-style multimer predictor.

Falls back to per-chain ESMFold + simple alignment for monomeric chains.
To enable Boltz:
    pip install boltz
"""

from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class MultimerResult:
    pdb_string: str
    chains: list[dict]
    mean_confidence: float
    interface_residues: list[dict] = field(default_factory=list)
    method: str = "boltz"
    notes: str = ""


def fold_multimer(
    sequences: list[str],
    chain_ids: Optional[list[str]] = None,
    on_progress: Optional[Callable[[str, float], None]] = None,
) -> MultimerResult:
    """Predict the structure of a protein complex from multiple sequences.

    Args:
        sequences: List of amino acid sequences, one per chain
        chain_ids: Optional list of chain IDs (default: A, B, C, ...)
        on_progress: Progress callback

    Tries Boltz first (real multimer prediction), falls back to per-chain
    ESMFold (monomers only).
    """
    if not chain_ids:
        chain_ids = [chr(ord("A") + i) for i in range(len(sequences))]

    # Try Boltz
    try:
        return _boltz_predict(sequences, chain_ids, on_progress)
    except ImportError:
        logger.info("Boltz not installed, falling back to per-chain ESMFold")
    except Exception as e:
        logger.warning(f"Boltz failed: {e}, falling back to per-chain ESMFold")

    return _per_chain_esmfold(sequences, chain_ids, on_progress)


def _boltz_predict(sequences, chain_ids, on_progress):
    """Use the Boltz model for real multimer prediction."""
    try:
        import boltz  # type: ignore  # noqa: F401
    except ImportError:
        raise ImportError("boltz package not installed")

    if on_progress:
        on_progress("Loading Boltz model", 0.05)

    # Boltz CLI takes a YAML input. Build it.
    yaml_content = "version: 1\nsequences:\n"
    for chain_id, seq in zip(chain_ids, sequences):
        yaml_content += f"  - protein:\n      id: {chain_id}\n      sequence: {seq}\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        input_yaml = Path(tmpdir) / "input.yaml"
        input_yaml.write_text(yaml_content)

        if on_progress:
            on_progress("Running Boltz prediction (this can take several minutes)", 0.2)

        # Run boltz CLI
        import subprocess
        try:
            subprocess.run(
                ["boltz", "predict", str(input_yaml), "--out_dir", tmpdir],
                check=True,
                capture_output=True,
                timeout=1800,
            )
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            raise RuntimeError(f"Boltz CLI failed: {e}")

        # Find the output PDB
        pdb_files = list(Path(tmpdir).rglob("*.pdb"))
        if not pdb_files:
            raise RuntimeError("Boltz produced no PDB output")

        pdb_string = pdb_files[0].read_text()

    if on_progress:
        on_progress("Computing interface", 0.9)

    interface = _detect_interface(pdb_string, chain_ids)

    if on_progress:
        on_progress("Complete", 1.0)

    return MultimerResult(
        pdb_string=pdb_string,
        chains=[{"id": cid, "sequence": s} for cid, s in zip(chain_ids, sequences)],
        mean_confidence=_mean_plddt_from_pdb(pdb_string),
        interface_residues=interface,
        method="boltz",
        notes=f"Real multimer prediction with Boltz ({len(sequences)} chains)",
    )


def _per_chain_esmfold(sequences, chain_ids, on_progress):
    """Fallback: fold each chain independently with ESMFold and concatenate."""
    from opendna.engines.folding import fold

    if on_progress:
        on_progress("Per-chain ESMFold (no inter-chain prediction)", 0.1)

    chain_pdbs = []
    confidences = []
    for i, (chain_id, seq) in enumerate(zip(chain_ids, sequences)):
        if on_progress:
            on_progress(
                f"Folding chain {chain_id} ({i + 1}/{len(sequences)})",
                0.1 + 0.85 * (i / len(sequences)),
            )
        result = fold(seq)
        confidences.append(result.mean_confidence)
        # Re-label chain ID in the PDB
        relabeled = _relabel_chain(result.pdb_string, chain_id)
        # Offset the residue numbers and shift coordinates so chains don't overlap
        shifted = _shift_chain(relabeled, x_offset=i * 50.0)
        chain_pdbs.append(shifted)

    combined_pdb = _combine_pdbs(chain_pdbs)
    interface = _detect_interface(combined_pdb, chain_ids)

    if on_progress:
        on_progress("Complete", 1.0)

    return MultimerResult(
        pdb_string=combined_pdb,
        chains=[{"id": cid, "sequence": s} for cid, s in zip(chain_ids, sequences)],
        mean_confidence=sum(confidences) / len(confidences) if confidences else 0.0,
        interface_residues=interface,
        method="per-chain-esmfold",
        notes=(
            "Each chain folded independently with ESMFold and placed in separate "
            "regions of space. NO real inter-chain interactions predicted. "
            "Install Boltz (pip install boltz) for true multimer prediction."
        ),
    )


def _relabel_chain(pdb: str, new_chain: str) -> str:
    out = []
    for line in pdb.split("\n"):
        if line.startswith(("ATOM", "HETATM")) and len(line) >= 22:
            line = line[:21] + new_chain + line[22:]
        out.append(line)
    return "\n".join(out)


def _shift_chain(pdb: str, x_offset: float) -> str:
    out = []
    for line in pdb.split("\n"):
        if line.startswith(("ATOM", "HETATM")) and len(line) >= 54:
            try:
                x = float(line[30:38].strip())
                new_x = x + x_offset
                line = line[:30] + f"{new_x:8.3f}" + line[38:]
            except ValueError:
                pass
        out.append(line)
    return "\n".join(out)


def _combine_pdbs(pdb_strings: list[str]) -> str:
    """Combine multiple PDB strings into one multimer PDB."""
    out = []
    serial = 1
    for pdb in pdb_strings:
        for line in pdb.split("\n"):
            if line.startswith("END"):
                continue
            if line.startswith(("ATOM", "HETATM")) and len(line) >= 11:
                line = line[:6] + f"{serial:>5}" + line[11:]
                serial += 1
            out.append(line)
        out.append("TER")
    out.append("END")
    return "\n".join(out)


def _detect_interface(pdb: str, chain_ids: list[str], cutoff: float = 5.0) -> list[dict]:
    """Find inter-chain residue contacts within `cutoff` angstroms."""
    import math
    atoms_by_chain: dict[str, list] = {cid: [] for cid in chain_ids}

    for line in pdb.split("\n"):
        if not line.startswith("ATOM") or len(line) < 54:
            continue
        try:
            chain = line[21]
            res = line[17:20].strip()
            res_num = int(line[22:26].strip())
            x = float(line[30:38].strip())
            y = float(line[38:46].strip())
            z = float(line[46:54].strip())
            if chain in atoms_by_chain:
                atoms_by_chain[chain].append((res, res_num, x, y, z))
        except (ValueError, IndexError):
            continue

    interface = set()
    chain_list = list(atoms_by_chain.keys())
    cutoff2 = cutoff * cutoff
    for i, ca in enumerate(chain_list):
        for cb in chain_list[i + 1:]:
            for ra in atoms_by_chain[ca]:
                for rb in atoms_by_chain[cb]:
                    d2 = (ra[2] - rb[2]) ** 2 + (ra[3] - rb[3]) ** 2 + (ra[4] - rb[4]) ** 2
                    if d2 < cutoff2:
                        interface.add((ca, ra[0], ra[1]))
                        interface.add((cb, rb[0], rb[1]))

    return [
        {"chain": c, "residue": r, "residue_num": n}
        for c, r, n in sorted(interface)
    ][:200]


def _mean_plddt_from_pdb(pdb: str) -> float:
    values = []
    for line in pdb.split("\n"):
        if line.startswith("ATOM") and len(line) >= 66:
            if line[12:16].strip() == "CA":
                try:
                    values.append(float(line[60:66].strip()))
                except ValueError:
                    pass
    if not values:
        return 1.0
    mean = sum(values) / len(values)
    return mean / 100 if mean > 1 else mean
