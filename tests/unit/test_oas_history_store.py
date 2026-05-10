"""stock.oas_history_store FIFO 누적 회귀 테스트.

2026-05-10 ICE BofA 라이센스 정책 변경(FRED 3년 제한) 대응.
사용자 결정: 자체 DB FIFO 누적으로 10년 시계열 직접 구축.
"""

from datetime import date, timedelta
from unittest.mock import patch

import pytest

from stock import oas_history_store


@pytest.fixture(autouse=True)
def _clear_store():
    """각 테스트 후 누적 store 정리."""
    yield
    try:
        from stock.cache import delete_prefix
        delete_prefix("macro:oas_history_persist:")
    except Exception:
        pass


def test_merge_appends_new_dates_only():
    """기존 누적 + 신규 머지 — 같은 날짜는 기존 값 보존."""
    # 1차 머지
    s1 = oas_history_store.merge_and_persist("TEST", [
        {"date": "2025-01-01", "value": 4.0},
        {"date": "2025-01-02", "value": 4.1},
    ])
    assert s1["added"] == 2
    assert s1["total"] == 2

    # 2차 머지 (1건 중복 + 1건 신규)
    s2 = oas_history_store.merge_and_persist("TEST", [
        {"date": "2025-01-02", "value": 99.9},  # 중복 — 기존 4.1 보존
        {"date": "2025-01-03", "value": 4.2},
    ])
    assert s2["added"] == 1  # 신규만
    assert s2["total"] == 3

    history = oas_history_store.get_history("TEST")
    assert history[1]["value"] == 4.1  # 기존 값 보존 (vintage 우선)


def test_fifo_removes_old_entries_beyond_10_years():
    """10년(3650일) 초과 가장 오래된 항목 자동 제거."""
    today = date.today()
    old_date = (today - timedelta(days=365 * 11)).strftime("%Y-%m-%d")
    new_date = today.strftime("%Y-%m-%d")

    oas_history_store.merge_and_persist("TEST", [
        {"date": old_date, "value": 5.0},
        {"date": new_date, "value": 4.0},
    ])
    history = oas_history_store.get_history("TEST")
    # 11년 전 데이터는 FIFO로 제거
    assert all(r["date"] >= (today - timedelta(days=365 * 10)).strftime("%Y-%m-%d") for r in history)
    assert any(r["date"] == new_date for r in history)
    assert not any(r["date"] == old_date for r in history)


def test_slice_history_returns_recent_n_years():
    """slice_history(years=5)는 최근 5년만 반환."""
    today = date.today()
    rows = [
        {"date": (today - timedelta(days=365 * 7)).strftime("%Y-%m-%d"), "value": 5.0},
        {"date": (today - timedelta(days=365 * 3)).strftime("%Y-%m-%d"), "value": 4.0},
        {"date": today.strftime("%Y-%m-%d"), "value": 3.0},
    ]
    oas_history_store.merge_and_persist("TEST", rows)

    sliced_5y = oas_history_store.slice_history("TEST", 5)
    # 7년 전은 5년 슬라이스에서 제외
    assert all(r["date"] >= (today - timedelta(days=365 * 5)).strftime("%Y-%m-%d") for r in sliced_5y)
    assert len(sliced_5y) == 2  # 3년 전 + 오늘

    sliced_10y = oas_history_store.slice_history("TEST", 10)
    # 7년 전 포함
    assert len(sliced_10y) == 3


def test_get_history_empty_when_no_data():
    """저장 전 빈 리스트 반환."""
    assert oas_history_store.get_history("TEST_NEW") == []


def test_merge_invalid_rows_skipped():
    """date/value 누락 row는 silent skip."""
    s = oas_history_store.merge_and_persist("TEST", [
        {"date": "2025-01-01", "value": 4.0},
        {"date": None, "value": 5.0},      # 무효
        {"value": 6.0},                     # date 없음
        {"date": "2025-01-02"},             # value 없음
        {"date": "2025-01-03", "value": 4.2},
    ])
    assert s["added"] == 2  # 유효 2건만
    assert s["total"] == 2


def test_cleanup_only_retention():
    """cleanup은 신규 추가 없이 retention만 적용."""
    today = date.today()
    old = (today - timedelta(days=365 * 11)).strftime("%Y-%m-%d")
    recent = today.strftime("%Y-%m-%d")
    oas_history_store.merge_and_persist("TEST", [
        {"date": old, "value": 5.0},
        {"date": recent, "value": 4.0},
    ])
    # 머지 시점에 이미 FIFO 적용됐으니 추가 cleanup은 0
    removed = oas_history_store.cleanup("TEST")
    assert removed == 0


def test_isolation_per_series_id():
    """series_id별 독립 저장."""
    oas_history_store.merge_and_persist("HY", [{"date": "2025-01-01", "value": 4.0}])
    oas_history_store.merge_and_persist("IG", [{"date": "2025-01-01", "value": 1.5}])

    hy = oas_history_store.get_history("HY")
    ig = oas_history_store.get_history("IG")
    assert len(hy) == 1 and hy[0]["value"] == 4.0
    assert len(ig) == 1 and ig[0]["value"] == 1.5
