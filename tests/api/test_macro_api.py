"""Macro API 엔드포인트 테스트 (A-080 ~ A-084)."""

import pytest

# 이 모듈의 테스트는 mock 없이 외부 API(yfinance/Google News RSS/FRED 등)를
# 실제로 호출하는 스모크 테스트다. 검증은 "200 또는 502"뿐이라 CI 커버리지 가치가
# 낮은 반면, 외부 서비스 미응답 시 무한 대기 위험이 있다. (2026-06-20: /summary의
# FRED 신용스프레드 호출이 CI에서 hang → job 15분 wall 발동) 따라서 slow로 표시해
# CI(`-m "not slow"`)에서 제외한다. 로컬에서는 그대로 실행된다.
pytestmark = pytest.mark.slow


class TestMacroEndpoints:
    """매크로 분석 API — 섹션별 독립 실패 허용."""

    def test_get_indices(self, client):
        """A-080: GET /api/macro/indices → 200."""
        resp = client.get("/api/macro/indices")
        # yfinance 기반 → 외부 API 실패 가능
        assert resp.status_code in (200, 502)

    def test_get_news(self, client):
        """A-081: GET /api/macro/news → 200."""
        resp = client.get("/api/macro/news")
        assert resp.status_code in (200, 502)

    def test_get_sentiment(self, client):
        """A-082: GET /api/macro/sentiment → 200."""
        resp = client.get("/api/macro/sentiment")
        assert resp.status_code in (200, 502)

    def test_get_investor_quotes(self, client):
        """A-083: GET /api/macro/investor-quotes → 200."""
        resp = client.get("/api/macro/investor-quotes")
        assert resp.status_code in (200, 502)

    def test_get_summary(self, client):
        """A-084: GET /api/macro/summary → 200 (부분 실패 허용)."""
        resp = client.get("/api/macro/summary")
        assert resp.status_code in (200, 502)
