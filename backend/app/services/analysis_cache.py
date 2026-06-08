import time
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)

TTL_SECONDS = 3600


@dataclass
class AnalysisRecord:
    response: Any                        # AnalyzeResponse (avoid circular import)
    cover_pdf_path: Optional[Path] = None
    cd_pdf_path: Optional[Path] = None
    cover_docx_path: Optional[Path] = None
    cd_docx_path: Optional[Path] = None
    render_version: int = 0
    locked: bool = False
    status: str = "ANALYZED"            # ANALYZED | AWAITING_PAYMENT
    preview_failed: bool = False
    verification_slip_path: Optional[Path] = None
    confirmed_at: Optional[datetime] = None
    shipping_address: Optional[str] = None


_CACHE: dict[str, tuple[float, AnalysisRecord]] = {}
_DAILY_COUNTER: dict[str, int] = {}


def generate_analysis_id() -> str:
    today = date.today().strftime("%Y%m%d")
    _DAILY_COUNTER[today] = _DAILY_COUNTER.get(today, 0) + 1
    return f"anl_{today}_{_DAILY_COUNTER[today]:03d}"


def put(analysis_id: str, record: AnalysisRecord) -> None:
    _CACHE[analysis_id] = (time.monotonic(), record)


def get_record(analysis_id: str) -> Optional[AnalysisRecord]:
    _purge_expired()
    entry = _CACHE.get(analysis_id)
    if entry is None:
        return None
    stored_at, record = entry
    if time.monotonic() - stored_at > TTL_SECONDS:
        del _CACHE[analysis_id]
        return None
    return record


def get(analysis_id: str) -> Optional[Any]:
    """Backward-compatible helper; returns AnalyzeResponse or None."""
    record = get_record(analysis_id)
    return record.response if record is not None else None


def update_extracted(analysis_id: str, edits: dict) -> Optional[AnalysisRecord]:
    """Apply field edits to the cached extracted data and bump render_version."""
    record = get_record(analysis_id)
    if record is None:
        return None
    record.response = record.response.model_copy(
        update={"extracted": record.response.extracted.model_copy(update=edits)}
    )
    record.render_version += 1
    return record


def lock(analysis_id: str) -> Optional[AnalysisRecord]:
    record = get_record(analysis_id)
    if record is None:
        return None
    record.locked = True
    record.status = "AWAITING_PAYMENT"
    record.confirmed_at = datetime.now(timezone.utc)
    return record


def _purge_expired() -> None:
    now = time.monotonic()
    expired = [k for k, (t, _) in _CACHE.items() if now - t > TTL_SECONDS]
    for k in expired:
        del _CACHE[k]
    if expired:
        logger.debug("Purged %d expired analysis entries", len(expired))
