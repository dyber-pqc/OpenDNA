"""User store backed by SQLite at ~/.opendna/auth.db.

Stores:
  users(user_id PK, pwd_salt, pwd_hash, scopes_json, created_at)
  identities(user_id PK, public_key BLOB, secret_key BLOB, algorithm, created_at)
  api_keys(key_id PK, user_id, key_hash, name, created_at, last_used)

Passwords are hashed with scrypt. Identities are protected at rest by the
OS filesystem ACL; Phase 5 will add encryption-at-rest on top.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import List, Optional

from .pqc import Identity, generate_identity


def _db_path() -> Path:
    root = Path(os.environ.get("OPENDNA_AUTH_DIR", Path.home() / ".opendna"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "auth.db"


def _scrypt(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)


class UserStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = path or _db_path()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._migrate()

    def _migrate(self) -> None:
        c = self.conn.cursor()
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                pwd_salt BLOB,
                pwd_hash BLOB,
                scopes_json TEXT NOT NULL DEFAULT '["user"]',
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS identities (
                user_id TEXT PRIMARY KEY,
                public_key BLOB NOT NULL,
                secret_key BLOB NOT NULL,
                algorithm TEXT NOT NULL,
                created_at REAL NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );
            CREATE TABLE IF NOT EXISTS api_keys (
                key_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                key_hash BLOB NOT NULL,
                name TEXT,
                created_at REAL NOT NULL,
                last_used REAL,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );
            """
        )
        self.conn.commit()

    # --- users ---

    def create_user(
        self,
        user_id: str,
        password: Optional[str] = None,
        scopes: Optional[List[str]] = None,
    ) -> Identity:
        now = time.time()
        salt = secrets.token_bytes(16)
        pwd_hash = _scrypt(password, salt) if password else None
        identity = generate_identity(user_id)
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO users (user_id, pwd_salt, pwd_hash, scopes_json, created_at) VALUES (?,?,?,?,?)",
                (user_id, salt if password else None, pwd_hash, json.dumps(scopes or ["user"]), now),
            )
            self.conn.execute(
                "INSERT OR REPLACE INTO identities (user_id, public_key, secret_key, algorithm, created_at) VALUES (?,?,?,?,?)",
                (user_id, identity.public_key, identity.secret_key, identity.algorithm, now),
            )
        return identity

    def set_password(self, user_id: str, password: str) -> None:
        salt = secrets.token_bytes(16)
        with self.conn:
            self.conn.execute(
                "UPDATE users SET pwd_salt=?, pwd_hash=? WHERE user_id=?",
                (salt, _scrypt(password, salt), user_id),
            )

    def verify_password(self, user_id: str, password: str) -> bool:
        row = self.conn.execute(
            "SELECT pwd_salt, pwd_hash FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        if not row or row[0] is None:
            return False
        return secrets.compare_digest(_scrypt(password, row[0]), row[1])

    def get_identity(self, user_id: str) -> Optional[Identity]:
        row = self.conn.execute(
            "SELECT user_id, public_key, secret_key, algorithm, created_at FROM identities WHERE user_id=?",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        return Identity(
            user_id=row[0],
            public_key=row[1],
            secret_key=row[2],
            algorithm=row[3],
            created_at=row[4],
        )

    def get_user_scopes(self, user_id: str) -> List[str]:
        row = self.conn.execute(
            "SELECT scopes_json FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        if not row:
            return []
        try:
            return list(json.loads(row[0]))
        except Exception:
            return ["user"]

    def list_users(self) -> List[dict]:
        rows = self.conn.execute(
            "SELECT user_id, scopes_json, created_at, pwd_hash IS NOT NULL FROM users"
        ).fetchall()
        return [
            {"user_id": r[0], "scopes": json.loads(r[1]), "created_at": r[2], "has_password": bool(r[3])}
            for r in rows
        ]

    # --- api keys ---

    def create_api_key(self, user_id: str, name: str = "") -> str:
        raw = "opendna_pk_" + secrets.token_urlsafe(32)
        key_id = secrets.token_hex(8)
        key_hash = hashlib.sha256(raw.encode()).digest()
        with self.conn:
            self.conn.execute(
                "INSERT INTO api_keys (key_id, user_id, key_hash, name, created_at) VALUES (?,?,?,?,?)",
                (key_id, user_id, key_hash, name, time.time()),
            )
        return raw

    def verify_api_key(self, raw_key: str) -> Optional[str]:
        h = hashlib.sha256(raw_key.encode()).digest()
        row = self.conn.execute(
            "SELECT key_id, user_id FROM api_keys WHERE key_hash=?", (h,)
        ).fetchone()
        if not row:
            return None
        self.conn.execute(
            "UPDATE api_keys SET last_used=? WHERE key_id=?", (time.time(), row[0])
        )
        self.conn.commit()
        return row[1]


_store: Optional[UserStore] = None


def get_user_store() -> UserStore:
    global _store
    if _store is None:
        _store = UserStore()
    return _store


def create_user(user_id: str, password: Optional[str] = None, scopes: Optional[List[str]] = None) -> Identity:
    return get_user_store().create_user(user_id, password, scopes)


def verify_password(user_id: str, password: str) -> bool:
    return get_user_store().verify_password(user_id, password)


def set_password(user_id: str, password: str) -> None:
    get_user_store().set_password(user_id, password)
