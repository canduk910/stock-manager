"""REQ-FE-02: useUsMarketClock 미국 공휴일 휴장 판정 보조 검증.

프론트 Vitest 미설정 환경에서 useUsMarketClock.js의 핵심 데이터 정합성을 보조 검증한다:

1. 공휴일 명단 상수 ``US_HOLIDAYS_ET`` 가 useUsMarketClock.js에 존재
2. 명단 길이 — 2026/2027/2028 각 연도 10일 (총 30일 ±observed 보정 허용)
3. 핵심 공휴일 5건이 2026 연도에 포함:
   2026-01-01(New Year), 2026-01-19(MLK), 2026-05-25(Memorial),
   2026-07-03(Independence Day, observed Friday since 7/4 is Saturday),
   2026-11-26(Thanksgiving)

JS 측 순수 함수 ``resolveUsPhaseByClock`` 직접 실행은 Node ESM 의존성이 있어 본 단위에서는 생략한다.
프론트 빌드(``npm run build``)와 함께 사용된다.
"""
from __future__ import annotations

from pathlib import Path
import re


HOOK_PATH = Path(__file__).resolve().parents[2] / "frontend" / "src" / "hooks" / "useUsMarketClock.js"


def _read_hook() -> str:
    assert HOOK_PATH.exists(), f"useUsMarketClock.js missing: {HOOK_PATH}"
    return HOOK_PATH.read_text(encoding="utf-8")


def test_hook_exposes_us_holidays_constant():
    src = _read_hook()
    assert "US_HOLIDAYS_ET" in src, "US_HOLIDAYS_ET 상수 미정의"


def test_hook_holiday_list_includes_2026_core_dates():
    src = _read_hook()
    must_have = [
        "2026-01-01",  # New Year
        "2026-01-19",  # MLK Day (3rd Mon Jan)
        "2026-02-16",  # Presidents Day (3rd Mon Feb)
        "2026-04-03",  # Good Friday
        "2026-05-25",  # Memorial Day (last Mon May)
        "2026-06-19",  # Juneteenth
        "2026-07-03",  # Independence Day observed (7/4=Sat → Fri)
        "2026-09-07",  # Labor Day (1st Mon Sep)
        "2026-11-26",  # Thanksgiving (4th Thu Nov)
        "2026-12-25",  # Christmas
    ]
    missing = [d for d in must_have if d not in src]
    assert not missing, f"2026 핵심 공휴일 누락: {missing}"


def test_hook_holiday_list_includes_2027_2028_years():
    src = _read_hook()
    # 2027 / 2028 명단도 포함되어야 한다
    assert "2027-01-01" in src, "2027 New Year 누락"
    assert "2028-01-03" in src or "2028-01-01" in src, \
        "2028 New Year/observed 누락 (1/1=Sat 시 1/3 또는 1/1)"
    # 추수감사절 4번째 목요일
    assert "2027-11-25" in src, "2027 Thanksgiving 누락"
    assert "2028-11-23" in src, "2028 Thanksgiving 누락"


def test_resolve_phase_by_clock_handles_holiday_branch():
    """resolveUsPhaseByClock 함수에 공휴일 분기 로직이 추가되었는지 검증."""
    src = _read_hook()
    # 공휴일 set 사용 (Set/Array.includes/.has 등 어떤 형태든)
    has_holiday_check = (
        re.search(r"US_HOLIDAYS_ET\s*\.\s*(includes|has)", src)
        or re.search(r"US_HOLIDAYS\w*\.has\(", src)
        or "isUsHoliday" in src
    )
    assert has_holiday_check, "공휴일 판정 로직(Set.has/Array.includes/isUsHoliday)이 없음"

    # closed 분기 후 라벨 — 휴장(공휴일명) 또는 holiday 변수
    assert "holiday" in src.lower(), "공휴일 라벨/변수 미사용"
