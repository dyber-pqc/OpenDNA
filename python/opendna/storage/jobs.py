"""Persistent job storage in SQLite.

Replaces the in-memory dict so jobs survive server restarts.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from opendna.storage.database import get_data_dir


class JobStore:
    """SQLite-backed job store with the same dict-like API as the old version."""

    def __init__(self, path: Optional[Path] = None):
        if path is None:
            path = get_data_dir() / "jobs.sqlite"
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self):
        import sqlite3
        return sqlite3.connect(self.path)

    def _init_db(self):
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    status TEXT,
                    progress REAL,
                    result TEXT,
                    error TEXT,
                    started_at REAL,
                    completed_at REAL
                )
            """)
            c.commit()

    def create(self, job_id: str, job_type: str) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO jobs (id, type, status, progress, started_at) VALUES (?, ?, ?, ?, ?)",
                (job_id, job_type, "running", 0.0, time.time()),
            )
            c.commit()

    def update(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        result: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> None:
        fields = []
        values = []
        if status is not None:
            fields.append("status = ?")
            values.append(status)
        if progress is not None:
            fields.append("progress = ?")
            values.append(progress)
        if result is not None:
            fields.append("result = ?")
            values.append(json.dumps(result))
        if error is not None:
            fields.append("error = ?")
            values.append(error)
        if status in ("completed", "failed"):
            fields.append("completed_at = ?")
            values.append(time.time())
        if not fields:
            return
        values.append(job_id)
        with self._conn() as c:
            c.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?", values)
            c.commit()

    def get(self, job_id: str) -> Optional[dict]:
        with self._conn() as c:
            row = c.execute(
                "SELECT id, type, status, progress, result, error, started_at FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "type": row[1],
            "status": row[2],
            "progress": row[3],
            "result": json.loads(row[4]) if row[4] else None,
            "error": row[5],
            "started_at": row[6],
        }

    def list_recent(self, limit: int = 50) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT id, type, status, progress, started_at FROM jobs ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "id": r[0],
                "type": r[1],
                "status": r[2],
                "progress": r[3],
                "started_at": r[4],
            }
            for r in rows
        ]

    def __contains__(self, job_id: str) -> bool:
        return self.get(job_id) is not None

    def __getitem__(self, job_id: str) -> dict:
        j = self.get(job_id)
        if j is None:
            raise KeyError(job_id)
        return j

    def __setitem__(self, job_id: str, data: dict) -> None:
        # For backwards compatibility with the dict-style API
        if not self.__contains__(job_id):
            self.create(job_id, data.get("type", "unknown"))
        self.update(
            job_id,
            status=data.get("status"),
            progress=data.get("progress"),
            result=data.get("result"),
            error=data.get("error"),
        )


# Global instance
_job_store: Optional[JobStore] = None


def get_job_store() -> JobStore:
    global _job_store
    if _job_store is None:
        _job_store = JobStore()
    return _job_store
