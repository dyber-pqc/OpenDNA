"""Per-user workspace storage + AES-256-GCM encryption-at-rest."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore
    ENCRYPTION_AVAILABLE = True
except Exception:
    AESGCM = None  # type: ignore
    ENCRYPTION_AVAILABLE = False


def _workspaces_root() -> Path:
    root = Path(os.environ.get("OPENDNA_WORKSPACES_DIR", Path.home() / ".opendna" / "workspaces"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _derive_key(material: bytes, salt: bytes) -> bytes:
    return hashlib.scrypt(material, salt=salt, n=2**14, r=8, p=1, dklen=32)


def encrypt_bytes(data: bytes, key: bytes) -> bytes:
    """AES-256-GCM encrypt. Prefixes 12-byte nonce. Passthrough if unavailable."""
    if not ENCRYPTION_AVAILABLE:
        return b"PLAIN" + data
    nonce = secrets.token_bytes(12)
    ct = AESGCM(key).encrypt(nonce, data, None)  # type: ignore
    return b"AESG" + nonce + ct


def decrypt_bytes(blob: bytes, key: bytes) -> bytes:
    if blob[:5] == b"PLAIN":
        return blob[5:]
    if blob[:4] == b"AESG":
        if not ENCRYPTION_AVAILABLE:
            raise RuntimeError("Encrypted blob but `cryptography` is not installed")
        nonce = blob[4:16]
        ct = blob[16:]
        return AESGCM(key).decrypt(nonce, ct, None)  # type: ignore
    raise ValueError("Unknown blob format")


@dataclass
class WorkspaceMeta:
    user_id: str
    name: str
    created_at: float
    encrypted: bool
    key_salt_hex: str  # scrypt salt for deriving data-key from password
    wrap_check_hex: str  # ciphertext of a fixed plaintext; used to verify password


class Workspace:
    def __init__(self, root: Path, meta: WorkspaceMeta, data_key: Optional[bytes] = None):
        self.root = root
        self.meta = meta
        self._data_key = data_key

    @property
    def projects_dir(self) -> Path:
        p = self.root / "projects"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def cache_dir(self) -> Path:
        p = self.root / "cache"
        p.mkdir(parents=True, exist_ok=True)
        return p

    # --- project CRUD ---

    def save_project(self, name: str, payload: dict) -> Path:
        data = json.dumps(payload).encode()
        key = self._data_key or b"\x00" * 32
        enc = encrypt_bytes(data, key)
        path = self.projects_dir / f"{name}.opendna"
        path.write_bytes(enc)
        return path

    def load_project(self, name: str) -> dict:
        path = self.projects_dir / f"{name}.opendna"
        blob = path.read_bytes()
        key = self._data_key or b"\x00" * 32
        return json.loads(decrypt_bytes(blob, key).decode())

    def list_projects(self) -> List[dict]:
        out = []
        for f in self.projects_dir.glob("*.opendna"):
            out.append({
                "name": f.stem,
                "size_bytes": f.stat().st_size,
                "modified": f.stat().st_mtime,
            })
        return out

    def delete_project(self, name: str) -> bool:
        path = self.projects_dir / f"{name}.opendna"
        if path.exists():
            path.unlink()
            return True
        return False


def _meta_path(root: Path) -> Path:
    return root / "meta.json"


def get_workspace(user_id: str, password: Optional[str] = None, name: str = "default") -> Workspace:
    """Open or create a workspace. If `password` is given and encryption is
    available, data-key is derived from it; otherwise a random zero key is used."""
    root = _workspaces_root() / user_id / name
    root.mkdir(parents=True, exist_ok=True)
    meta_p = _meta_path(root)

    if meta_p.exists():
        raw = json.loads(meta_p.read_text())
        meta = WorkspaceMeta(**raw)
        if meta.encrypted and password and ENCRYPTION_AVAILABLE:
            salt = bytes.fromhex(meta.key_salt_hex)
            key = _derive_key(password.encode(), salt)
            # Verify key via wrap_check blob
            try:
                decrypt_bytes(bytes.fromhex(meta.wrap_check_hex), key)
            except Exception as e:
                raise PermissionError("Wrong password for workspace") from e
            return Workspace(root, meta, data_key=key)
        return Workspace(root, meta, data_key=None)

    # Create fresh
    salt = secrets.token_bytes(16)
    if password and ENCRYPTION_AVAILABLE:
        key = _derive_key(password.encode(), salt)
        wrap_check = encrypt_bytes(b"opendna-workspace-v1", key).hex()
        encrypted = True
    else:
        key = None
        wrap_check = ""
        encrypted = False
    meta = WorkspaceMeta(
        user_id=user_id,
        name=name,
        created_at=time.time(),
        encrypted=encrypted,
        key_salt_hex=salt.hex(),
        wrap_check_hex=wrap_check,
    )
    meta_p.write_text(json.dumps(asdict(meta)))
    return Workspace(root, meta, data_key=key)


def list_user_workspaces(user_id: str) -> List[Dict]:
    root = _workspaces_root() / user_id
    if not root.exists():
        return []
    out = []
    for ws in root.iterdir():
        mp = _meta_path(ws)
        if mp.exists():
            meta = json.loads(mp.read_text())
            meta["path"] = str(ws)
            out.append(meta)
    return out
