"""Collector base — 5 수집기 공통 자료형 + sanity helpers.

기존 `stock/macro_fetcher.py` / `stock/dart_fin.py` 의 단순 함수 패턴 유지.
추상 클래스 도입 안 함.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CollectorResult:
    """수집기 단위 출력. service가 ORM upsert 시 사용."""

    indicator_name: str
    observed_at: str  # YYYY-MM-DD (분기는 분기 마지막일)
    value: Optional[float]
    value_meta: dict = field(default_factory=dict)  # 반드시 "unit" 키 포함
    source: str = ""
    raw_at: str = ""  # raw API 응답 ISO timestamp

    def __post_init__(self):
        # 단위 키 강제. value_meta가 비었더라도 unit이 있어야 한다.
        if "unit" not in (self.value_meta or {}):
            self.value_meta = {**(self.value_meta or {}), "unit": "unknown"}


def apply_outlier_guard(curr, prev, *, pct: float = 30.0) -> bool:
    """단일 데이터포인트 ±pct% 변동 격리.

    Returns:
        True  — 정상 (가드 통과)
        False — 격리 (서비스 측에서 폐기 + failures 기록)

    Rules:
        - prev이 None/0 이면 True (비교 불가, 가드 통과)
        - curr이 None 이면 False (불완전 데이터)
        - abs(curr - prev) / abs(prev) > pct/100 → False
    """
    if curr is None:
        return False
    if prev is None or prev == 0:
        return True
    try:
        delta_ratio = abs(float(curr) - float(prev)) / abs(float(prev))
    except (TypeError, ValueError):
        return False
    return delta_ratio <= (pct / 100.0)


def pct_change_or_none(curr, prev) -> Optional[float]:
    """`(curr - prev) / prev * 100`. 계산 불가 시 None.

    - prev이 None/0 이면 None
    - curr이 None 이면 None
    """
    if curr is None or prev is None or prev == 0:
        return None
    try:
        return (float(curr) - float(prev)) / abs(float(prev)) * 100.0
    except (TypeError, ValueError):
        return None
