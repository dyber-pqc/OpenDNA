"""Append-only provenance DAG.

Each computation step is a Node:
    id, ts, project_id, kind, inputs(JSON), outputs(JSON), score, parent_ids[]
Edges are derived from parent_ids; the result is a DAG that lets us:
  - Replay any historical state (time machine)
  - Diff two outputs at the residue level
  - Blame which step introduced a regression

Stored in SQLite at ~/.opendna/provenance.db so it survives restarts.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def _db_path() -> Path:
    p = Path(os.environ.get("OPENDNA_PROVENANCE_DIR", Path.home() / ".opendna"))
    p.mkdir(parents=True, exist_ok=True)
    return p / "provenance.db"


@dataclass
class Node:
    id: str
    ts: float
    project_id: str
    kind: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    score: Optional[float]
    parent_ids: List[str] = field(default_factory=list)
    actor: Optional[str] = None
    content_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "ts": self.ts, "project_id": self.project_id,
            "kind": self.kind, "inputs": self.inputs, "outputs": self.outputs,
            "score": self.score, "parent_ids": self.parent_ids,
            "actor": self.actor, "content_hash": self.content_hash,
        }


@dataclass
class Edge:
    parent: str
    child: str


def _hash_node(kind: str, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> str:
    payload = json.dumps({"k": kind, "i": inputs, "o": outputs},
                         sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class ProvenanceStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = path or _db_path()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._migrate()

    def _migrate(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS prov_nodes (
                id TEXT PRIMARY KEY,
                ts REAL NOT NULL,
                project_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                inputs_json TEXT NOT NULL,
                outputs_json TEXT NOT NULL,
                score REAL,
                actor TEXT,
                content_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS prov_edges (
                parent TEXT NOT NULL,
                child TEXT NOT NULL,
                PRIMARY KEY (parent, child)
            );
            CREATE INDEX IF NOT EXISTS idx_prov_project ON prov_nodes(project_id);
            CREATE INDEX IF NOT EXISTS idx_prov_ts ON prov_nodes(ts);
            CREATE INDEX IF NOT EXISTS idx_prov_kind ON prov_nodes(kind);
            """
        )
        self.conn.commit()

    def add(
        self,
        project_id: str,
        kind: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        score: Optional[float] = None,
        parent_ids: Optional[List[str]] = None,
        actor: Optional[str] = None,
    ) -> Node:
        node = Node(
            id=uuid.uuid4().hex[:12],
            ts=time.time(),
            project_id=project_id,
            kind=kind,
            inputs=inputs,
            outputs=outputs,
            score=score,
            parent_ids=list(parent_ids or []),
            actor=actor,
            content_hash=_hash_node(kind, inputs, outputs),
        )
        with self.conn:
            self.conn.execute(
                "INSERT INTO prov_nodes (id, ts, project_id, kind, inputs_json, outputs_json, score, actor, content_hash) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (node.id, node.ts, node.project_id, node.kind,
                 json.dumps(node.inputs), json.dumps(node.outputs),
                 node.score, node.actor, node.content_hash),
            )
            for p in node.parent_ids:
                self.conn.execute("INSERT OR IGNORE INTO prov_edges (parent, child) VALUES (?,?)", (p, node.id))
        return node

    def get(self, node_id: str) -> Optional[Node]:
        row = self.conn.execute(
            "SELECT id, ts, project_id, kind, inputs_json, outputs_json, score, actor, content_hash "
            "FROM prov_nodes WHERE id=?", (node_id,)
        ).fetchone()
        if not row:
            return None
        parents = [r[0] for r in self.conn.execute(
            "SELECT parent FROM prov_edges WHERE child=?", (node_id,)
        ).fetchall()]
        return Node(
            id=row[0], ts=row[1], project_id=row[2], kind=row[3],
            inputs=json.loads(row[4]), outputs=json.loads(row[5]),
            score=row[6], actor=row[7], content_hash=row[8],
            parent_ids=parents,
        )

    def project_nodes(self, project_id: str) -> List[Node]:
        rows = self.conn.execute(
            "SELECT id FROM prov_nodes WHERE project_id=? ORDER BY ts ASC",
            (project_id,),
        ).fetchall()
        return [self.get(r[0]) for r in rows if self.get(r[0]) is not None]  # type: ignore

    def project_edges(self, project_id: str) -> List[Edge]:
        rows = self.conn.execute(
            "SELECT e.parent, e.child FROM prov_edges e "
            "JOIN prov_nodes n ON n.id = e.child WHERE n.project_id=?",
            (project_id,),
        ).fetchall()
        return [Edge(parent=r[0], child=r[1]) for r in rows]

    def children_of(self, node_id: str) -> List[str]:
        return [r[0] for r in self.conn.execute(
            "SELECT child FROM prov_edges WHERE parent=?", (node_id,)
        ).fetchall()]

    def lineage(self, node_id: str) -> List[Node]:
        """Walk parents back to roots, returning chronological list."""
        seen = set()
        out: List[Node] = []
        stack = [node_id]
        while stack:
            nid = stack.pop()
            if nid in seen:
                continue
            seen.add(nid)
            n = self.get(nid)
            if n is None:
                continue
            out.append(n)
            stack.extend(n.parent_ids)
        out.sort(key=lambda n: n.ts)
        return out

    def stats(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        if project_id:
            n = self.conn.execute(
                "SELECT COUNT(*) FROM prov_nodes WHERE project_id=?", (project_id,)
            ).fetchone()[0]
        else:
            n = self.conn.execute("SELECT COUNT(*) FROM prov_nodes").fetchone()[0]
        return {"nodes": n}


_store: Optional[ProvenanceStore] = None


def get_provenance_store() -> ProvenanceStore:
    global _store
    if _store is None:
        _store = ProvenanceStore()
    return _store


def record_step(
    project_id: str,
    kind: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    score: Optional[float] = None,
    parent_ids: Optional[List[str]] = None,
    actor: Optional[str] = None,
) -> Node:
    return get_provenance_store().add(
        project_id, kind, inputs, outputs, score, parent_ids, actor,
    )
