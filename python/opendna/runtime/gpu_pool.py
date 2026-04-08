"""GPU memory pool + model warm-up cache.

A lightweight semaphore-based allocator that tracks GPU memory reservations
per job so we don't OOM by running too many heavy models at once. Also keeps
a warm-cache of loaded models so re-running the same pipeline is instant.

Falls back gracefully when torch is not installed (CPU-only mode).
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional


class GpuPool:
    def __init__(self):
        self._lock = threading.Lock()
        self._warm: Dict[str, Any] = {}
        self._warm_at: Dict[str, float] = {}
        self._reservations: Dict[str, int] = {}  # job_id -> MB
        self._total_reserved_mb = 0

    # --- hardware introspection ---

    def info(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "total_mb": 0,
            "free_mb": 0,
            "device": "cpu",
            "backend": "cpu",
            "warm_models": list(self._warm.keys()),
            "reserved_mb": self._total_reserved_mb,
        }
        try:
            import torch  # type: ignore
            if torch.cuda.is_available():
                dev = torch.cuda.current_device()
                free, total = torch.cuda.mem_get_info(dev)
                out.update({
                    "total_mb": int(total / 1024 / 1024),
                    "free_mb": int(free / 1024 / 1024),
                    "device": torch.cuda.get_device_name(dev),
                    "backend": "cuda",
                })
            elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                out.update({"backend": "mps", "device": "apple-silicon"})
        except Exception:
            pass
        return out

    # --- reservations ---

    def reserve(self, job_id: str, mb: int, timeout_s: float = 60.0) -> bool:
        """Block until `mb` MB can be reserved. Returns True on success."""
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            with self._lock:
                info = self.info()
                free = info.get("free_mb", 0)
                if info["backend"] == "cpu" or free == 0 or free - self._total_reserved_mb >= mb:
                    self._reservations[job_id] = mb
                    self._total_reserved_mb += mb
                    return True
            time.sleep(0.25)
        return False

    def release(self, job_id: str) -> None:
        with self._lock:
            mb = self._reservations.pop(job_id, 0)
            self._total_reserved_mb = max(0, self._total_reserved_mb - mb)

    # --- warm model cache ---

    def get_warm(self, key: str) -> Optional[Any]:
        return self._warm.get(key)

    def put_warm(self, key: str, obj: Any) -> None:
        self._warm[key] = obj
        self._warm_at[key] = time.time()

    def evict_warm(self, key: str) -> None:
        self._warm.pop(key, None)
        self._warm_at.pop(key, None)

    def evict_older_than(self, seconds: float) -> int:
        cutoff = time.time() - seconds
        n = 0
        for k in list(self._warm_at):
            if self._warm_at[k] < cutoff:
                self.evict_warm(k)
                n += 1
        return n


_pool: Optional[GpuPool] = None


def get_gpu_pool() -> GpuPool:
    global _pool
    if _pool is None:
        _pool = GpuPool()
    return _pool
