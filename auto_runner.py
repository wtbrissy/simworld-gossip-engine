from __future__ import annotations

import threading
import time
from contextlib import suppress

from db import get_state, set_state
from sim_engine import simulate_day

_LOCK = threading.Lock()
_STARTED = False


def _safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: str, default: int = 1440) -> int:
    try:
        return int(value)
    except Exception:
        return default


def tick_once() -> bool:
    """Return True if one day was simulated by auto mode."""
    if get_state("auto_enabled", "0") != "1":
        return False
    interval = max(1, _safe_int(get_state("auto_interval_minutes", "1440"), 1440)) * 60
    now = time.time()
    last = _safe_float(get_state("last_auto_timestamp", "0"), 0)
    if now - last < interval:
        return False
    if not _LOCK.acquire(blocking=False):
        return False
    try:
        set_state("last_auto_timestamp", str(now))
        use_ai = get_state("auto_use_ai", "0") == "1"
        simulate_day(use_ai=use_ai)
        return True
    finally:
        _LOCK.release()


def _loop() -> None:
    while True:
        with suppress(Exception):
            tick_once()
        time.sleep(30)


def start_background_runner() -> None:
    global _STARTED
    if _STARTED:
        return
    _STARTED = True
    t = threading.Thread(target=_loop, name="simworld-auto-runner", daemon=True)
    t.start()
