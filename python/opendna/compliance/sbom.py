"""CycloneDX 1.5 SBOM generator for the running environment."""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


def _list_installed() -> List[Dict[str, Any]]:
    try:
        from importlib.metadata import distributions
    except Exception:
        return []
    out = []
    for dist in distributions():
        try:
            name = dist.metadata["Name"] or ""
            version = dist.version or ""
            if not name:
                continue
            out.append({
                "type": "library",
                "bom-ref": f"pypi:{name}@{version}",
                "name": name,
                "version": version,
                "purl": f"pkg:pypi/{name}@{version}",
                "licenses": [{"license": {"id": dist.metadata.get("License", "unknown") or "unknown"}}],
            })
        except Exception:
            pass
    out.sort(key=lambda c: c["name"].lower())
    return out


def generate_sbom() -> Dict[str, Any]:
    """Return a CycloneDX 1.5 JSON SBOM for the running Python environment."""
    try:
        from opendna import __version__ as v  # type: ignore
    except Exception:
        v = "0.5.0"
    components = _list_installed()
    doc = {
        "$schema": "http://cyclonedx.org/schema/bom-1.5.schema.json",
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tools": [{"vendor": "Dyber, Inc.", "name": "opendna", "version": v}],
            "component": {
                "type": "application",
                "bom-ref": f"opendna@{v}",
                "name": "opendna",
                "version": v,
                "purl": f"pkg:pypi/opendna@{v}",
            },
            "properties": [
                {"name": "python.version", "value": sys.version.split()[0]},
                {"name": "python.platform", "value": platform.platform()},
            ],
        },
        "components": components,
    }
    return doc


def write_sbom_file(out_path: str) -> str:
    doc = generate_sbom()
    Path(out_path).write_text(json.dumps(doc, indent=2))
    return out_path
