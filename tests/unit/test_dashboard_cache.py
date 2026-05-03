"""QW-4: 사용자별 dashboard 응답 in-memory 캐시.

키: (user_id, hash(sorted(item_codes)))
TTL: 60s
invalidation: add/remove/update_memo 시 user_id 캐시 삭제
멀티 인스턴스 전환 시 재설계 필요(F-4-A) — 코드 주석 명시.
"""

import time
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def cache():
    """clean cache for each test."""
    from services import _dashboard_cache as dc
    dc.invalidate_all()
    yield dc
    dc.invalidate_all()


class TestDashboardCache:
    def test_set_get_basic(self, cache):
        cache.set(user_id=1, items=[{"code": "005930", "market": "KR"}], data=[{"x": 1}])
        hit = cache.get(user_id=1, items=[{"code": "005930", "market": "KR"}])
        assert hit == [{"x": 1}]

    def test_miss_for_different_user(self, cache):
        cache.set(user_id=1, items=[{"code": "005930", "market": "KR"}], data=[{"x": 1}])
        # 다른 user → miss
        assert cache.get(user_id=2, items=[{"code": "005930", "market": "KR"}]) is None

    def test_miss_after_items_change(self, cache):
        cache.set(user_id=1, items=[{"code": "005930", "market": "KR"}], data=[{"x": 1}])
        # 종목 추가 → miss
        assert cache.get(user_id=1, items=[
            {"code": "005930", "market": "KR"},
            {"code": "000660", "market": "KR"},
        ]) is None

    def test_invalidate_user(self, cache):
        cache.set(user_id=1, items=[{"code": "005930", "market": "KR"}], data=[{"x": 1}])
        cache.invalidate(1)
        assert cache.get(user_id=1, items=[{"code": "005930", "market": "KR"}]) is None

    def test_other_user_not_invalidated(self, cache):
        cache.set(user_id=1, items=[{"code": "005930", "market": "KR"}], data=[{"x": 1}])
        cache.set(user_id=2, items=[{"code": "AAPL", "market": "US"}], data=[{"y": 2}])
        cache.invalidate(1)
        assert cache.get(user_id=2, items=[{"code": "AAPL", "market": "US"}]) == [{"y": 2}]

    def test_ttl_expiry(self, cache, monkeypatch):
        """TTL 60s 경과 후 miss."""
        cache.set(user_id=1, items=[{"code": "005930", "market": "KR"}], data=[{"x": 1}])
        # _now()를 미래로 점프
        future = time.time() + 120
        monkeypatch.setattr(cache, "_now", lambda: future)
        assert cache.get(user_id=1, items=[{"code": "005930", "market": "KR"}]) is None

    def test_item_order_irrelevant(self, cache):
        """items 순서가 달라도 동일 키 (sorted hash)."""
        cache.set(user_id=1, items=[
            {"code": "005930", "market": "KR"},
            {"code": "000660", "market": "KR"},
        ], data=[{"x": 1}])
        # 역순으로 조회
        hit = cache.get(user_id=1, items=[
            {"code": "000660", "market": "KR"},
            {"code": "005930", "market": "KR"},
        ])
        assert hit == [{"x": 1}]


class TestDashboardCacheInRouter:
    """router 통합: dashboard 호출 → 1차 fetch + 2차 cache hit."""

    def test_router_uses_cache(self, monkeypatch):
        """get_dashboard 라우터는 캐시 hit 시 service.get_dashboard_data 미호출."""
        from services import _dashboard_cache as dc
        dc.invalidate_all()

        from routers import watchlist as r
        items = [{"code": "005930", "name": "삼성전자", "memo": "", "market": "KR"}]
        fetched = [{"code": "005930", "price": 70000, "partial_failure": []}]

        call_count = {"n": 0}

        def fake_get_dashboard_data(its):
            call_count["n"] += 1
            return fetched

        with patch("stock.store.all_items", return_value=items), \
             patch.object(r._svc, "get_dashboard_data", side_effect=fake_get_dashboard_data):
            user = {"id": 1, "username": "u"}
            # 1차
            res1 = r.get_dashboard(user=user)
            # 2차 (즉시 재호출 → cache hit)
            res2 = r.get_dashboard(user=user)

        assert res1 == res2
        assert call_count["n"] == 1, "두 번째 호출은 캐시 hit이라 service 미호출"
        dc.invalidate_all()

    def test_add_item_invalidates_cache(self, monkeypatch):
        from services import _dashboard_cache as dc
        dc.invalidate_all()

        from routers import watchlist as r
        items = [{"code": "005930", "name": "삼성전자", "memo": "", "market": "KR"}]

        with patch("stock.store.all_items", return_value=items), \
             patch.object(r._svc, "get_dashboard_data", return_value=[{"x": 1}]):
            user = {"id": 1, "username": "u"}
            r.get_dashboard(user=user)

        # 캐시에 들어있다는 것을 확인
        assert dc.get(user_id=1, items=items) is not None

        # add_item 시뮬레이션 → invalidate(1)
        dc.invalidate(1)
        assert dc.get(user_id=1, items=items) is None
