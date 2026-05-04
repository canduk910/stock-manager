"""신용스프레드 — `services.macro_service.get_credit_spread()` 응답 shape + 일일 캐시.

R3 (P2): IG OAS + HY-IG 스프레드 + 5단계 sentiment + 일일 영속 캐시.

Note: API 통합은 PostgreSQL 컨테이너가 필요 → service 함수 직접 호출로 검증.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from services import macro_service


def _fake_oas_data():
    """fake fred HY OAS 응답 (전 기간 통계 포함)."""
    history = [{"date": f"2024-01-{d:02d}", "oas": float(d) / 2 + 3.0} for d in range(1, 16)]
    return {
        "oas_current": 5.5,
        "oas_history_5y": history,
        "oas_history_full": history,
        "oas_stats": {
            "mean": 5.5, "median": 5.5, "std": 1.0,
            "p10": 3.5, "p25": 4.5, "p50": 5.5, "p75": 6.5,
            "p90": 7.5, "p95": 8.0, "max": 10.5, "max_date": "2020-03-23",
        },
        "oas_percentile": 50.0,
        "oas_zscore": 0.0,
        "sentiment": "normal",
        "oas_history": history,
        "percentile": 50.0,
    }


def _fake_ig_data():
    history = [{"date": f"2024-01-{d:02d}", "ig": 1.0 + float(d) / 30} for d in range(1, 16)]
    return {
        "ig_current": 1.4,
        "ig_history_5y": history,
        "ig_stats": {"mean": 1.3, "median": 1.3, "std": 0.1, "p90": 1.5, "max": 2.0},
    }


def _patches(oas=None, ig=None, cached=None):
    """공용 patch 리스트 — fetcher cache·DB 캐시·yfinance·FRED 함수."""
    if oas is None:
        oas = _fake_oas_data()
    if ig is None:
        ig = _fake_ig_data()
    return [
        patch("stock.macro_fetcher._fetch_fred_oas", return_value=oas),
        patch("stock.macro_fetcher._fetch_fred_ig_oas", return_value=ig),
        patch("stock.macro_fetcher.get_cached", return_value=None),
        patch("stock.macro_fetcher.set_cached"),
        patch("services.macro_service.get_macro_today", return_value=cached),
        patch("services.macro_service.save_macro_today"),
        # yfinance HYG/LQD는 빈 응답 (외부 의존 격리)
        patch("stock.macro_fetcher._safe", side_effect=lambda v: v),
    ]


class TestCreditSpreadShape:
    def test_response_shape_full_fields(self):
        """credit_spread 응답에 oas_stats / oas_percentile / ig_current / hy_ig_spread / 5단계 sentiment 존재."""
        # yfinance 모킹 — Ticker 호출 시 빈 history 반환
        import pandas as pd

        class FakeTicker:
            def __init__(self, sym):
                self.info = {"yield": 0.07, "trailingAnnualDividendYield": None}

            def history(self, *args, **kwargs):
                return pd.DataFrame()

        ctxs = _patches() + [patch("yfinance.Ticker", FakeTicker)]
        with _MultiPatch(ctxs):
            result = macro_service.get_credit_spread()
            cs = result["credit_spread"]
            assert cs is not None
            # HY OAS 통계
            assert "oas_stats" in cs
            stats = cs["oas_stats"]
            for key in ("mean", "p10", "p50", "p90", "max"):
                assert key in stats
            # 백분위
            assert cs.get("oas_percentile") is not None
            # 5단계 sentiment
            assert cs.get("oas_sentiment") in {
                "extreme_greed", "greed", "normal", "fear", "extreme_fear",
            }
            # IG OAS + HY-IG
            assert cs.get("ig_current") == 1.4
            assert cs.get("hy_ig_spread") is not None
            # 후방호환 alias
            assert "oas_history" in cs

    def test_partial_failure_ig_missing(self):
        """IG OAS 실패 시 partial_failure에 ig_oas 포함, HY 데이터 정상."""
        import pandas as pd

        class FakeTicker:
            def __init__(self, sym):
                self.info = {"yield": 0.07}

            def history(self, *args, **kwargs):
                return pd.DataFrame()

        ctxs = _patches(ig={}) + [patch("yfinance.Ticker", FakeTicker)]
        with _MultiPatch(ctxs):
            result = macro_service.get_credit_spread()
            cs = result["credit_spread"]
            assert "ig_oas" in cs.get("partial_failure", [])
            # HY 데이터는 정상
            assert cs.get("oas_current") is not None
            assert cs.get("oas_sentiment") in {
                "extreme_greed", "greed", "normal", "fear", "extreme_fear",
            }

    def test_daily_cache_hit_on_second_call(self):
        """get_macro_today에서 데이터 반환 시 외부 fetch 미호출."""
        cached_data = _fake_oas_data()
        cached_data["ig_current"] = 1.4
        cached_data["hy_ig_spread"] = 4.1
        cached_data["partial_failure"] = []

        with patch("services.macro_service.get_macro_today", return_value=cached_data), \
             patch("stock.macro_fetcher.fetch_credit_spread") as mock_fetch:
            result = macro_service.get_credit_spread()
            cs = result["credit_spread"]
            assert cs.get("oas_current") == 5.5
            mock_fetch.assert_not_called()


class _MultiPatch:
    """다수 patch contextmanager 동시 적용."""

    def __init__(self, patches):
        self.patches = patches

    def __enter__(self):
        for p in self.patches:
            p.start()
        return self

    def __exit__(self, *args):
        for p in self.patches:
            try:
                p.stop()
            except Exception:
                pass
