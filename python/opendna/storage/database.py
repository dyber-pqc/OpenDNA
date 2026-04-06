"""Local SQLite storage for OpenDNA projects and proteins."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import Column, Float, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


class ProteinRecord(Base):
    __tablename__ = "proteins"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    sequence = Column(Text, nullable=False)
    metadata_json = Column(Text, default="{}")
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)


class ProjectRecord(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    path = Column(String, nullable=False)
    created_at = Column(String, nullable=False)


class JobRecord(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=True)
    job_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    input_json = Column(Text, nullable=False)
    output_json = Column(Text, nullable=True)
    progress = Column(Float, default=0.0)
    created_at = Column(String, nullable=False)
    completed_at = Column(String, nullable=True)


class Database:
    """Local SQLite database for OpenDNA metadata."""

    def __init__(self, path: Optional[str | Path] = None):
        if path is None:
            path = get_data_dir() / "database.sqlite"
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(f"sqlite:///{path}")
        Base.metadata.create_all(self.engine)
        self._Session = sessionmaker(bind=self.engine)

    def session(self) -> Session:
        return self._Session()

    def save_protein(self, protein) -> None:
        from opendna.models.protein import Protein

        with self.session() as s:
            record = ProteinRecord(
                id=protein.id,
                name=protein.name,
                sequence=str(protein.sequence),
                metadata_json=json.dumps(protein.metadata),
                created_at=protein.created_at.isoformat(),
                updated_at=protein.updated_at.isoformat(),
            )
            s.merge(record)
            s.commit()

    def get_protein(self, protein_id: str):
        from opendna.models.protein import Protein, Sequence

        with self.session() as s:
            record = s.query(ProteinRecord).filter_by(id=protein_id).first()
            if record is None:
                return None
            return Protein(
                id=record.id,
                name=record.name,
                sequence=Sequence(record.sequence),
                metadata=json.loads(record.metadata_json or "{}"),
                created_at=datetime.fromisoformat(record.created_at),
                updated_at=datetime.fromisoformat(record.updated_at),
            )

    def list_proteins(self) -> list[tuple[str, str, int]]:
        with self.session() as s:
            records = s.query(ProteinRecord).order_by(ProteinRecord.created_at.desc()).all()
            return [(r.id, r.name, len(r.sequence)) for r in records]

    def save_job(self, job_id: str, job_type: str, input_data: dict) -> None:
        with self.session() as s:
            record = JobRecord(
                id=job_id,
                job_type=job_type,
                status="pending",
                input_json=json.dumps(input_data),
                progress=0.0,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            s.merge(record)
            s.commit()

    def update_job(self, job_id: str, status: str, progress: float = 0.0, output: dict | None = None) -> None:
        with self.session() as s:
            record = s.query(JobRecord).filter_by(id=job_id).first()
            if record:
                record.status = status
                record.progress = progress
                if output:
                    record.output_json = json.dumps(output)
                if status in ("completed", "failed"):
                    record.completed_at = datetime.now(timezone.utc).isoformat()
                s.commit()

    def get_job(self, job_id: str) -> Optional[dict]:
        with self.session() as s:
            record = s.query(JobRecord).filter_by(id=job_id).first()
            if record is None:
                return None
            return {
                "id": record.id,
                "type": record.job_type,
                "status": record.status,
                "progress": record.progress,
                "input": json.loads(record.input_json),
                "output": json.loads(record.output_json) if record.output_json else None,
                "created_at": record.created_at,
                "completed_at": record.completed_at,
            }


def get_data_dir() -> Path:
    """Get the OpenDNA data directory."""
    data_dir = Path.home() / ".opendna"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_models_dir() -> Path:
    """Get the models cache directory."""
    models_dir = get_data_dir() / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir
