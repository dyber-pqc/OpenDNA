"""Post-Quantum Cryptography auth layer for OpenDNA (Phase 4).

Uses NIST-standardized PQC primitives via liboqs-python:
  - ML-KEM-768  (Kyber)    key encapsulation
  - ML-DSA-65   (Dilithium) digital signatures for tokens
  - SLH-DSA-128f (SPHINCS+) hash-based backup signatures

If liboqs is not installed, falls back to a classical HMAC-SHA256
token scheme so the server still works. Audit logs are written
regardless of which backend is active.
"""
from .pqc import (
    PQC_AVAILABLE,
    generate_identity,
    sign_token,
    verify_token,
    kem_encapsulate,
    kem_decapsulate,
)
from .tokens import (
    issue_token,
    validate_token,
    Identity,
    AuthContext,
)
from .audit import AuditLog, get_audit_log
from .users import (
    UserStore,
    get_user_store,
    create_user,
    verify_password,
    set_password,
)

__all__ = [
    "PQC_AVAILABLE",
    "generate_identity",
    "sign_token",
    "verify_token",
    "kem_encapsulate",
    "kem_decapsulate",
    "issue_token",
    "validate_token",
    "Identity",
    "AuthContext",
    "AuditLog",
    "get_audit_log",
    "UserStore",
    "get_user_store",
    "create_user",
    "verify_password",
    "set_password",
]
