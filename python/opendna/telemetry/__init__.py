"""Opt-in telemetry for OpenDNA.

Nothing is ever written unless OPENDNA_TELEMETRY_CONSENT=1 (or the consent
flag file ~/.opendna/telemetry_consent contains '1'). No PII is captured -
just event names, paths, durations, status codes.
"""
from __future__ import annotations

import json
import os
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict


def _base() -> Path:
    p = Path.home() / ".opendna"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _log_path() -> Path:
    return _base() / "telemetry.jsonl"


def _consent_file() -> Path:
    return _base() / "telemetry_consent"


def has_consent() -> bool:
    if os.environ.get("OPENDNA_TELEMETRY_CONSENT", "0") == "1":
        return True
    f = _consent_file()
    if f.exists():
        try:
            return f.read_text(encoding="utf-8").strip() == "1"
        except Exception:
            return False
    return False


def set_consent(consent: bool) -> Dict[str, Any]:
    f = _consent_file()
    f.write_text("1" if consent else "0", encoding="utf-8")
    return {"consent": bool(consent)}


def record_event(event: str, properties: Dict[str, Any] | None = None) -> bool:
    """Append an event to the jsonl log iff consent is granted."""
    if not has_consent():
        return False
    rec = {
        "ts": time.time(),
        "event": event,
        "properties": properties or {},
    }
    try:
        with _log_path().open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        return True
    except Exception:
        return False


def _iter_events():
    p = _log_path()
    if not p.exists():
        return
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def get_stats(days: int = 30) -> Dict[str, Any]:
    cutoff = time.time() - days * 86400
    top_events: Counter = Counter()
    daily: Dict[str, int] = defaultdict(int)
    feature_heatmap: Dict[str, Counter] = defaultdict(Counter)
    total = 0
    errors = 0
    for rec in _iter_events():
        ts = float(rec.get("ts", 0))
        if ts < cutoff:
            continue
        total += 1
        ev = rec.get("event", "unknown")
        top_events[ev] += 1
        day = time.strftime("%Y-%m-%d", time.localtime(ts))
        daily[day] += 1
        props = rec.get("properties") or {}
        path = props.get("path")
        if path:
            hour = time.strftime("%H", time.localtime(ts))
            feature_heatmap[path][hour] += 1
        sc = props.get("status_code")
        try:
            if sc is not None and int(sc) >= 500:
                errors += 1
        except Exception:
            pass
    return {
        "days": days,
        "total_events": total,
        "error_rate": (errors / total) if total else 0.0,
        "top_events": top_events.most_common(20),
        "daily_counts": dict(sorted(daily.items())),
        "feature_heatmap": {k: dict(v) for k, v in feature_heatmap.items()},
    }


def clear_telemetry() -> Dict[str, Any]:
    p = _log_path()
    existed = p.exists()
    if existed:
        try:
            p.unlink()
        except Exception as e:
            return {"cleared": False, "error": str(e)}
    return {"cleared": True, "existed": existed}


__all__ = [
    "has_consent",
    "set_consent",
    "record_event",
    "get_stats",
    "clear_telemetry",
]
