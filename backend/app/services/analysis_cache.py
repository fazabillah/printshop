import time
import logging
from datetime import date
from typing import Optional, Any

logger = logging.getLogger(__name__)

TTL_SECONDS = 3600

_CACHE: dict[str, tuple[float, Any]] = {}
_DAILY_COUNTER: dict[str, int] = {}


def generate_analysis_id() -> str:
    today = date.today().strftime("%Y%m%d")
    _DAILY_COUNTER[today] = _DAILY_COUNTER.get(today, 0) + 1
    return f"anl_{today}_{_DAILY_COUNTER[today]:03d}"


def put(analysis_id: str, response: Any) -> None:
    _CACHE[analysis_id] = (time.monotonic(), response)


def get(analysis_id: str) -> Optional[Any]:
    _purge_expired()
    entry = _CACHE.get(analysis_id)
    if entry is None:
        return None
    stored_at, response = entry
    if time.monotonic() - stored_at > TTL_SECONDS:
        del _CACHE[analysis_id]
        return None
    return response


def _purge_expired() -> None:
    now = time.monotonic()
    expired = [k for k, (t, _) in _CACHE.items() if now - t > TTL_SECONDS]
    for k in expired:
        del _CACHE[k]
    if expired:
        logger.debug("Purged %d expired analysis entries", len(expired))
