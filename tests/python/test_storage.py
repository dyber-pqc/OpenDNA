"""Tests for the storage layer."""

import tempfile
from pathlib import Path

from opendna.models.protein import Protein
from opendna.storage.database import Database


def test_database_create():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        assert db is not None
        db.engine.dispose()


def test_save_and_load_protein():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        p = Protein(name="Test", sequence="MKTVRQERLK")

        db.save_protein(p)
        loaded = db.get_protein(p.id)

        assert loaded is not None
        assert loaded.name == "Test"
        assert str(loaded.sequence) == "MKTVRQERLK"
        db.engine.dispose()


def test_list_proteins():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db = Database(Path(tmpdir) / "test.db")
        db.save_protein(Protein(name="P1", sequence="MKTV"))
        db.save_protein(Protein(name="P2", sequence="ACDE"))

        proteins = db.list_proteins()
        assert len(proteins) == 2
        db.engine.dispose()


def test_job_lifecycle():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db = Database(Path(tmpdir) / "test.db")

        db.save_job("job-1", "fold", {"sequence": "MKTV"})
        job = db.get_job("job-1")
        assert job["status"] == "pending"

        db.update_job("job-1", "running", progress=0.5)
        job = db.get_job("job-1")
        assert job["status"] == "running"
        assert job["progress"] == 0.5

        db.update_job("job-1", "completed", progress=1.0, output={"pdb": "..."})
        job = db.get_job("job-1")
        assert job["status"] == "completed"
        assert job["output"] is not None
        db.engine.dispose()
