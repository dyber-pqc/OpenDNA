"""Append-only audit log with hash-chained records.

Each record's hash includes the previous record's hash, so tampering with any
historical entry invalidates all subsequent hashes. This gives us tamper-evident
logging cheaply without a full blockchain.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def _db_path() -> Path:
    root = Path(os.environ.get("OPENDNA_AUTH_DIR", Path.home() / ".opendna"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "audit.db"


class AuditLog:
    def __init__(self, path: Optional[Path] = None):
        self.path = path or _db_path()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                actor TEXT,
                action TEXT NOT NULL,
                resource TEXT,
                ip TEXT,
                details_json TEXT,
                prev_hash TEXT,
                record_hash TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def _last_hash(self) -> str:
        row = self.conn.execute("SELECT record_hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
        return row[0] if row else "GENESIS"

    def append(
        self,
        action: str,
        actor: Optional[str] = None,
        resource: Optional[str] = None,
        ip: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        ts = time.time()
        prev = self._last_hash()
        details_json = json.dumps(details or {}, sort_keys=True, separators=(",", ":"))
        payload = f"{ts}|{actor or ''}|{action}|{resource or ''}|{ip or ''}|{details_json}|{prev}"
        record_hash = hashlib.sha256(payload.encode()).hexdigest()
        with self.conn:
            self.conn.execute(
                "INSERT INTO audit (ts, actor, action, resource, ip, details_json, prev_hash, record_hash) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (ts, actor, action, resource, ip, details_json, prev, record_hash),
            )
        return record_hash

    def tail(self, n: int = 100) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id, ts, actor, action, resource, ip, details_json, prev_hash, record_hash "
            "FROM audit ORDER BY id DESC LIMIT ?", (n,)
        ).fetchall()
        out = []
        for r in rows:
            out.append({
                "id": r[0], "ts": r[1], "actor": r[2], "action": r[3],
                "resource": r[4], "ip": r[5], "details": json.loads(r[6] or "{}"),
                "prev_hash": r[7], "record_hash": r[8],
            })
        return out

    def verify_chain(self) -> Dict[str, Any]:
        """Walk the chain and verify every hash. Returns {ok, broken_at}."""
        prev = "GENESIS"
        rows = self.conn.execute(
            "SELECT id, ts, actor, action, resource, ip, details_json, prev_hash, record_hash "
            "FROM audit ORDER BY id ASC"
        ).fetchall()
        for r in rows:
            id_, ts, actor, action, resource, ip, dj, stored_prev, rec_hash = r
            if stored_prev != prev:
                return {"ok": False, "broken_at": id_, "reason": "prev_hash mismatch"}
            payload = f"{ts}|{actor or ''}|{action}|{resource or ''}|{ip or ''}|{dj}|{prev}"
            if hashlib.sha256(payload.encode()).hexdigest() != rec_hash:
                return {"ok": False, "broken_at": id_, "reason": "hash mismatch"}
            prev = rec_hash
        return {"ok": True, "count": len(rows)}


_log: Optional[AuditLog] = None


def get_audit_log() -> AuditLog:
    global _log
    if _log is None:
        _log = AuditLog()
    return _log
