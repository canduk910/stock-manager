"""REQ-ANALYST-04, 05, 07, 11: research_collector 6번째 카테고리 통합 테스트."""

from datetime import date, timedelta
from unittest.mock import patch

import pytest


# ────────────────────────────────────────────────────────────────────────────
# REQ-ANALYST-04: 컨센서스 통계 (중앙값 우선)
# ────────────────────────────────────────────────────────────────────────────


class TestComputeConsensus:
    def test_median_dispersion_opinion_dist(self):
        from stock.research_collector import _compute_consensus

        reports = [
            {"broker": "A", "target_price": 80000, "opinion": "Buy"},
            {"broker": "B", "target_price": 85000, "opinion": "Buy"},
            {"broker": "C", "target_price": 90000, "opinion": "Hold"},
            {"broker": "D", "target_price": 95000, "opinion": "Buy"},
            {"broker": "E", "target_price": 100000, "opinion": "Strong Buy"},
        ]
        c = _compute_consensus(reports, current_price=80000)
        assert c["target_median"] == 90000
        assert c["target_mean"] == 90000
        # 표준편차는 약 7905 (인구표준편차)
        assert 7000 <= c["target_stdev"] <= 9000
        # dispersion ≈ 0.09
        assert 0.07 <= c["target_dispersion"] <= 0.12
        assert c["count"] == 5
        # 3단계 정규화
        d3 = c["opinion_dist_3"]
        assert d3["buy"] == 4   # Buy 3 + Strong Buy 1
        assert d3["hold"] == 1
        assert d3["sell"] == 0
        # 5단계 원본 보존
        d5 = c["opinion_dist_raw"]
        assert d5["strong_buy"] == 1
        assert d5["buy"] == 3
        assert d5["hold"] == 1
        # upside_pct_median
        assert c["upside_pct_median"] is not None
        assert c["upside_pct_median"] > 0

    def test_none_target_excluded_from_stats(self):
        """target_price=None 행은 통계에서 제외, count는 전체."""
        from stock.research_collector import _compute_consensus

        reports = [
            {"broker": "A", "target_price": 80000, "opinion": "Buy"},
            {"broker": "B", "target_price": 100000, "opinion": "Buy"},
            {"broker": "C", "target_price": None, "opinion": "Hold"},
        ]
        c = _compute_consensus(reports, current_price=90000)
        assert c["count"] == 3
        assert c["target_median"] == 90000
        # 의견 분포는 None 행도 포함
        assert sum(c["opinion_dist_3"].values()) == 3

    def test_empty_reports(self):
        from stock.research_collector import _compute_consensus
        c = _compute_consensus([], current_price=80000)
        assert c["count"] == 0
        assert c["target_median"] is None
        assert c["target_mean"] is None
        assert c["target_stdev"] is None
        assert c["target_dispersion"] is None
        assert c["upside_pct_median"] is None

    def test_opinion_korean_mapping(self):
        from stock.research_collector import _compute_consensus
        reports = [
            {"broker": "A", "target_price": 100, "opinion": "매수"},
            {"broker": "B", "target_price": 100, "opinion": "강력매수"},
            {"broker": "C", "target_price": 100, "opinion": "관망"},
            {"broker": "D", "target_price": 100, "opinion": "매도"},
            {"broker": "E", "target_price": 100, "opinion": "강력매도"},
        ]
        c = _compute_consensus(reports, current_price=100)
        # 3단계
        assert c["opinion_dist_3"]["buy"] == 2
        assert c["opinion_dist_3"]["hold"] == 1
        assert c["opinion_dist_3"]["sell"] == 2
        # 5단계 원본
        assert c["opinion_dist_raw"]["strong_buy"] == 1
        assert c["opinion_dist_raw"]["buy"] == 1
        assert c["opinion_dist_raw"]["hold"] == 1
        assert c["opinion_dist_raw"]["sell"] == 1
        assert c["opinion_dist_raw"]["strong_sell"] == 1

    def test_opinion_us_mapping(self):
        from stock.research_collector import _compute_consensus
        reports = [
            {"broker": "GS", "target_price": 100, "opinion": "Overweight"},
            {"broker": "JPM", "target_price": 100, "opinion": "Equal-Weight"},
            {"broker": "MS", "target_price": 100, "opinion": "Underweight"},
        ]
        c = _compute_consensus(reports, current_price=100)
        assert c["opinion_dist_3"]["buy"] == 1
        assert c["opinion_dist_3"]["hold"] == 1
        assert c["opinion_dist_3"]["sell"] == 1


# ────────────────────────────────────────────────────────────────────────────
# REQ-ANALYST-05: momentum + consensus_overheated
# ────────────────────────────────────────────────────────────────────────────


def _hist(broker, days_ago, tp, op="Buy"):
    return {
        "broker": broker,
        "date": (date.today() - timedelta(days=days_ago)).isoformat(),
        "target_price": tp,
        "opinion": op,
    }


class TestMomentum:
    def test_strong_up_and_overheated(self):
        from stock.research_collector import _compute_momentum

        history = [
            _hist("A", 150, 80000),
            _hist("A", 5, 100000),     # +25%
            _hist("B", 140, 85000),
            _hist("B", 8, 110000),     # +29.4%
        ]
        signal, overheated = _compute_momentum(history)
        assert signal == "strong_up"
        assert overheated is True

    def test_flat_when_one_per_broker(self):
        """모든 broker 1건씩 → flat, overheated=False."""
        from stock.research_collector import _compute_momentum
        history = [
            _hist("A", 30, 80000),
            _hist("B", 20, 90000),
        ]
        signal, overheated = _compute_momentum(history)
        assert signal == "flat"
        assert overheated is False

    def test_down_signal(self):
        from stock.research_collector import _compute_momentum
        history = [
            _hist("A", 100, 100000),
            _hist("A", 10, 88000),    # -12%
            _hist("B", 80, 100000),
            _hist("B", 5, 90000),     # -10%
        ]
        signal, overheated = _compute_momentum(history)
        assert signal == "down"
        assert overheated is False

    def test_strong_down_signal(self):
        from stock.research_collector import _compute_momentum
        history = [
            _hist("A", 100, 100000),
            _hist("A", 10, 75000),    # -25%
            _hist("B", 100, 100000),
            _hist("B", 10, 70000),    # -30%
        ]
        signal, overheated = _compute_momentum(history)
        assert signal == "strong_down"
        assert overheated is False

    def test_overheated_threshold_50_pct(self):
        """30% 이상 상향한 broker가 50% 초과면 True."""
        from stock.research_collector import _compute_momentum

        # 4명 중 3명이 30%+ 상향 → 75% > 50%
        history = [
            _hist("A", 100, 80000), _hist("A", 5, 110000),   # +37.5%
            _hist("B", 100, 80000), _hist("B", 5, 105000),   # +31.3%
            _hist("C", 100, 80000), _hist("C", 5, 108000),   # +35%
            _hist("D", 100, 80000), _hist("D", 5, 85000),    # +6.3%
        ]
        _, overheated = _compute_momentum(history)
        assert overheated is True

    def test_not_overheated_when_threshold_not_exceeded(self):
        """30%+ 상향 broker가 정확히 50%면 False (초과 조건)."""
        from stock.research_collector import _compute_momentum
        history = [
            _hist("A", 100, 80000), _hist("A", 5, 110000),   # +37.5%
            _hist("B", 100, 80000), _hist("B", 5, 85000),    # +6.3%
        ]
        _, overheated = _compute_momentum(history)
        # 1/2 = 50%. "초과" 조건이므로 False
        assert overheated is False


# ────────────────────────────────────────────────────────────────────────────
# REQ-ANALYST-07: _collect_analyst_consensus 통합 (Mock)
# ────────────────────────────────────────────────────────────────────────────


class TestCollectAnalystConsensus:
    def _kr_meta(self):
        return [
            {"broker": "미래에셋", "title": "t1", "target_price": 100000,
             "opinion": "Buy", "date": "26.04.28",
             "pdf_url": "https://e.com/1.pdf"},
            {"broker": "키움", "title": "t2", "target_price": 95000,
             "opinion": "Buy", "date": "26.04.26",
             "pdf_url": "https://e.com/2.pdf"},
            {"broker": "한국투자", "title": "t3", "target_price": 88000,
             "opinion": "Hold", "date": "26.04.22",
             "pdf_url": "https://e.com/3.pdf"},
        ]

    def test_kr_collects_pdf_summary(self, db_session, monkeypatch):
        from stock import research_collector

        monkeypatch.setattr(
            "stock.naver_research.fetch_analyst_reports",
            lambda code, limit=20: self._kr_meta(),
        )
        monkeypatch.setattr(
            "stock.analyst_pdf.summarize_one",
            lambda url: "요약 본문",
        )
        # market price fetcher
        monkeypatch.setattr(
            "stock.market.fetch_price",
            lambda code: 90000,
        )
        # session 패치
        from contextlib import contextmanager

        @contextmanager
        def fake_session():
            yield db_session

        monkeypatch.setattr("db.session.get_session", fake_session)

        result = research_collector._collect_analyst_consensus(
            "005930", "KR", "삼성전자",
        )
        assert result["data_source"] == "naver_research"
        assert len(result["reports"]) >= 1
        assert result["reports"][0]["summary"] == "요약 본문"
        assert result["consensus"] is not None
        assert result["consensus"]["count"] >= 1

    def test_us_uses_upgrades_downgrades(self, db_session, monkeypatch):
        from stock import research_collector

        us_meta = [
            {"broker": "Goldman Sachs", "from_grade": "Equal-Weight",
             "to_grade": "Overweight", "action": "up", "date": "2026-04-15"},
            {"broker": "JPMorgan", "from_grade": "Buy",
             "to_grade": "Hold", "action": "down", "date": "2026-04-10"},
        ]
        monkeypatch.setattr(
            "stock.yf_client.fetch_upgrades_downgrades",
            lambda code, limit=20: us_meta,
        )
        monkeypatch.setattr(
            "stock.yf_client.fetch_price_yf",
            lambda code: 200.0,
        )

        from contextlib import contextmanager

        @contextmanager
        def fake_session():
            yield db_session

        monkeypatch.setattr("db.session.get_session", fake_session)

        result = research_collector._collect_analyst_consensus(
            "AAPL", "US", "Apple",
        )
        assert result["data_source"] == "yfinance_upgrades"
        assert all(r["summary"] == "" for r in result["reports"])
        # target_price 부재 → 컨센서스 통계는 None
        cons = result["consensus"]
        assert cons["target_median"] is None
        assert cons["target_mean"] is None

    def test_empty_data_source(self, db_session, monkeypatch):
        from stock import research_collector
        monkeypatch.setattr(
            "stock.naver_research.fetch_analyst_reports",
            lambda code, limit=20: [],
        )

        from contextlib import contextmanager

        @contextmanager
        def fake_session():
            yield db_session

        monkeypatch.setattr("db.session.get_session", fake_session)

        result = research_collector._collect_analyst_consensus(
            "005930", "KR", "삼성전자",
        )
        assert result["data_source"] == "empty"
        assert result["reports"] == []
        # consensus는 None 또는 빈 dict (요건: count=0인 dict 허용)
        assert (result["consensus"] is None) or (result["consensus"]["count"] == 0)


# ────────────────────────────────────────────────────────────────────────────
# REQ-ANALYST-11: 6카테고리 통합 + 기존 5카테고리 호환성
# ────────────────────────────────────────────────────────────────────────────


class TestIntegrationWithCollectAll:
    def test_collect_all_research_includes_analyst_consensus(self, db_session, monkeypatch):
        """tasks 딕셔너리에 analyst_consensus 추가 검증."""
        from stock import research_collector

        # 모든 카테고리를 빈 dict로 모킹 (6번째만 검증)
        monkeypatch.setattr(research_collector, "_collect_basic_macro",
                            lambda c, m, n: {})
        monkeypatch.setattr(research_collector, "_collect_valuation_band",
                            lambda c, m: {})
        monkeypatch.setattr(research_collector, "_collect_management",
                            lambda c, m: {})
        monkeypatch.setattr(research_collector, "_collect_capital_actions",
                            lambda c, m, n: {})
        monkeypatch.setattr(research_collector, "_collect_industry_peers",
                            lambda c, m, n: {})
        monkeypatch.setattr(research_collector, "_collect_analyst_consensus",
                            lambda c, m, n: {
                                "reports": [], "consensus": None,
                                "history_line": "", "momentum_signal": "flat",
                                "consensus_overheated": False,
                                "data_source": "empty",
                            })

        result = research_collector.collect_all_research("005930", "KR", "삼성전자")
        assert "analyst_consensus" in result
        assert "basic_macro" in result
        assert "valuation_band" in result
        assert "management" in result
        assert "capital_actions" in result
        assert "industry_peers" in result
