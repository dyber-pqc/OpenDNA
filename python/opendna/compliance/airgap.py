"""Air-gapped deployment helpers."""
from __future__ import annotations

import os
import platform
import shutil
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List


def check_airgap_capability() -> Dict[str, Any]:
    """Diagnostic: can this install run fully offline?"""
    report: Dict[str, Any] = {
        "internet_reachable": False,
        "ollama_local": shutil.which("ollama") is not None,
        "esmfold_cached": False,
        "bundled_sidecar": False,
        "components_installed": [],
    }
    try:
        urllib.request.urlopen("https://www.google.com", timeout=2).read()
        report["internet_reachable"] = True
    except Exception:
        pass
    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
    if hf_cache.exists():
        report["esmfold_cached"] = any(
            "esmfold" in str(p).lower() for p in hf_cache.glob("**/*")
        )
    try:
        from opendna.components import list_components, get_status
        for c in list_components():
            if get_status(c.name) == "installed":
                report["components_installed"].append(c.name)
    except Exception:
        pass
    report["airgap_ready"] = (
        bool(report["components_installed"])
        and (report["esmfold_cached"] or "esmfold" in report["components_installed"])
    )
    return report


def bundle_offline_artifacts(out_dir: str) -> Dict[str, Any]:
    """Copy everything needed for an air-gapped install into `out_dir`."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    bundled: List[str] = []

    # 1. SBOM
    from opendna.compliance.sbom import write_sbom_file
    sbom_path = out / "sbom.cdx.json"
    write_sbom_file(str(sbom_path))
    bundled.append("sbom.cdx.json")

    # 2. Marker manifest
    manifest = {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "bundled_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (out / "manifest.json").write_text(__import__("json").dumps(manifest, indent=2))
    bundled.append("manifest.json")

    # 3. README instructions
    readme = f"""OpenDNA Air-Gapped Bundle
=========================
Platform: {manifest['platform']}
Python:   {manifest['python']}

To install on an offline machine:
  1. Copy this entire directory to the target machine
  2. pip install --no-index --find-links . opendna
  3. Copy ~/.cache/huggingface to the target machine (for ESMFold weights)
  4. Copy ~/.opendna/components/ markers to opt out of re-downloads
"""
    (out / "README.txt").write_text(readme)
    bundled.append("README.txt")

    return {"out_dir": str(out), "bundled": bundled}
