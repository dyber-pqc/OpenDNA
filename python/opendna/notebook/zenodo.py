"""Zenodo DOI minting for OpenDNA project exports.

Requires ZENODO_ACCESS_TOKEN env var. Without it, records the deposit locally
and returns a "draft" so the flow still works end-to-end for demos.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


ZENODO_BASE = os.environ.get("ZENODO_API_URL", "https://zenodo.org/api")


def _deposits_dir() -> Path:
    p = Path(os.environ.get("OPENDNA_DEPOSITS_DIR", Path.home() / ".opendna" / "deposits"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def _post_json(url: str, data: dict, token: str) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode())


def mint_doi_zenodo(
    title: str,
    description: str,
    creators: List[str],
    files: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    upload_type: str = "software",
) -> Dict[str, Any]:
    token = os.environ.get("ZENODO_ACCESS_TOKEN")
    deposit_id = uuid.uuid4().hex[:12]
    record = {
        "local_id": deposit_id,
        "title": title,
        "description": description,
        "creators": creators,
        "keywords": keywords or [],
        "upload_type": upload_type,
        "ts": time.time(),
        "files": files or [],
        "status": "draft",
        "submitted": bool(token),
    }

    if not token:
        (_deposits_dir() / f"{deposit_id}.json").write_text(json.dumps(record, indent=2))
        record["note"] = "Set ZENODO_ACCESS_TOKEN to mint a real DOI"
        return record

    try:
        meta = {
            "metadata": {
                "title": title,
                "description": description,
                "upload_type": upload_type,
                "creators": [{"name": c} for c in creators],
                "keywords": keywords or [],
                "access_right": "open",
                "license": "apache2.0",
            }
        }
        resp = _post_json(f"{ZENODO_BASE}/deposit/depositions?access_token={token}", meta, token)
        record["deposit_id"] = resp.get("id")
        record["doi"] = resp.get("metadata", {}).get("prereserve_doi", {}).get("doi")
        record["zenodo_url"] = resp.get("links", {}).get("html")
        record["status"] = "created"
        # File upload intentionally left to the user — it needs multipart which
        # we keep out of the core to avoid dependencies.
    except Exception as e:
        record["status"] = "failed"
        record["error"] = str(e)
    (_deposits_dir() / f"{deposit_id}.json").write_text(json.dumps(record, indent=2))
    return record


def list_local_deposits() -> List[Dict[str, Any]]:
    out = []
    for f in sorted(_deposits_dir().glob("*.json"), reverse=True):
        try:
            out.append(json.loads(f.read_text()))
        except Exception:
            pass
    return out
