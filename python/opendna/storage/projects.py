"""Project workspace storage: save/load full sessions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from opendna.storage.database import get_data_dir


def projects_dir() -> Path:
    p = get_data_dir() / "projects"
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_project(name: str, data: dict) -> str:
    """Save a project workspace by name. Returns the file path."""
    safe_name = "".join(c for c in name if c.isalnum() or c in "-_") or "untitled"
    proj_dir = projects_dir() / safe_name
    proj_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "name": name,
        "version": "0.2.0",
        "saved_at": datetime.now(timezone.utc).isoformat(),
        **data,
    }

    path = proj_dir / "workspace.json"
    path.write_text(json.dumps(payload, indent=2))
    return str(path)


def load_project(name: str) -> dict | None:
    """Load a project workspace by name."""
    safe_name = "".join(c for c in name if c.isalnum() or c in "-_")
    path = projects_dir() / safe_name / "workspace.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def list_projects() -> list[dict]:
    """List all saved projects with metadata."""
    out = []
    for proj_dir in projects_dir().iterdir():
        if not proj_dir.is_dir():
            continue
        ws = proj_dir / "workspace.json"
        if not ws.exists():
            continue
        try:
            data = json.loads(ws.read_text())
            out.append({
                "name": data.get("name", proj_dir.name),
                "saved_at": data.get("saved_at"),
                "structures": len(data.get("structures", [])),
                "path": str(ws),
            })
        except Exception:
            continue
    out.sort(key=lambda x: x.get("saved_at") or "", reverse=True)
    return out


def delete_project(name: str) -> bool:
    """Delete a project."""
    safe_name = "".join(c for c in name if c.isalnum() or c in "-_")
    proj_dir = projects_dir() / safe_name
    if not proj_dir.exists():
        return False
    import shutil
    shutil.rmtree(proj_dir, ignore_errors=True)
    return True
