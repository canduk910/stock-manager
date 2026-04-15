"""db 패키지 공용 유틸리티 — KST 타임존 헬퍼.

stock/db_base.py에서 re-export하여 기존 caller 호환 유지.
"""

from datetime import datetime, timedelta, timezone

# ── KST 타임존 (한국 표준시 UTC+9) ──────────────────────────────────────────
KST = timezone(timedelta(hours=9))


def now_kst() -> datetime:
    """현재 KST 시각 (timezone-aware datetime)."""
    return datetime.now(KST)


def now_kst_iso(timespec: str = "seconds") -> str:
    """현재 KST 시각 ISO 문자열."""
    return datetime.now(KST).isoformat(timespec=timespec)
