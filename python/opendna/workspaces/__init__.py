"""Per-user workspaces with encryption-at-rest (Phase 5).

Layout:
  ~/.opendna/workspaces/<user_id>/
      meta.json          - workspace metadata (owner, created_at, key_wrap)
      projects/*.opendna - encrypted project bundles
      cache/             - scratch

Encryption: AES-256-GCM via the `cryptography` package. The per-workspace
data-key is wrapped by a key derived from the user's password (scrypt) OR
from the host's OS keyring when the user has no password (desktop mode).

If `cryptography` isn't installed, encryption is a no-op passthrough so
dev/CI keeps working. The meta.json records which mode was used.
"""
from .storage import (
    Workspace,
    get_workspace,
    list_user_workspaces,
    encrypt_bytes,
    decrypt_bytes,
    ENCRYPTION_AVAILABLE,
)

__all__ = [
    "Workspace",
    "get_workspace",
    "list_user_workspaces",
    "encrypt_bytes",
    "decrypt_bytes",
    "ENCRYPTION_AVAILABLE",
]
