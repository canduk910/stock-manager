"""사용자 결정 2026-06-01: 현재가 캐시 금지 도메인 원칙 강화.

dashboard 응답은 현재가를 포함하므로 더 이상 캐시하지 않는다.
`services._dashboard_cache`는 항상 no-op이다 (get→None, set→무시).

라우터는 매 호출마다 service.get_dashboard_data를 호출해야 한다.
"""

from unittest.mock import patch

import pytest


@pytest.fixture
def cache():
    from services import _dashboard_cache as dc
    yield dc


class TestDashboardCacheDisabled:
    def test_get_always_none(self, cache):
        # set 후에도 get은 None — 캐시 비활성
        cache.set(user_id=1, items=[{"code": "005930", "market": "KR"}], data=[{"x": 1}])
        assert cache.get(user_id=1, items=[{"code": "005930", "market": "KR"}]) is None

    def test_set_is_noop(self, cache):
        # set 호출이 예외 없이 통과하고 아무 효과도 없어야 함
        cache.set(user_id=1, items=[], data=[{"y": 2}])
        assert cache.get(user_id=1, items=[]) is None

    def test_invalidate_does_not_raise(self, cache):
        cache.invalidate(1)
        cache.invalidate_all()


class TestRouterAlwaysHitsService:
    """현재가 캐시 금지 — 라우터는 매 호출 service.get_dashboard_data 호출."""

    def test_each_call_hits_service(self, monkeypatch):
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
            r.get_dashboard(user=user)
            r.get_dashboard(user=user)

        assert call_count["n"] == 2, "캐시 비활성 — 매 호출 service 호출되어야 함"
