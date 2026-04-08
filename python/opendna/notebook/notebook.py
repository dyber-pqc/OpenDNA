"""Markdown-based lab notebook with structured entries.

Stored at ~/.opendna/notebooks/<project_id>/ as .md files plus a small
meta.json index. Each entry has YAML front-matter with timestamp, tags,
linked provenance nodes, and attachments.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


def _nb_root() -> Path:
    p = Path(os.environ.get("OPENDNA_NOTEBOOK_DIR", Path.home() / ".opendna" / "notebooks"))
    p.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class Entry:
    id: str
    project_id: str
    title: str
    body_md: str
    ts: float
    tags: List[str] = field(default_factory=list)
    prov_node_ids: List[str] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)
    author: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        fm = {
            "id": self.id, "project_id": self.project_id, "title": self.title,
            "ts": self.ts, "tags": self.tags, "prov_node_ids": self.prov_node_ids,
            "attachments": self.attachments, "author": self.author,
        }
        fm_json = json.dumps(fm, indent=2)
        return f"---\n{fm_json}\n---\n\n# {self.title}\n\n{self.body_md}\n"


class LabNotebook:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.root = _nb_root() / project_id
        self.root.mkdir(parents=True, exist_ok=True)
        self.entries_dir = self.root / "entries"
        self.entries_dir.mkdir(exist_ok=True)
        self.attach_dir = self.root / "attachments"
        self.attach_dir.mkdir(exist_ok=True)

    def add_entry(
        self,
        title: str,
        body_md: str,
        tags: Optional[List[str]] = None,
        prov_node_ids: Optional[List[str]] = None,
        author: Optional[str] = None,
    ) -> Entry:
        entry = Entry(
            id=uuid.uuid4().hex[:12],
            project_id=self.project_id,
            title=title,
            body_md=body_md,
            ts=time.time(),
            tags=tags or [],
            prov_node_ids=prov_node_ids or [],
            author=author,
        )
        (self.entries_dir / f"{int(entry.ts)}-{entry.id}.md").write_text(entry.to_markdown(), encoding="utf-8")
        return entry

    def list_entries(self) -> List[Dict[str, Any]]:
        out = []
        for f in sorted(self.entries_dir.glob("*.md")):
            try:
                text = f.read_text(encoding="utf-8")
                if text.startswith("---\n"):
                    meta_end = text.find("\n---", 4)
                    meta = json.loads(text[4:meta_end])
                    meta["_file"] = str(f)
                    out.append(meta)
            except Exception:
                pass
        return out

    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        for f in self.entries_dir.glob(f"*-{entry_id}.md"):
            text = f.read_text(encoding="utf-8")
            if text.startswith("---\n"):
                meta_end = text.find("\n---", 4)
                meta = json.loads(text[4:meta_end])
                meta["body_md"] = text[meta_end + 4:].lstrip()
                return meta
        return None

    def attach(self, filename: str, data: bytes) -> str:
        p = self.attach_dir / filename
        p.write_bytes(data)
        return str(p)


_cache: Dict[str, LabNotebook] = {}


def get_notebook(project_id: str) -> LabNotebook:
    if project_id not in _cache:
        _cache[project_id] = LabNotebook(project_id)
    return _cache[project_id]
