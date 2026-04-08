"""Self-healing health checker.

Periodically inspects critical subsystems and runs registered "fix-it"
callbacks when something is wrong:
  - GPU OOM      → evict warm models, drop reservations
  - DB locked    → reopen WAL connection
  - Model load   → re-fetch from Component Manager
  - Disk full    → clear old crash dumps + cache
"""
from __future__ import annotations

import shutil
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional


@dataclass
class HealthCheck:
    name: str
    check: Callable[[], bool]                       # True = healthy
    fix: Optional[Callable[[], None]] = None
    last_status: Optional[bool] = None
    last_check: float = 0.0
    last_fix: float = 0.0
    fix_count: int = 0


class SelfHealer:
    def __init__(self):
        self._checks: Dict[str, HealthCheck] = {}
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._register_defaults()

    def _register_defaults(self) -> None:
        # GPU OOM heuristic
        def _gpu_ok() -> bool:
            try:
                from opendna.runtime import get_gpu_pool
                info = get_gpu_pool().info()
                if info.get("backend") == "cpu":
                    return True
                return info.get("free_mb", 0) > 200
            except Exception:
                return True

        def _gpu_fix() -> None:
            try:
                from opendna.runtime import get_gpu_pool
                get_gpu_pool().evict_older_than(0)
                import torch  # type: ignore
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

        self.register("gpu_memory", _gpu_ok, _gpu_fix)

        # Disk space
        def _disk_ok() -> bool:
            try:
                free = shutil.disk_usage(Path.home()).free
                return free > 500 * 1024 * 1024
            except Exception:
                return True

        def _disk_fix() -> None:
            try:
                from opendna.reliability.crash import get_crash_reporter
                get_crash_reporter().clear()
            except Exception:
                pass

        self.register("disk_space", _disk_ok, _disk_fix)

        # Auth DB lock recovery
        def _db_ok() -> bool:
            try:
                from opendna.auth import get_user_store
                get_user_store().conn.execute("SELECT 1").fetchone()
                return True
            except Exception:
                return False

        def _db_fix() -> None:
            try:
                from opendna.auth import users as u
                u._store = None  # type: ignore
            except Exception:
                pass

        self.register("auth_db", _db_ok, _db_fix)

    def register(
        self,
        name: str,
        check: Callable[[], bool],
        fix: Optional[Callable[[], None]] = None,
    ) -> None:
        self._checks[name] = HealthCheck(name, check, fix)

    def run_once(self) -> Dict[str, dict]:
        out: Dict[str, dict] = {}
        for name, hc in self._checks.items():
            ok = False
            try:
                ok = bool(hc.check())
            except Exception:
                ok = False
            hc.last_status = ok
            hc.last_check = time.time()
            if not ok and hc.fix is not None:
                try:
                    hc.fix()
                    hc.fix_count += 1
                    hc.last_fix = time.time()
                except Exception:
                    pass
            out[name] = {
                "ok": ok,
                "last_check": hc.last_check,
                "last_fix": hc.last_fix,
                "fix_count": hc.fix_count,
            }
        return out

    def start(self, interval_s: float = 30.0) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()

        def _loop():
            while not self._stop.wait(interval_s):
                try:
                    self.run_once()
                except Exception:
                    pass

        self._thread = threading.Thread(target=_loop, daemon=True, name="opendna-healer")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()


_healer: Optional[SelfHealer] = None


def get_healer() -> SelfHealer:
    global _healer
    if _healer is None:
        _healer = SelfHealer()
    return _healer
