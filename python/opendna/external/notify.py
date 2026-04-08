"""Slack/Teams/Discord notifications + generic webhook fan-out."""
from __future__ import annotations

import json
import os
import sqlite3
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


def _wh_db() -> Path:
    p = Path(os.environ.get("OPENDNA_AUTH_DIR", Path.home() / ".opendna"))
    p.mkdir(parents=True, exist_ok=True)
    return p / "webhooks.db"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_wh_db(), check_same_thread=False)
    c.execute(
        """CREATE TABLE IF NOT EXISTS webhooks (
              id TEXT PRIMARY KEY,
              url TEXT NOT NULL,
              event TEXT,
              secret TEXT,
              created_at REAL,
              last_fired REAL,
              fire_count INTEGER NOT NULL DEFAULT 0
        )"""
    )
    return c


def _post_json(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> bool:
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", **(headers or {})},
        )
        urllib.request.urlopen(req, timeout=8).read()
        return True
    except Exception:
        return False


def notify_slack(text: str, webhook_url: Optional[str] = None) -> bool:
    url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        return False
    return _post_json(url, {"text": text})


def notify_teams(text: str, webhook_url: Optional[str] = None) -> bool:
    url = webhook_url or os.environ.get("TEAMS_WEBHOOK_URL")
    if not url:
        return False
    return _post_json(url, {"@type": "MessageCard", "text": text})


def notify_discord(text: str, webhook_url: Optional[str] = None) -> bool:
    url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        return False
    return _post_json(url, {"content": text})


def register_webhook(url: str, event: str = "*", secret: Optional[str] = None) -> str:
    wid = uuid.uuid4().hex[:12]
    with _conn() as c:
        c.execute(
            "INSERT INTO webhooks (id, url, event, secret, created_at, fire_count) VALUES (?,?,?,?,?,0)",
            (wid, url, event, secret, time.time()),
        )
    return wid


def list_webhooks() -> List[Dict[str, Any]]:
    rows = _conn().execute(
        "SELECT id, url, event, created_at, last_fired, fire_count FROM webhooks"
    ).fetchall()
    return [
        {"id": r[0], "url": r[1], "event": r[2], "created_at": r[3], "last_fired": r[4], "fire_count": r[5]}
        for r in rows
    ]


def delete_webhook(wid: str) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM webhooks WHERE id=?", (wid,))
    return cur.rowcount > 0


def fire_webhooks(event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send `payload` to every webhook subscribed to `event` (or '*')."""
    rows = _conn().execute(
        "SELECT id, url, secret FROM webhooks WHERE event=? OR event='*'", (event,)
    ).fetchall()
    delivered, failed = 0, 0
    for wid, url, secret in rows:
        body = {"event": event, "payload": payload, "ts": time.time()}
        headers = {}
        if secret:
            import hashlib, hmac
            sig = hmac.new(secret.encode(), json.dumps(body).encode(), hashlib.sha256).hexdigest()
            headers["X-OpenDNA-Signature"] = f"sha256={sig}"
        ok = _post_json(url, body, headers)
        if ok:
            delivered += 1
        else:
            failed += 1
        with _conn() as c:
            c.execute("UPDATE webhooks SET last_fired=?, fire_count=fire_count+1 WHERE id=?", (time.time(), wid))
    return {"delivered": delivered, "failed": failed, "total": len(rows)}
