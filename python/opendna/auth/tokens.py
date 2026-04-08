"""PQC-signed session tokens.

Token format (compact, base64url):
    <header_b64>.<payload_b64>.<signature_b64>

where:
    header  = {"alg": "ML-DSA-65", "typ": "opendna-pqc"}
    payload = {"sub": user_id, "iat": ..., "exp": ..., "scopes": [...], "nonce": ...}

Validation uses the user's stored public key from the UserStore.
"""
from __future__ import annotations

import base64
import dataclasses
import json
import secrets
import time
from dataclasses import dataclass
from typing import List, Optional

from .pqc import (
    ALG_SIG,
    PQC_AVAILABLE,
    Identity,
    sign_token,
    verify_token,
    verify_hmac,
)


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64u_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


@dataclass
class AuthContext:
    """Who is making this request."""
    user_id: str
    scopes: List[str]
    algorithm: str
    token_exp: float
    is_pqc: bool

    def has_scope(self, scope: str) -> bool:
        return "admin" in self.scopes or scope in self.scopes


def issue_token(
    identity: Identity,
    scopes: Optional[List[str]] = None,
    ttl_seconds: int = 3600 * 12,
) -> str:
    now = time.time()
    header = {
        "alg": identity.algorithm,
        "typ": "opendna-pqc" if PQC_AVAILABLE else "opendna-hmac",
    }
    payload = {
        "sub": identity.user_id,
        "iat": now,
        "exp": now + ttl_seconds,
        "scopes": scopes or ["user"],
        "nonce": secrets.token_hex(8),
    }
    h = _b64u(json.dumps(header, separators=(",", ":")).encode())
    p = _b64u(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{h}.{p}".encode()
    sig = sign_token(identity, signing_input)
    return f"{h}.{p}.{_b64u(sig)}"


def validate_token(
    token: str,
    resolve_identity,  # Callable[[user_id], Optional[Identity]]
) -> Optional[AuthContext]:
    """Validate a token. `resolve_identity` returns the stored Identity for `sub`."""
    try:
        h_b64, p_b64, s_b64 = token.split(".")
        header = json.loads(_b64u_decode(h_b64))
        payload = json.loads(_b64u_decode(p_b64))
        signature = _b64u_decode(s_b64)
    except Exception:
        return None

    if payload.get("exp", 0) < time.time():
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    identity = resolve_identity(user_id)
    if identity is None:
        return None

    signing_input = f"{h_b64}.{p_b64}".encode()
    alg = header.get("alg", "")
    ok = False
    if alg == ALG_SIG and PQC_AVAILABLE:
        ok = verify_token(identity.public_key, signing_input, signature, algorithm=ALG_SIG)
    elif alg == "HMAC-SHA256-fallback":
        ok = verify_hmac(identity.secret_key, signing_input, signature)

    if not ok:
        return None

    return AuthContext(
        user_id=user_id,
        scopes=list(payload.get("scopes", [])),
        algorithm=alg,
        token_exp=float(payload.get("exp", 0)),
        is_pqc=(alg == ALG_SIG and PQC_AVAILABLE),
    )
