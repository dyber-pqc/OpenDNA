"""Ollama auto-install + streaming + multi-turn memory (Phase 15)."""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional


OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OPENDNA_DEFAULT_MODEL", "llama3.2:3b")


def is_installed() -> bool:
    return shutil.which("ollama") is not None


def is_running() -> bool:
    try:
        urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=2).read()
        return True
    except Exception:
        return False


def auto_install(on_progress=None) -> Dict[str, Any]:
    """Install Ollama via platform-specific installer. Windows/Mac launch
    the official installer; Linux uses the shell install script."""
    if is_installed():
        return {"installed": True, "already": True}
    sysname = platform.system()
    if on_progress:
        on_progress("downloading", 0.1, f"Detecting platform: {sysname}")
    try:
        if sysname == "Linux":
            script = urllib.request.urlopen("https://ollama.com/install.sh", timeout=15).read().decode()
            p = subprocess.run(["sh"], input=script, text=True, capture_output=True)
            ok = p.returncode == 0
            return {"installed": ok, "log": (p.stdout + p.stderr)[-2000:]}
        elif sysname == "Darwin":
            return {
                "installed": False,
                "manual": True,
                "message": "Download Ollama for macOS from https://ollama.com/download",
                "url": "https://ollama.com/download/Ollama-darwin.zip",
            }
        elif sysname == "Windows":
            return {
                "installed": False,
                "manual": True,
                "message": "Download Ollama for Windows from https://ollama.com/download",
                "url": "https://ollama.com/download/OllamaSetup.exe",
            }
    except Exception as e:
        return {"installed": False, "error": str(e)}
    return {"installed": False, "error": "unknown platform"}


def list_local_models() -> List[Dict[str, Any]]:
    try:
        raw = urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=5).read()
        return json.loads(raw).get("models", [])
    except Exception:
        return []


def pull_model(name: str = DEFAULT_MODEL, on_progress=None) -> Dict[str, Any]:
    """Stream a pull request; forward progress lines to callback."""
    if not is_running():
        return {"ok": False, "error": "ollama not running"}
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/pull",
        data=json.dumps({"name": name, "stream": True}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=3600)
        while True:
            line = resp.readline()
            if not line:
                break
            try:
                evt = json.loads(line)
                if on_progress:
                    total = evt.get("total") or 1
                    done = evt.get("completed") or 0
                    on_progress("pull", done / total, evt.get("status", ""))
            except Exception:
                pass
        return {"ok": True, "model": name}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def stream_chat(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    system: Optional[str] = None,
    temperature: float = 0.7,
) -> Generator[str, None, None]:
    """Yield chunks of assistant text from Ollama's streaming /api/chat."""
    if not is_running():
        yield "(Ollama is not running. Start it with `ollama serve` or use the Component Manager.)"
        return
    body: Dict[str, Any] = {
        "model": model,
        "messages": ([{"role": "system", "content": system}] if system else []) + messages,
        "stream": True,
        "options": {"temperature": temperature},
    }
    try:
        req = urllib.request.Request(
            f"{OLLAMA_HOST}/api/chat",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=300)
        while True:
            line = resp.readline()
            if not line:
                break
            try:
                evt = json.loads(line)
                chunk = evt.get("message", {}).get("content", "")
                if chunk:
                    yield chunk
                if evt.get("done"):
                    break
            except Exception:
                continue
    except Exception as e:
        yield f"\n[error: {e}]"


# --- Multi-turn memory per session ---

_SESSIONS: Dict[str, List[Dict[str, str]]] = {}


def session_history(session_id: str) -> List[Dict[str, str]]:
    return list(_SESSIONS.get(session_id, []))


def session_append(session_id: str, role: str, content: str) -> None:
    _SESSIONS.setdefault(session_id, []).append({"role": role, "content": content})
    if len(_SESSIONS[session_id]) > 40:
        _SESSIONS[session_id] = _SESSIONS[session_id][-40:]


def session_clear(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)
