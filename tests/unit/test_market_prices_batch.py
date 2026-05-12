"""stock.market.fetch_prices_batch 단위 테스트 (RED → GREEN).

요건:
- 1차: yfinance Tickers 일괄 호출 (KR `.KS`/`.KQ`)
- 2차 폴백: yfinance 빈 응답 / 예외 시 KIS REST FHKST01010100 종목별 호출
- 부분 실패 시 성공한 종목만 반환
- in-memory TTL 캐시 (장중 10초 / 장외 60초)
- N>20 가드 (분당 제한 보호)
"""

import pytest
from unittest.mock import patch, MagicMock


# ── 1. 시그니처 / 기본 동작 ──────────────────────────────────────────────────

class TestFetchPricesBatchSignature:

    def test_function_exists_and_callable(self):
        """fetch_prices_batch 함수가 존재해야 한다."""
        from stock.market import fetch_prices_batch
        assert callable(fetch_prices_batch)

    def test_empty_codes_returns_empty(self):
        """빈 codes → 빈 dict 반환 (외부 호출 없음)."""
        from stock.market import fetch_prices_batch
        result = fetch_prices_batch([], market="KR")
        assert result == {}

    def test_returns_dict_keyed_by_code(self):
        """반환 shape: {code: {price, change, change_pct, prev_close, volume, ...}}."""
        from stock.market import fetch_prices_batch
        import stock.market as mkt

        fake_fi_005930 = MagicMock(
            last_price=72000.0,
            previous_close=71000.0,
            last_volume=12345678,
        )
        fake_fi_000660 = MagicMock(
            last_price=125000.0,
            previous_close=120000.0,
            last_volume=5000000,
        )

        # _yf_batch_fast_info 가 dict 반환하도록 mock
        def fake_batch(codes, market):
            return {
                "005930.KS": fake_fi_005930,
                "000660.KS": fake_fi_000660,
            }

        with patch.object(mkt, "_yf_batch_fast_info", side_effect=fake_batch), \
             patch.object(mkt, "_resolve_kr_yf_tickers", return_value={"005930": "005930.KS", "000660": "000660.KS"}):
            # 캐시 초기화
            mkt._prices_batch_cache.clear()
            result = fetch_prices_batch(["005930", "000660"], market="KR")

        assert "005930" in result
        assert "000660" in result
        assert result["005930"]["price"] == pytest.approx(72000.0)
        assert result["005930"]["prev_close"] == pytest.approx(71000.0)
        # change_pct = (72000-71000)/71000*100 ≈ 1.4084
        assert result["005930"]["change_pct"] == pytest.approx(1.41, abs=0.05)
        assert result["005930"]["change"] == pytest.approx(1000.0)


# ── 2. KIS REST 폴백 ────────────────────────────────────────────────────────

class TestFetchPricesBatchKISFallback:

    def test_kis_fallback_when_yfinance_returns_none(self):
        """yfinance가 모든 종목 None → KIS REST 폴백."""
        from stock.market import fetch_prices_batch
        import stock.market as mkt

        # yfinance는 빈 결과
        with patch.object(mkt, "_yf_batch_fast_info", return_value={}), \
             patch.object(mkt, "_resolve_kr_yf_tickers", return_value={"005930": "005930.KS"}), \
             patch.object(mkt, "_kis_rest_price_batch") as kis_mock:
            kis_mock.return_value = {
                "005930": {
                    "price": 72500.0,
                    "change": 500.0,
                    "change_pct": 0.69,
                    "prev_close": 72000.0,
                    "volume": 9876543,
                }
            }
            mkt._prices_batch_cache.clear()
            result = fetch_prices_batch(["005930"], market="KR")

        kis_mock.assert_called_once()
        assert "005930" in result
        assert result["005930"]["price"] == pytest.approx(72500.0)

    def test_kis_fallback_when_yfinance_raises(self):
        """yfinance가 예외 raise → KIS REST 폴백."""
        from stock.market import fetch_prices_batch
        import stock.market as mkt

        def raise_exc(*a, **kw):
            raise RuntimeError("yfinance failed")

        with patch.object(mkt, "_yf_batch_fast_info", side_effect=raise_exc), \
             patch.object(mkt, "_resolve_kr_yf_tickers", return_value={"005930": "005930.KS"}), \
             patch.object(mkt, "_kis_rest_price_batch") as kis_mock:
            kis_mock.return_value = {
                "005930": {"price": 72500.0, "change": 0, "change_pct": 0, "prev_close": 72500.0, "volume": 0}
            }
            mkt._prices_batch_cache.clear()
            result = fetch_prices_batch(["005930"], market="KR")

        assert "005930" in result
        kis_mock.assert_called_once()


# ── 3. 부분 실패 ──────────────────────────────────────────────────────────────

class TestFetchPricesBatchPartial:

    def test_partial_success_only_returns_successful(self):
        """일부 종목만 yfinance 응답 있을 때 → 그 종목만 채워서 반환."""
        from stock.market import fetch_prices_batch
        import stock.market as mkt

        fake_fi = MagicMock(last_price=72000.0, previous_close=71000.0, last_volume=100)

        # 005930만 응답, 999999는 없음
        with patch.object(mkt, "_yf_batch_fast_info", return_value={"005930.KS": fake_fi}), \
             patch.object(mkt, "_resolve_kr_yf_tickers", return_value={"005930": "005930.KS", "999999": None}), \
             patch.object(mkt, "_kis_rest_price_batch", return_value={}):
            mkt._prices_batch_cache.clear()
            result = fetch_prices_batch(["005930", "999999"], market="KR")

        assert "005930" in result
        # 999999는 yfinance도 ticker resolve 실패, KIS도 빈 결과 → 미포함 (또는 None)
        # 부분 결과 정책: 키 자체 없거나 None 값
        assert "999999" not in result or result.get("999999") is None


# ── 4. TTL 캐시 ───────────────────────────────────────────────────────────────

class TestFetchPricesBatchCache:

    def test_cache_hit_skips_external_call(self):
        """동일 코드 연속 호출 시 캐시 적중 → 외부 호출 1회만."""
        from stock.market import fetch_prices_batch
        import stock.market as mkt

        fake_fi = MagicMock(last_price=72000.0, previous_close=71000.0, last_volume=100)

        call_count = {"n": 0}

        def counting_batch(codes, market):
            call_count["n"] += 1
            return {"005930.KS": fake_fi}

        with patch.object(mkt, "_yf_batch_fast_info", side_effect=counting_batch), \
             patch.object(mkt, "_resolve_kr_yf_tickers", return_value={"005930": "005930.KS"}):
            mkt._prices_batch_cache.clear()
            r1 = fetch_prices_batch(["005930"], market="KR")
            r2 = fetch_prices_batch(["005930"], market="KR")

        assert call_count["n"] == 1, "두 번째 호출은 캐시에서 응답해야 함"
        assert r1 == r2


# ── 5. N 가드 (분당 제한 보호) ────────────────────────────────────────────────

class TestFetchPricesBatchGuard:

    def test_kis_fallback_n_gt_20_skipped(self):
        """yfinance 실패 후 KIS 폴백 시 N>20 이면 KIS 호출 생략 (분당 제한 보호)."""
        from stock.market import fetch_prices_batch
        import stock.market as mkt

        codes = [f"{i:06d}" for i in range(25)]
        ticker_map = {c: f"{c}.KS" for c in codes}

        # yfinance는 빈 결과
        with patch.object(mkt, "_yf_batch_fast_info", return_value={}), \
             patch.object(mkt, "_resolve_kr_yf_tickers", return_value=ticker_map), \
             patch.object(mkt, "_kis_rest_price_batch") as kis_mock:
            kis_mock.return_value = {}
            mkt._prices_batch_cache.clear()
            result = fetch_prices_batch(codes, market="KR")

        # KIS는 호출되지 않거나, 최대 20개로 제한
        if kis_mock.called:
            called_codes = kis_mock.call_args.args[0] if kis_mock.call_args.args else kis_mock.call_args.kwargs.get("codes", [])
            assert len(called_codes) <= 20, "KIS 폴백은 N≤20 가드 적용"
