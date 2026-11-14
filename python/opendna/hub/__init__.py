"""OpenDNA Hub - LOCAL STUB.

A pretend "GitHub for proteins" that stores everything under
``~/.opendna/hub_local/``. No network calls; the "hub URL" is a made-up
``opendna://local/<user>/<project>`` scheme that this module fully owns.

Provides publish, list, fork, and a minimal pull-request workflow.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List


def _hub_root() -> Path:
    root = Path(os.path.expanduser("~/.opendna/hub_local"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _pr_db() -> Path:
    p = _hub_root() / "pull_requests.db"
    with sqlite3.connect(str(p)) as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS prs (
                   id TEXT PRIMARY KEY,
                   source TEXT NOT NULL,
                   target TEXT NOT NULL,
                   message TEXT NOT NULL,
                   status TEXT NOT NULL,
                   created_at REAL NOT NULL
               )"""
        )
    return p


def _project_dir(user_id: str, project_name: str) -> Path:
    safe_user = "".join(ch for ch in user_id if ch.isalnum() or ch in "-_.") or "anon"
    safe_proj = "".join(ch for ch in project_name if ch.isalnum() or ch in "-_.") or "untitled"
    d = _hub_root() / safe_user / safe_proj
    d.mkdir(parents=True, exist_ok=True)
    return d


def _hub_url(user_id: str, project_name: str) -> str:
    return f"opendna://local/{user_id}/{project_name}"


def publish_project(
    user_id: str, project_name: str, pdb_string: str, description: str
) -> Dict[str, Any]:
    """Publish a project to the local hub; returns metadata including hub_url."""
    d = _project_dir(user_id, project_name)
    (d / "structure.pdb").write_text(pdb_string or "", encoding="utf-8")
    meta = {
        "user_id": user_id,
        "project_name": project_name,
        "description": description,
        "hub_url": _hub_url(user_id, project_name),
        "published_at": time.time(),
        "visibility": "public",
    }
    (d / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def list_public_projects() -> List[Dict[str, Any]]:
    """Scan the hub root and return all public project metas."""
    out: List[Dict[str, Any]] = []
    root = _hub_root()
    if not root.exists():
        return out
    for user_dir in root.iterdir():
        if not user_dir.is_dir():
            continue
        for proj_dir in user_dir.iterdir():
            if not proj_dir.is_dir():
                continue
            meta_path = proj_dir / "meta.json"
            if meta_path.exists():
                try:
                    out.append(json.loads(meta_path.read_text(encoding="utf-8")))
                except Exception:
                    continue
    out.sort(key=lambda m: m.get("published_at", 0), reverse=True)
    return out


def _parse_url(hub_url: str) -> Dict[str, str]:
    # opendna://local/<user>/<project>
    prefix = "opendna://local/"
    if not hub_url.startswith(prefix):
        raise ValueError(f"Not a hub URL: {hub_url}")
    rest = hub_url[len(prefix) :]
    parts = rest.split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Malformed hub URL: {hub_url}")
    return {"user_id": parts[0], "project_name": parts[1]}


def fork_project(hub_url: str, new_user_id: str) -> Dict[str, Any]:
    """Copy a project under a new user namespace and return the new meta."""
    src = _parse_url(hub_url)
    src_dir = _project_dir(src["user_id"], src["project_name"])
    meta_path = src_dir / "meta.json"
    if not meta_path.exists():
        raise ValueError(f"Project not found: {hub_url}")
    src_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    pdb_path = src_dir / "structure.pdb"
    pdb = pdb_path.read_text(encoding="utf-8") if pdb_path.exists() else ""
    new_meta = publish_project(
        new_user_id,
        src["project_name"],
        pdb,
        f"Forked from {hub_url}: {src_meta.get('description', '')}",
    )
    new_meta["forked_from"] = hub_url
    (_project_dir(new_user_id, src["project_name"]) / "meta.json").write_text(
        json.dumps(new_meta, indent=2), encoding="utf-8"
    )
    return new_meta


def open_pull_request(source: str, target: str, message: str) -> Dict[str, Any]:
    """Record a PR between two hub URLs. Returns {pr_id, ...}."""
    pr_id = f"pr_{uuid.uuid4().hex[:10]}"
    ts = time.time()
    with sqlite3.connect(str(_pr_db())) as c:
        c.execute(
            "INSERT INTO prs (id, source, target, message, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (pr_id, source, target, message, "open", ts),
        )
    return {
        "pr_id": pr_id,
        "source": source,
        "target": target,
        "message": message,
        "status": "open",
        "created_at": ts,
    }


def list_pull_requests(project: str) -> List[Dict[str, Any]]:
    """List PRs whose source OR target matches the given hub URL (or substring)."""
    with sqlite3.connect(str(_pr_db())) as c:
        rows = c.execute(
            "SELECT id, source, target, message, status, created_at FROM prs "
            "WHERE source LIKE ? OR target LIKE ? ORDER BY created_at DESC",
            (f"%{project}%", f"%{project}%"),
        ).fetchall()
    return [
        {
            "pr_id": r[0],
            "source": r[1],
            "target": r[2],
            "message": r[3],
            "status": r[4],
            "created_at": r[5],
        }
        for r in rows
    ]
