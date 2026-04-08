"""Install / uninstall / status for heavy components.

Supports four install kinds:
  - pip:    `pip install <target>`
  - hf:     download a HuggingFace repo via huggingface_hub into the HF cache
  - script: run a repo-specific install script (for RFdiffusion, etc.)
  - ollama: `ollama pull <model>`

Each install runs as a subprocess so the main API server stays responsive.
Progress is streamed via an optional callback.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable, Dict, Optional

from .registry import Component, get_component, list_components


ProgressCb = Callable[[str, float, str], None]  # (component_name, pct, message)


def _component_marker(name: str) -> Path:
    root = Path.home() / ".opendna" / "components"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{name}.installed"


def get_status(name: str) -> str:
    """Return: 'installed' | 'not_installed' | 'unknown'."""
    c = get_component(name)
    if c is None:
        return "unknown"
    # Marker file wins (set after successful install)
    if _component_marker(name).exists():
        return "installed"
    # Try an import check if provided
    if c.import_check:
        try:
            exec(c.import_check, {})
            return "installed"
        except Exception:
            return "not_installed"
    return "not_installed"


def total_disk_usage() -> int:
    """Return the rough total MB used by installed components (from registry sizes)."""
    return sum(c.size_mb for c in list_components() if get_status(c.name) == "installed")


def _run(cmd: list[str], on_progress: Optional[ProgressCb], name: str) -> int:
    """Run a subprocess, forwarding output lines to the progress callback."""
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    pct = 0.0
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        if on_progress:
            # Heuristic: look for "%" in the line and parse it; else just bump
            if "%" in line:
                try:
                    tok = line.split("%")[0].split()[-1]
                    pct = max(pct, min(99.0, float(tok)))
                except Exception:
                    pass
            on_progress(name, pct, line)
    proc.wait()
    return proc.returncode


def install_component(
    name: str,
    on_progress: Optional[ProgressCb] = None,
) -> Dict[str, str]:
    """Install a component. Blocking; run on a worker thread from the API."""
    c = get_component(name)
    if c is None:
        raise ValueError(f"Unknown component: {name}")

    if get_status(name) == "installed":
        return {"status": "already_installed", "component": name}

    if on_progress:
        on_progress(name, 0.0, f"Starting install of {c.display_name}")

    rc = 1
    if c.install_kind == "pip":
        rc = _run(
            [sys.executable, "-m", "pip", "install", "--upgrade", c.install_target],
            on_progress, name,
        )
    elif c.install_kind == "hf":
        # Use huggingface_hub CLI via python -m
        try:
            import huggingface_hub  # noqa: F401
        except ImportError:
            _run([sys.executable, "-m", "pip", "install", "huggingface_hub"], on_progress, name)
        rc = _run(
            [
                sys.executable, "-m", "huggingface_hub.commands.huggingface_cli",
                "download", c.install_target,
            ],
            on_progress, name,
        )
    elif c.install_kind == "ollama":
        if not shutil.which("ollama"):
            if on_progress:
                on_progress(name, 0.0, "Ollama not found on PATH. Install from https://ollama.com first.")
            return {"status": "error", "component": name, "message": "ollama binary missing"}
        rc = _run(["ollama", "pull", c.install_target], on_progress, name)
    elif c.install_kind == "script":
        # For RFdiffusion-style installs. We try pip first as a best effort.
        rc = _run([sys.executable, "-m", "pip", "install", c.install_target], on_progress, name)
        if rc != 0 and on_progress:
            on_progress(name, 0.0, f"Scripted install of {c.display_name} requires manual steps. See {c.homepage}")
    else:
        raise ValueError(f"Unknown install_kind: {c.install_kind}")

    if rc == 0:
        _component_marker(name).write_text("ok")
        if on_progress:
            on_progress(name, 100.0, f"{c.display_name} installed")
        return {"status": "installed", "component": name}

    return {"status": "error", "component": name, "message": f"exit code {rc}"}


def uninstall_component(name: str) -> Dict[str, str]:
    c = get_component(name)
    if c is None:
        raise ValueError(f"Unknown component: {name}")
    marker = _component_marker(name)
    if marker.exists():
        marker.unlink()
    if c.install_kind == "pip":
        _run([sys.executable, "-m", "pip", "uninstall", "-y", c.install_target.split(">=")[0].split("==")[0]], None, name)
    return {"status": "uninstalled", "component": name}
