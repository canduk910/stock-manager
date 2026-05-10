"""FRED OAS 시계열 FIFO 영구 누적 store.

배경(2026-05-10):
- ICE BofA 라이센스 정책 변경: 2026년 4월부터 BAMLH0A0HYM2 등 OAS 시리즈가
  FRED API에서 **최근 3년치만** 공개됨.
- 사용자 결정: 자체 DB FIFO 누적으로 10년치 시계열 직접 구축.

흐름:
1. 매일 자정(KST 00:05) cron에서 FRED API 호출 → 최근 3년치 다운로드
2. cache.db에 누적된 기존 데이터와 머지 (date 키 unique)
3. 10년(365×10일) 초과한 가장 오래된 항목 제거 (FIFO rolling)
4. fetch_credit_spread는 누적 store 우선 사용 (FRED 직접 호출 안 함)

영속 캐시 키: `macro:oas_history_persist:{series_id}` (TTL = 365일 × 50, 사실상 무한)
저장 형식: list[dict] = [{"date": "YYYY-MM-DD", "value": float}, ...] (date 오름차순)

초기 적재(첫 출시): 3년치 (FRED 가용분).
이후 매일 +1일 → 7년 후 자연스럽게 10년 시계열 도달.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

from stock.cache import get_cached, set_cached

logger = logging.getLogger(__name__)


# 무한에 가까운 TTL (50년) — cache.db 자연 만료 회피
_PERSIST_TTL_HOURS = 24 * 365 * 50

# 10년 보존 (영업일 기준 약 2,610일, 달력 기준 3,650일 — 안전하게 달력 기준)
_RETENTION_DAYS = 365 * 10


def _key(series_id: str) -> str:
    return f"macro:oas_history_persist:{series_id}"


def get_history(series_id: str) -> list[dict]:
    """누적된 전체 시계열 반환 (date 오름차순)."""
    cached = get_cached(_key(series_id))
    if not isinstance(cached, list):
        return []
    return cached


def merge_and_persist(series_id: str, new_rows: list[dict]) -> dict:
    """신규 데이터를 기존 누적과 머지 + 10년 초과 제거 (FIFO).

    Args:
        series_id: FRED 시리즈 ID (예: "BAMLH0A0HYM2")
        new_rows: [{date, value}, ...] (date YYYY-MM-DD, value float)

    Returns:
        {
            "added": int,        # 신규 추가된 row 수
            "removed": int,      # FIFO로 제거된 row 수
            "total": int,        # 누적 후 총 row 수
            "first_date": str,   # 가장 오래된 날짜
            "last_date": str,    # 가장 최근 날짜
        }
    """
    existing = get_history(series_id)
    existing_map = {r["date"]: r for r in existing if r.get("date")}

    added = 0
    for r in new_rows or []:
        if not isinstance(r, dict):
            continue
        d = r.get("date")
        v = r.get("value")
        if not d or v is None:
            continue
        # 신규 날짜만 추가 (기존 값 보존 — vintage 우선)
        if d not in existing_map:
            existing_map[d] = {"date": d, "value": float(v)}
            added += 1

    # date 오름차순 정렬
    merged = sorted(existing_map.values(), key=lambda x: x["date"])

    # FIFO: 10년 초과 가장 오래된 항목 제거
    cutoff = (date.today() - timedelta(days=_RETENTION_DAYS)).strftime("%Y-%m-%d")
    before_count = len(merged)
    merged = [r for r in merged if r["date"] >= cutoff]
    removed = before_count - len(merged)

    # 영속 저장
    set_cached(_key(series_id), merged, ttl_hours=_PERSIST_TTL_HOURS)

    return {
        "added": added,
        "removed": removed,
        "total": len(merged),
        "first_date": merged[0]["date"] if merged else None,
        "last_date": merged[-1]["date"] if merged else None,
    }


def slice_history(series_id: str, years: int) -> list[dict]:
    """누적된 시계열에서 최근 N년 슬라이스 반환."""
    history = get_history(series_id)
    if not history:
        return []
    cutoff = (date.today() - timedelta(days=365 * years)).strftime("%Y-%m-%d")
    return [r for r in history if r["date"] >= cutoff]


def cleanup(series_id: str) -> int:
    """10년 초과 가장 오래된 항목 제거 (cron 전용 — append 없이 retention만)."""
    history = get_history(series_id)
    if not history:
        return 0
    cutoff = (date.today() - timedelta(days=_RETENTION_DAYS)).strftime("%Y-%m-%d")
    before = len(history)
    after = [r for r in history if r["date"] >= cutoff]
    removed = before - len(after)
    if removed > 0:
        set_cached(_key(series_id), after, ttl_hours=_PERSIST_TTL_HOURS)
    return removed
