"""Priority job queue + progress pub/sub (Phase 6).

A single global queue holds jobs with priorities:
    0 = interactive  (runs immediately if a worker is free)
    1 = normal       (default)
    2 = batch        (runs only when nothing else is waiting)

Workers pull from the highest-priority non-empty bucket. Each job publishes
progress events to an asyncio pub/sub so WebSocket and SSE clients can stream
updates in real time.

Jobs are persisted to SQLite at ~/.opendna/jobs.db so that the queue survives
process restarts. On startup, any jobs left in 'queued' or 'running' state are
reloaded; running jobs are reset to 'queued' so they will be re-executed by a
worker. Note: persisted jobs without an in-memory `fn` callable cannot actually
be re-run automatically — they remain visible in `list()`/`get()` but require
the caller to resubmit them with the same job_id (or accept that they sit in
'queued' until manually cleaned up). The persistence layer is best-effort and
never raises into the hot path.
"""
from __future__ import annotations

import asyncio
import heapq
import itertools
import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set


@dataclass(order=True)
class _Entry:
    priority: int
    seq: int
    job_id: str = field(compare=False)
    fn: Callable = field(compare=False)
    kwargs: Dict[str, Any] = field(compare=False)


def _default_db_path() -> Path:
    override = os.environ.get("OPENDNA_JOBS_DB")
    if override:
        return Path(override)
    return Path.home() / ".opendna" / "jobs.db"


_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    type TEXT,
    status TEXT,
    progress REAL,
    priority INTEGER,
    user_id TEXT,
    created_at REAL,
    started_at REAL,
    finished_at REAL,
    result_json TEXT,
    error TEXT,
    messages_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
"""


class JobQueue:
    def __init__(self, num_workers: int = 2, db_path: Optional[Path] = None):
        self._heap: List[_Entry] = []
        self._counter = itertools.count()
        self._lock = asyncio.Lock()
        self._cond = asyncio.Condition()
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self.num_workers = num_workers
        self._workers_started = False
        self._db_path = Path(db_path) if db_path else _default_db_path()
        self._last_progress_persist: Dict[str, float] = {}
        self._init_db()
        self._load_persisted()

    # --- persistence ---

    def _init_db(self) -> None:
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self._db_path) as conn:
                conn.executescript(_SCHEMA)
        except Exception as e:  # pragma: no cover
            print(f"[job_queue] failed to init db: {e}")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _load_persisted(self) -> None:
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM jobs WHERE status IN ('queued','running')"
                ).fetchall()
                for r in rows:
                    status = r["status"]
                    if status == "running":
                        status = "queued"
                    job = {
                        "id": r["id"],
                        "type": r["type"],
                        "status": status,
                        "progress": r["progress"] or 0.0,
                        "priority": r["priority"] if r["priority"] is not None else 1,
                        "user_id": r["user_id"],
                        "created_at": r["created_at"],
                        "started_at": None,
                        "finished_at": None,
                        "result": json.loads(r["result_json"]) if r["result_json"] else None,
                        "error": r["error"],
                        "messages": json.loads(r["messages_json"]) if r["messages_json"] else [],
                    }
                    self._jobs[job["id"]] = job
                    # Mark running -> queued in db
                    if r["status"] == "running":
                        conn.execute(
                            "UPDATE jobs SET status='queued', started_at=NULL WHERE id=?",
                            (r["id"],),
                        )
                conn.commit()
        except Exception as e:  # pragma: no cover
            print(f"[job_queue] failed to load persisted jobs: {e}")

    def _persist(self, job: Dict[str, Any]) -> None:
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO jobs (id, type, status, progress, priority, user_id,
                                      created_at, started_at, finished_at,
                                      result_json, error, messages_json)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET
                        type=excluded.type,
                        status=excluded.status,
                        progress=excluded.progress,
                        priority=excluded.priority,
                        user_id=excluded.user_id,
                        started_at=excluded.started_at,
                        finished_at=excluded.finished_at,
                        result_json=excluded.result_json,
                        error=excluded.error,
                        messages_json=excluded.messages_json
                    """,
                    (
                        job["id"],
                        job.get("type"),
                        job.get("status"),
                        job.get("progress", 0.0),
                        job.get("priority", 1),
                        job.get("user_id"),
                        job.get("created_at"),
                        job.get("started_at"),
                        job.get("finished_at"),
                        json.dumps(job.get("result")) if job.get("result") is not None else None,
                        job.get("error"),
                        json.dumps(job.get("messages") or []),
                    ),
                )
                conn.commit()
        except Exception as e:  # pragma: no cover
            print(f"[job_queue] failed to persist job {job.get('id')}: {e}")

    # --- lifecycle ---

    async def start(self) -> None:
        if self._workers_started:
            return
        self._workers_started = True
        for i in range(self.num_workers):
            asyncio.create_task(self._worker(f"w{i}"))

    async def submit(
        self,
        fn: Callable,
        *,
        priority: int = 1,
        job_type: str = "generic",
        kwargs: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> str:
        job_id = f"{job_type}-{uuid.uuid4().hex[:10]}"
        self._jobs[job_id] = {
            "id": job_id,
            "type": job_type,
            "status": "queued",
            "progress": 0.0,
            "priority": priority,
            "user_id": user_id,
            "created_at": time.time(),
            "started_at": None,
            "finished_at": None,
            "result": None,
            "error": None,
            "messages": [],
        }
        self._persist(self._jobs[job_id])
        async with self._cond:
            heapq.heappush(self._heap, _Entry(priority, next(self._counter), job_id, fn, kwargs or {}))
            self._cond.notify()
        return job_id

    async def _worker(self, name: str) -> None:
        while True:
            async with self._cond:
                while not self._heap:
                    await self._cond.wait()
                entry = heapq.heappop(self._heap)
            job = self._jobs.get(entry.job_id)
            if job is None:
                continue
            job["status"] = "running"
            job["started_at"] = time.time()
            self._persist(job)
            await self._publish(entry.job_id, {"event": "started", "job": job})
            try:
                def on_progress(stage: str, frac: float, msg: str = ""):
                    job["progress"] = float(frac)
                    if msg:
                        job["messages"].append(msg)
                        if len(job["messages"]) > 200:
                            job["messages"] = job["messages"][-200:]
                    # Throttle persistence to ~1Hz
                    now = time.time()
                    last = self._last_progress_persist.get(entry.job_id, 0.0)
                    if now - last >= 1.0:
                        self._last_progress_persist[entry.job_id] = now
                        self._persist(job)
                    # Fire-and-forget publish (from worker thread context)
                    try:
                        asyncio.get_event_loop().create_task(
                            self._publish(entry.job_id, {
                                "event": "progress",
                                "stage": stage,
                                "progress": frac,
                                "message": msg,
                            })
                        )
                    except RuntimeError:
                        pass

                # Run the fn; could be sync or async
                if asyncio.iscoroutinefunction(entry.fn):
                    result = await entry.fn(on_progress=on_progress, **entry.kwargs)
                else:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, lambda: entry.fn(on_progress=on_progress, **entry.kwargs)
                    )
                job["status"] = "completed"
                job["progress"] = 1.0
                job["result"] = result
            except Exception as e:
                job["status"] = "failed"
                job["error"] = str(e)
            finally:
                job["finished_at"] = time.time()
                self._persist(job)
                self._last_progress_persist.pop(entry.job_id, None)
                await self._publish(entry.job_id, {"event": "finished", "job": job})

    # --- pub/sub ---

    async def _publish(self, job_id: str, event: dict) -> None:
        subs = self._subscribers.get(job_id, set())
        for q in list(subs):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def subscribe(self, job_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._subscribers.setdefault(job_id, set()).add(q)
        return q

    def unsubscribe(self, job_id: str, q: asyncio.Queue) -> None:
        if job_id in self._subscribers:
            self._subscribers[job_id].discard(q)

    # --- introspection ---

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)

    def list(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if user_id is None:
            return list(self._jobs.values())
        return [j for j in self._jobs.values() if j.get("user_id") == user_id]

    def stats(self) -> Dict[str, Any]:
        by_status: Dict[str, int] = {}
        for j in self._jobs.values():
            by_status[j["status"]] = by_status.get(j["status"], 0) + 1
        return {
            "workers": self.num_workers,
            "queued": len(self._heap),
            "total": len(self._jobs),
            "by_status": by_status,
        }


_queue: Optional[JobQueue] = None


def get_queue() -> JobQueue:
    global _queue
    if _queue is None:
        _queue = JobQueue(num_workers=int(
            __import__("os").environ.get("OPENDNA_WORKERS", "2")
        ))
    return _queue
