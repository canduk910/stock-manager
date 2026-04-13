"""Report API 엔드포인트 테스트."""


class TestReportEndpoints:
    def test_list_reports(self, client):
        resp = client.get("/api/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_list_reports_with_market_filter(self, client):
        resp = client.get("/api/reports?market=KR")
        assert resp.status_code == 200

    def test_get_report_not_found(self, client):
        resp = client.get("/api/reports/99999")
        assert resp.status_code == 404

    def test_list_recommendations(self, client):
        resp = client.get("/api/reports/recommendations")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_list_recommendations_with_filters(self, client):
        resp = client.get("/api/reports/recommendations?market=KR&status=recommended")
        assert resp.status_code == 200

    def test_get_recommendation_not_found(self, client):
        resp = client.get("/api/reports/recommendations/99999")
        assert resp.status_code == 404

    def test_performance_stats(self, client):
        resp = client.get("/api/reports/performance")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "wins" in data
        assert "win_rate" in data

    def test_list_regimes(self, client):
        resp = client.get("/api/reports/regimes")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_latest_regime(self, client):
        resp = client.get("/api/reports/regimes/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert "regime" in data
