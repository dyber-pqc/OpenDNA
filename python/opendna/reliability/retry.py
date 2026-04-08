"""Retry decorator with exponential backoff + jitter + classification."""
from __future__ import annotations

import asyncio
import functools
import logging
import random
import time
from dataclasses import dataclass
from typing import Callable, Tuple, Type, Optional


log = logging.getLogger("opendna.retry")


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    initial_delay: float = 0.5
    max_delay: float = 8.0
    backoff: float = 2.0
    jitter: float = 0.25
    retry_on: Tuple[Type[BaseException], ...] = (Exception,)
    give_up_on: Tuple[Type[BaseException], ...] = ()


def _is_transient(exc: BaseException, policy: RetryPolicy) -> bool:
    if isinstance(exc, policy.give_up_on):
        return False
    return isinstance(exc, policy.retry_on)


def retry(
    fn: Optional[Callable] = None,
    *,
    policy: Optional[RetryPolicy] = None,
    on_retry: Optional[Callable[[int, BaseException, float], None]] = None,
):
    """Decorator. Works with sync and async functions.

    Usage:
        @retry(policy=RetryPolicy(max_attempts=5))
        def fetch(...): ...
    """
    p = policy or RetryPolicy()

    def _wrap(f):
        if asyncio.iscoroutinefunction(f):
            @functools.wraps(f)
            async def _aw(*args, **kwargs):
                last: BaseException = RuntimeError("no attempts")
                delay = p.initial_delay
                for attempt in range(1, p.max_attempts + 1):
                    try:
                        return await f(*args, **kwargs)
                    except BaseException as e:  # noqa: BLE001
                        last = e
                        if attempt >= p.max_attempts or not _is_transient(e, p):
                            raise
                        sleep_for = min(p.max_delay, delay) + random.uniform(0, p.jitter)
                        log.warning("retry %d/%d after %.2fs: %s", attempt, p.max_attempts, sleep_for, e)
                        if on_retry:
                            on_retry(attempt, e, sleep_for)
                        await asyncio.sleep(sleep_for)
                        delay *= p.backoff
                raise last
            return _aw
        @functools.wraps(f)
        def _sw(*args, **kwargs):
            last: BaseException = RuntimeError("no attempts")
            delay = p.initial_delay
            for attempt in range(1, p.max_attempts + 1):
                try:
                    return f(*args, **kwargs)
                except BaseException as e:  # noqa: BLE001
                    last = e
                    if attempt >= p.max_attempts or not _is_transient(e, p):
                        raise
                    sleep_for = min(p.max_delay, delay) + random.uniform(0, p.jitter)
                    log.warning("retry %d/%d after %.2fs: %s", attempt, p.max_attempts, sleep_for, e)
                    if on_retry:
                        on_retry(attempt, e, sleep_for)
                    time.sleep(sleep_for)
                    delay *= p.backoff
            raise last
        return _sw

    return _wrap(fn) if fn else _wrap
