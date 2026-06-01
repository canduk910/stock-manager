"""QW-1: dict 기반 stale 판정 단위 테스트.

`is_stale_from_dict(info, field, *, now=None)` 신규 순수 함수의 동작을
DB 기반 `is_stale(code, market, field)` 결과와 동일하게 검증한다.

목적: 26종목 × 4 SELECT(get_stock_info × 1 + is_stale × 3) → 26 SELECT
     (fetch 1회 + dict 판정 3회)로 N+1 제거.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from db.utils import KST


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


# ── is_stale_from_dict 신규 함수 ────────────────────────────────────────────

class TestIsStaleFromDict:
    """is_stale_from_dict — dict + field만으로 stale 여부 판정."""

    def test_none_info_is_stale(self):
        from db.repositories.stock_info_repo import is_stale_from_dict
        assert is_stale_from_dict(None, "price") is True

    def test_empty_dict_is_stale(self):
        from db.repositories.stock_info_repo import is_stale_from_dict
        assert is_stale_from_dict({}, "price") is True

    def test_missing_field_updated_at_is_stale(self):
        from db.repositories.stock_info_repo import is_stale_from_dict
        info = {"code": "005930", "market": "KR", "price": 70000}
        # price_updated_at 없음 → stale
        assert is_stale_from_dict(info, "price") is True

    def test_price_always_stale_regardless_of_timestamp(self):
        """현재가 캐시 금지 강화(2026-06-01) — price는 timestamp 무관 항상 stale."""
        from db.repositories.stock_info_repo import is_stale_from_dict
        now = datetime(2026, 5, 4, 14, 0, 0)
        # 1초 전 갱신이어도 stale (영속 캐시 우회 강제)
        info = {"price_updated_at": _iso(now - timedelta(seconds=1))}
        assert is_stale_from_dict(info, "price", now=now) is True

    def test_old_price_is_stale(self):
        from db.repositories.stock_info_repo import is_stale_from_dict
        old = datetime.now(KST).replace(tzinfo=None) - timedelta(hours=24)
        info = {"price_updated_at": _iso(old)}
        # price TTL 최대 12시간 → 24시간이면 무조건 stale
        assert is_stale_from_dict(info, "price") is True

    def test_metrics_field_uses_metrics_updated_at(self):
        from db.repositories.stock_info_repo import is_stale_from_dict
        now = datetime.now(KST).replace(tzinfo=None)
        info = {"metrics_updated_at": _iso(now - timedelta(minutes=10))}
        # metrics TTL: 6h trading / 24h off → 10분이면 fresh
        assert is_stale_from_dict(info, "metrics") is False

    def test_financials_field_uses_fin_updated_at(self):
        """financials 영역은 컬럼명이 fin_updated_at — 변환 매핑 검증."""
        from db.repositories.stock_info_repo import is_stale_from_dict
        now = datetime.now(KST).replace(tzinfo=None)
        info = {"fin_updated_at": _iso(now - timedelta(hours=1))}
        # financials TTL: 168h → 1시간이면 fresh
        assert is_stale_from_dict(info, "financials") is False

    def test_returns_field(self):
        from db.repositories.stock_info_repo import is_stale_from_dict
        now = datetime.now(KST).replace(tzinfo=None)
        info = {"returns_updated_at": _iso(now - timedelta(minutes=10))}
        assert is_stale_from_dict(info, "returns") is False

    def test_invalid_iso_string_is_stale(self):
        from db.repositories.stock_info_repo import is_stale_from_dict
        info = {"price_updated_at": "not-a-date"}
        assert is_stale_from_dict(info, "price") is True

    def test_explicit_now_parameter_metrics(self):
        """주입된 now로 metrics 트레이딩 윈도우 검증 (price는 항상 stale 별도 검증)."""
        from db.repositories.stock_info_repo import is_stale_from_dict
        now = datetime(2026, 5, 4, 14, 0, 0)  # 평일 KST 14:00 trading
        # metrics TTL: 6h trading → 30분 전이면 fresh
        info = {"metrics_updated_at": _iso(now - timedelta(minutes=30))}
        assert is_stale_from_dict(info, "metrics", now=now) is False
        # 8시간 전 → trading TTL 6h 초과 → stale
        info2 = {"metrics_updated_at": _iso(now - timedelta(hours=8))}
        assert is_stale_from_dict(info2, "metrics", now=now) is True

    def test_off_hours_uses_off_ttl_for_metrics(self):
        """장외 metrics TTL 검증 (price 영역은 timestamp 무관 stale이므로 metrics로 확인)."""
        from db.repositories.stock_info_repo import is_stale_from_dict
        # 토요일 자정 = 비거래
        now = datetime(2026, 5, 2, 0, 0, 0)
        # metrics off TTL=24h, 3h 전 → fresh
        info = {"metrics_updated_at": _iso(now - timedelta(hours=3))}
        assert is_stale_from_dict(info, "metrics", now=now) is False
        # 25h 전 → off TTL 24h 초과 → stale
        info2 = {"metrics_updated_at": _iso(now - timedelta(hours=25))}
        assert is_stale_from_dict(info2, "metrics", now=now) is True


# ── is_stale 후방 호환 회귀 ──────────────────────────────────────────────────

class TestIsStaleBackwardCompat:
    """기존 is_stale(code, market, field) 시그니처가 동일한 결과 반환하는지 회귀."""

    def test_signature_preserved(self):
        """`is_stale(code, market, field)` 함수가 여전히 호출 가능하다 — DB 모킹."""
        from unittest.mock import patch
        from stock import stock_info_store

        # get_session 모킹: get_stock_info → None 반환 → is_stale_from_dict(None) → True
        class _FakeRepo:
            def get_stock_info(self, code, market):
                return None
            def is_stale(self, code, market, field):
                # 실제 구현은 get_stock_info 위임, 여기선 직접 위임 결과 흉내
                from db.repositories.stock_info_repo import is_stale_from_dict
                return is_stale_from_dict(self.get_stock_info(code, market), field)

        class _FakeCtx:
            def __enter__(self): return None
            def __exit__(self, *a): return False

        with patch.object(stock_info_store, "get_session", return_value=_FakeCtx()), \
             patch.object(stock_info_store, "StockInfoRepository", return_value=_FakeRepo()):
            assert stock_info_store.is_stale("999999", "KR", "price") is True
