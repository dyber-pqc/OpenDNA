"""Low-level PQC primitives: ML-KEM-768 and ML-DSA-65 via liboqs.

Graceful fallback to HMAC-SHA256 (classical) if liboqs is not installed,
so development and CI keep working. The fallback is clearly labeled in
tokens so production deployments can reject non-PQC sessions.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from typing import Optional, Tuple


# NIST PQC algorithm names per liboqs
ALG_SIG = "ML-DSA-65"        # Dilithium (digital signatures)
ALG_KEM = "ML-KEM-768"       # Kyber   (key exchange)
ALG_SIG_BACKUP = "SPHINCS+-SHA2-128f-simple"  # hash-based backup

try:  # pragma: no cover - optional dependency
    import oqs  # type: ignore
    PQC_AVAILABLE = True
except Exception:
    oqs = None  # type: ignore
    PQC_AVAILABLE = False


@dataclass
class Identity:
    """A PQC (or fallback) identity consisting of a signing keypair."""
    user_id: str
    public_key: bytes
    secret_key: bytes
    algorithm: str
    created_at: float

    def to_public_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "public_key": base64.b64encode(self.public_key).decode(),
            "algorithm": self.algorithm,
            "created_at": self.created_at,
        }


def generate_identity(user_id: str) -> Identity:
    """Generate a fresh signing keypair for this user."""
    import time
    if PQC_AVAILABLE:
        sig = oqs.Signature(ALG_SIG)  # type: ignore
        public_key = sig.generate_keypair()
        secret_key = sig.export_secret_key()
        sig.free()
        return Identity(
            user_id=user_id,
            public_key=public_key,
            secret_key=secret_key,
            algorithm=ALG_SIG,
            created_at=time.time(),
        )
    # Classical HMAC fallback: "secret_key" is the shared secret.
    secret = secrets.token_bytes(32)
    return Identity(
        user_id=user_id,
        public_key=hashlib.sha256(secret).digest(),
        secret_key=secret,
        algorithm="HMAC-SHA256-fallback",
        created_at=time.time(),
    )


def sign_token(identity: Identity, message: bytes) -> bytes:
    """Sign `message` with the identity's secret key."""
    if PQC_AVAILABLE and identity.algorithm == ALG_SIG:
        sig = oqs.Signature(ALG_SIG, identity.secret_key)  # type: ignore
        try:
            signature = sig.sign(message)
        finally:
            sig.free()
        return signature
    # Fallback: HMAC
    return hmac.new(identity.secret_key, message, hashlib.sha256).digest()


def verify_token(
    public_key: bytes,
    message: bytes,
    signature: bytes,
    algorithm: str = ALG_SIG,
) -> bool:
    if PQC_AVAILABLE and algorithm == ALG_SIG:
        verifier = oqs.Signature(ALG_SIG)  # type: ignore
        try:
            return bool(verifier.verify(message, signature, public_key))
        finally:
            verifier.free()
    if algorithm == "HMAC-SHA256-fallback":
        # public_key is sha256(secret); we can't recompute HMAC without secret.
        # For fallback mode, the token-validation path must use the secret key
        # directly via validate_token().
        return False
    return False


def verify_hmac(secret: bytes, message: bytes, signature: bytes) -> bool:
    expected = hmac.new(secret, message, hashlib.sha256).digest()
    return hmac.compare_digest(expected, signature)


def kem_encapsulate(peer_public_key: bytes) -> Tuple[bytes, bytes]:
    """ML-KEM-768 encapsulate. Returns (ciphertext, shared_secret)."""
    if PQC_AVAILABLE:
        client = oqs.KeyEncapsulation(ALG_KEM)  # type: ignore
        try:
            ciphertext, shared_secret = client.encap_secret(peer_public_key)
            return ciphertext, shared_secret
        finally:
            client.free()
    # Fallback: plain random shared secret hashed with peer pk
    shared = secrets.token_bytes(32)
    ct = hashlib.sha256(peer_public_key + shared).digest()
    return ct, shared


def kem_decapsulate(secret_key: bytes, ciphertext: bytes) -> bytes:
    if PQC_AVAILABLE:
        server = oqs.KeyEncapsulation(ALG_KEM, secret_key)  # type: ignore
        try:
            return server.decap_secret(ciphertext)
        finally:
            server.free()
    return hashlib.sha256(ciphertext + secret_key).digest()


def kem_generate_keypair() -> Tuple[bytes, bytes]:
    if PQC_AVAILABLE:
        kem = oqs.KeyEncapsulation(ALG_KEM)  # type: ignore
        try:
            pk = kem.generate_keypair()
            sk = kem.export_secret_key()
            return pk, sk
        finally:
            kem.free()
    sk = secrets.token_bytes(32)
    pk = hashlib.sha256(sk).digest()
    return pk, sk
