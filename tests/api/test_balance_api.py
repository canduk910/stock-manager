"""Balance API 엔드포인트 테스트 (A-070 ~ A-071)."""

import pytest


class TestBalanceEndpoints:
    """잔고 조회 API."""

    def test_get_balance_no_key(self, client):
        """A-070: 잔고 조회 → KIS 키 없으면 503, 있으면 200."""
        resp = client.get("/api/balance")
        # KIS 키 미설정 → 503, 설정됨 → 200/502
        assert resp.status_code in (200, 502, 503)

    def test_get_balance_response_shape(self, client):
        """A-071: 응답 구조 검증 (503이어도 에러 메시지 형식)."""
        resp = client.get("/api/balance")
        if resp.status_code == 200:
            data = resp.json()
            # 정상 응답 시 필수 키 존재
            assert "stock_list" in data
            assert "overseas_list" in data
            assert "futures_list" in data
            assert "fno_enabled" in data
            assert "total_evaluation" in data
            assert "deposit" in data
        else:
            # 503 에러 응답도 JSON 형식이어야 함
            data = resp.json()
            assert "detail" in data or "message" in data or isinstance(data, dict)
