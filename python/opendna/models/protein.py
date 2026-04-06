"""Core data models for OpenDNA."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional


VALID_AMINO_ACIDS = set("ACDEFGHIKLMNPQRSTVWY")


@dataclass
class Sequence:
    """An amino acid sequence."""

    residues: str

    def __post_init__(self):
        self.residues = self.residues.upper().replace(" ", "")

    def __len__(self) -> int:
        return len(self.residues)

    def __str__(self) -> str:
        return self.residues

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Sequence):
            return self.residues == other.residues
        return NotImplemented

    @property
    def hash(self) -> str:
        return hashlib.sha256(self.residues.encode()).hexdigest()[:12]

    @property
    def is_valid(self) -> bool:
        return all(c in VALID_AMINO_ACIDS for c in self.residues)

    def to_fasta(self, name: str = "protein") -> str:
        lines = [f">{name}"]
        for i in range(0, len(self.residues), 80):
            lines.append(self.residues[i : i + 80])
        return "\n".join(lines) + "\n"


class StructureFormat(str, Enum):
    PDB = "pdb"
    MMCIF = "mmcif"


@dataclass
class Atom:
    """A single atom in a 3D structure."""

    serial: int
    name: str
    residue_name: str
    chain_id: str
    residue_seq: int
    x: float
    y: float
    z: float
    occupancy: float = 1.0
    temp_factor: float = 0.0
    element: str = ""


@dataclass
class Structure:
    """A 3D protein structure."""

    atoms: list[Atom]
    confidence: Optional[list[float]] = None
    format: StructureFormat = StructureFormat.PDB
    pdb_string: Optional[str] = None

    @property
    def num_atoms(self) -> int:
        return len(self.atoms)

    @property
    def mean_confidence(self) -> Optional[float]:
        if self.confidence is None or len(self.confidence) == 0:
            return None
        return sum(self.confidence) / len(self.confidence)

    def to_pdb(self) -> str:
        if self.pdb_string:
            return self.pdb_string
        lines = []
        for atom in self.atoms:
            lines.append(
                f"ATOM  {atom.serial:>5} {atom.name:<4} {atom.residue_name:>3} "
                f"{atom.chain_id}{atom.residue_seq:>4}    "
                f"{atom.x:>8.3f}{atom.y:>8.3f}{atom.z:>8.3f}"
                f"{atom.occupancy:>6.2f}{atom.temp_factor:>6.2f}          {atom.element:>2}"
            )
        lines.append("END")
        return "\n".join(lines) + "\n"

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.to_pdb())

    @classmethod
    def from_pdb_file(cls, path: str | Path) -> "Structure":
        content = Path(path).read_text()
        return cls.from_pdb_string(content)

    @classmethod
    def from_pdb_string(cls, content: str) -> "Structure":
        atoms = []
        for line in content.splitlines():
            if line.startswith(("ATOM", "HETATM")) and len(line) >= 54:
                try:
                    atoms.append(
                        Atom(
                            serial=int(line[6:11].strip()),
                            name=line[12:16].strip(),
                            residue_name=line[17:20].strip(),
                            chain_id=line[21:22].strip() or "A",
                            residue_seq=int(line[22:26].strip()),
                            x=float(line[30:38].strip()),
                            y=float(line[38:46].strip()),
                            z=float(line[46:54].strip()),
                            occupancy=float(line[54:60].strip()) if len(line) > 54 else 1.0,
                            temp_factor=float(line[60:66].strip()) if len(line) > 60 else 0.0,
                            element=line[76:78].strip() if len(line) > 76 else "",
                        )
                    )
                except (ValueError, IndexError):
                    continue
        return cls(atoms=atoms, pdb_string=content)


@dataclass
class Protein:
    """A protein with sequence, optional structure, and metadata."""

    name: str
    sequence: Sequence
    id: str = ""
    structure: Optional[Structure] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if isinstance(self.sequence, str):
            self.sequence = Sequence(self.sequence)
        if not self.id:
            self.id = self.sequence.hash

    def __len__(self) -> int:
        return len(self.sequence)

    def __repr__(self) -> str:
        return f"Protein(name='{self.name}', length={len(self)}, id='{self.id}')"

    @classmethod
    def from_fasta(cls, path: str | Path) -> list["Protein"]:
        content = Path(path).read_text()
        proteins = []
        current_name = ""
        current_seq = ""
        for line in content.splitlines():
            line = line.strip()
            if line.startswith(">"):
                if current_name:
                    proteins.append(cls(name=current_name, sequence=current_seq))
                    current_seq = ""
                current_name = line[1:].strip()
            elif line and not line.startswith(";"):
                current_seq += line
        if current_name:
            proteins.append(cls(name=current_name, sequence=current_seq))
        return proteins
