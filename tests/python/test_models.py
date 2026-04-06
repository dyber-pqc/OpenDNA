"""Tests for OpenDNA data models."""

from opendna.models.protein import Protein, Sequence, Structure


def test_sequence_creation():
    seq = Sequence("MKTVRQERLK")
    assert len(seq) == 10
    assert seq.is_valid
    assert str(seq) == "MKTVRQERLK"


def test_sequence_normalization():
    seq = Sequence("mktv rqerlk")
    assert str(seq) == "MKTVRQERLK"


def test_sequence_invalid():
    seq = Sequence("MKTXZJ123")
    assert not seq.is_valid


def test_sequence_hash_deterministic():
    s1 = Sequence("MKTVRQERLK")
    s2 = Sequence("MKTVRQERLK")
    assert s1.hash == s2.hash


def test_sequence_hash_unique():
    s1 = Sequence("MKTVRQERLK")
    s2 = Sequence("ACDEFGHIK")
    assert s1.hash != s2.hash


def test_protein_creation():
    p = Protein(name="Test", sequence="MKTVRQERLK")
    assert p.name == "Test"
    assert len(p) == 10
    assert p.id == p.sequence.hash


def test_protein_from_string():
    p = Protein(name="Test", sequence="MKTVRQERLK")
    assert isinstance(p.sequence, Sequence)


def test_protein_repr():
    p = Protein(name="Test", sequence="MKTVRQERLK")
    assert "Test" in repr(p)
    assert "10" in repr(p)


def test_structure_from_pdb_string():
    pdb = (
        "ATOM      1  N   ALA A   1       1.000   2.000   3.000  1.00  0.00           N  \n"
        "ATOM      2  CA  ALA A   1       2.000   3.000   4.000  1.00  0.00           C  \n"
        "ATOM      3  C   ALA A   1       3.000   4.000   5.000  1.00  0.00           C  \n"
        "END\n"
    )
    s = Structure.from_pdb_string(pdb)
    assert s.num_atoms == 3
    assert s.atoms[0].name == "N"
    assert abs(s.atoms[0].x - 1.0) < 0.001


def test_sequence_fasta():
    seq = Sequence("MKTVRQERLK")
    fasta = seq.to_fasta("test_protein")
    assert fasta.startswith(">test_protein\n")
    assert "MKTVRQERLK" in fasta
