"""Local-first crash reporter.

Writes redacted crash dumps to ~/.opendna/crashes/<ts>.json. Optionally
forwards them to a user-configured endpoint (Sentry-compatible) when
OPENDNA_CRASH_ENDPOINT is set. By default, no data leaves the machine.
"""
from __future__ import annotations

import json
import os
import platform
import re
import sys
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


_REDACT_PATTERNS = [
    re.compile(r"(?i)(password|pwd|passwd|token|api[_-]?key|secret|bearer)\s*[:=]\s*[^\s,}]+"),
    re.compile(r"[A-Za-z0-9+/]{40,}={0,2}"),  # base64-ish blobs
]


def _redact(text: str) -> str:
    for p in _REDACT_PATTERNS:
        text = p.sub("<redacted>", text)
    return text


def _crash_dir() -> Path:
    p = Path(os.environ.get("OPENDNA_CRASH_DIR", Path.home() / ".opendna" / "crashes"))
    p.mkdir(parents=True, exist_ok=True)
    return p


class CrashReporter:
    def __init__(self):
        self.endpoint = os.environ.get("OPENDNA_CRASH_ENDPOINT")
        self.consent = os.environ.get("OPENDNA_CRASH_CONSENT", "0") == "1"

    def report(
        self,
        exc: BaseException,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        crash_id = str(uuid.uuid4())
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        record = {
            "id": crash_id,
            "ts": time.time(),
            "version": _opendna_version(),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "exception_type": type(exc).__name__,
            "message": _redact(str(exc)),
            "traceback": _redact(tb),
            "context": context or {},
        }
        path = _crash_dir() / f"{int(record['ts'])}-{crash_id[:8]}.json"
        try:
            path.write_text(json.dumps(record, indent=2))
        except Exception:
            pass

        # Optional remote forwarding (only with explicit consent)
        if self.endpoint and self.consent:
            try:
                import urllib.request
                req = urllib.request.Request(
                    self.endpoint,
                    data=json.dumps(record).encode(),
                    headers={"Content-Type": "application/json"},
                )
                urllib.request.urlopen(req, timeout=5).read()
            except Exception:
                pass
        return crash_id

    def list_crashes(self, limit: int = 50) -> List[Dict[str, Any]]:
        files = sorted(_crash_dir().glob("*.json"), reverse=True)[:limit]
        out = []
        for f in files:
            try:
                out.append(json.loads(f.read_text()))
            except Exception:
                pass
        return out

    def clear(self) -> int:
        n = 0
        for f in _crash_dir().glob("*.json"):
            try:
                f.unlink()
                n += 1
            except Exception:
                pass
        return n


def _opendna_version() -> str:
    try:
        from opendna import __version__  # type: ignore
        return __version__
    except Exception:
        return "0.5.0"


_reporter: Optional[CrashReporter] = None


def get_crash_reporter() -> CrashReporter:
    global _reporter
    if _reporter is None:
        _reporter = CrashReporter()
    return _reporter


def install_excepthook() -> None:
    """Install a sys.excepthook that records crashes before re-raising."""
    prev = sys.excepthook

    def _hook(t, v, tb):
        try:
            get_crash_reporter().report(v)
        except Exception:
            pass
        prev(t, v, tb)

    sys.excepthook = _hook
