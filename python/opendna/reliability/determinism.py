"""Deterministic output helpers: seed pinning + input hashing."""
from __future__ import annotations

import functools
import hashlib
import json
import os
import random
from typing import Any, Callable

_CURRENT_SEED: int = 42


def set_global_seed(seed: int = 42) -> int:
    """Seed Python random, numpy, torch CPU+CUDA, and PYTHONHASHSEED."""
    global _CURRENT_SEED
    _CURRENT_SEED = int(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    try:
        import numpy as np  # type: ignore
        np.random.seed(seed)
    except Exception:
        pass
    try:
        import torch  # type: ignore
        torch.manual_seed(seed)
        if hasattr(torch, "cuda") and torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        if hasattr(torch, "use_deterministic_algorithms"):
            try:
                torch.use_deterministic_algorithms(True, warn_only=True)
            except Exception:
                pass
    except Exception:
        pass
    return _CURRENT_SEED


def get_current_seed() -> int:
    return _CURRENT_SEED


def hash_inputs(**kwargs: Any) -> str:
    """SHA256 of canonical JSON representation of kwargs."""
    blob = json.dumps(kwargs, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _snapshot_state() -> dict:
    st: dict = {"py": random.getstate()}
    try:
        import numpy as np  # type: ignore
        st["np"] = np.random.get_state()
    except Exception:
        pass
    try:
        import torch  # type: ignore
        st["torch"] = torch.get_rng_state()
    except Exception:
        pass
    return st


def _restore_state(st: dict) -> None:
    try:
        random.setstate(st["py"])
    except Exception:
        pass
    if "np" in st:
        try:
            import numpy as np  # type: ignore
            np.random.set_state(st["np"])
        except Exception:
            pass
    if "torch" in st:
        try:
            import torch  # type: ignore
            torch.set_rng_state(st["torch"])
        except Exception:
            pass


def deterministic(fn: Callable) -> Callable:
    """Decorator: seed before call, restore prior RNG state after."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        prior = _snapshot_state()
        try:
            set_global_seed(_CURRENT_SEED)
            return fn(*args, **kwargs)
        finally:
            _restore_state(prior)
    return wrapper


__all__ = [
    "set_global_seed",
    "get_current_seed",
    "hash_inputs",
    "deterministic",
]
