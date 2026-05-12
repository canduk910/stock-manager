"""SupplyDemandService 단위 테스트.

REQ-SUPPLY-CACHE-01 / REQ-SUPPLY-MACRO-01 / REQ-SUPPLY-STOCK-01.
- fetch_market_supply_demand(market, days)
- fetch_stock_supply_demand(code, days)
- 단위 변환(백만원 → 억원, ÷100, 반올림)
- 누적합 계산
- color_map 응답
- advisory_note 고정 + 매매 액션 키 부재
- 예외 매핑 (ServiceError/ConfigError/ExternalAPIError/NotFoundError)
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from services.exceptions import (
    ConfigError, ExternalAPIError, NotFoundError, ServiceError,
)


# ── 공용 fixtures ─────────────────────────────────────────────────────────────

def _wrapper_market_row(date="2024-05-17", p=720787, f=-597490, o=-150685, idx=2724.62):
    """wrapper.get_market_investor_daily가 반환하는 표준화 한 행."""
    return {
        "date": date,
        "index_close": idx,
        "prev_diff": -28.38,
        "prev_pct": -1.03,
        "personal_net_amt": p,
        "foreign_net_amt": f,
        "institution_net_amt": o,
        "securities_net_amt": -18893,
        "inv_trust_net_amt": -7246,
        "private_fund_net_amt": -25668,
        "bank_net_amt": 3326,
        "insurance_net_amt": -13791,
        "mrbn_net_amt": -2742,
        "pension_net_amt": -85671,
        "etc_finance_net_amt": 27388,
        "etc_corp_net_amt": 27388,
        "etc_org_net_amt": 0,
    }


def _wrapper_stock_row(date="2025-08-11", close=71000, p=120110, f=-144363, o=-40903):
    return {
        "date": date,
        "close_price": close,
        "personal_net_amt": p,
        "foreign_net_amt": f,
        "institution_net_amt": o,
        "personal_buy_amt": 262790,
        "personal_sell_amt": 142680,
        "foreign_buy_amt": 180172,
        "foreign_sell_amt": 324535,
        "institution_buy_amt": 293298,
        "institution_sell_amt": 334201,
        "securities_net_amt": -3169,
        "inv_trust_net_amt": -14641,
        "private_fund_net_amt": -8887,
        "bank_net_amt": 209,
        "insurance_net_amt": -6061,
        "mrbn_net_amt": -52,
        "pension_net_amt": -8301,
        "etc_finance_net_amt": 65156,
        "etc_corp_net_amt": 65156,
        "etc_org_net_amt": 0,
    }


@pytest.fixture(autouse=True)
def _disable_macro_store_cache():
    """macro_store hit으로 KIS 호출이 스킵되는 것을 방지(테스트는 매번 호출 검증).

    영속 캐시 hit 시나리오는 별도 test 클래스에서 명시적으로 활성화.
    """
    with patch("services.supply_demand_service.macro_store.get_today", return_value=None), \
         patch("services.supply_demand_service.macro_store.save_today"):
        yield


@pytest.fixture(autouse=True)
def _ensure_kis_keys(monkeypatch):
    """기본 fixture: KIS 키 설정된 환경 가정 (개별 테스트에서 override)."""
    monkeypatch.setattr("services.supply_demand_service.KIS_APP_KEY", "TEST_KEY")
    monkeypatch.setattr("services.supply_demand_service.KIS_APP_SECRET", "TEST_SECRET")


# ── REQ-SUPPLY-MACRO-01: fetch_market_supply_demand ──────────────────────────

class TestFetchMarketSupplyDemand:

    def test_kospi_ok_response_shape(self):
        from services import supply_demand_service as svc
        rows = [
            _wrapper_market_row(date=f"2024-05-{15+i:02d}", p=100 * (i + 1) * 100,
                                f=-50 * (i + 1) * 100, o=-50 * (i + 1) * 100)
            for i in range(20)
        ]
        with patch("services.supply_demand_service.get_market_investor_daily",
                   return_value=rows):
            result = svc.fetch_market_supply_demand("kospi", days=20)

        assert result["market"] == "kospi"
        assert result["days"] == 20
        # color_map
        assert result["color_map"]["personal"] == "#EF4444"
        assert result["color_map"]["foreign"] == "#3B82F6"
        assert result["color_map"]["institution"] == "#10B981"
        # daily 길이
        assert len(result["daily"]) == 20
        # 단위 변환 확인 (백만원 → 억원, ÷100)
        first = result["daily"][0]
        assert first["personal_net"] == 100  # 10000백만원 ÷ 100 = 100억원
        assert first["foreign_net"] == -50
        assert first["institution_net"] == -50
        # institution_detail 11종 중 핵심 키 존재
        detail = first["institution_detail"]
        for key in ("securities", "inv_trust", "private_fund", "bank",
                    "insurance", "mrbn", "pension", "etc_finance",
                    "etc_corp", "etc_org"):
            assert key in detail
        # cumulative
        assert len(result["cumulative"]) == 20
        # 마지막 cumulative.foreign_cum == sum(daily[i].foreign_net)
        expected_cum = sum(d["foreign_net"] for d in result["daily"])
        assert result["cumulative"][-1]["foreign_cum"] == expected_cum
        # summary
        s = result["summary"]
        assert s["personal_today"] == result["daily"][-1]["personal_net"]
        assert s["foreign_today"] == result["daily"][-1]["foreign_net"]
        assert s["personal_cum_total"] == sum(d["personal_net"] for d in result["daily"])

    def test_kosdaq_ok(self):
        from services import supply_demand_service as svc
        rows = [_wrapper_market_row(date="2024-05-17")]
        with patch("services.supply_demand_service.get_market_investor_daily",
                   return_value=rows):
            r = svc.fetch_market_supply_demand("kosdaq", days=10)
        assert r["market"] == "kosdaq"

    def test_invalid_market_raises_service_error(self):
        from services import supply_demand_service as svc
        with pytest.raises(ServiceError):
            svc.fetch_market_supply_demand("FX", days=20)
        with pytest.raises(ServiceError):
            svc.fetch_market_supply_demand("KOSPI", days=20)  # 대소문자 구분

    def test_days_out_of_range_raises_service_error(self):
        from services import supply_demand_service as svc
        with pytest.raises(ServiceError):
            svc.fetch_market_supply_demand("kospi", days=5)
        with pytest.raises(ServiceError):
            svc.fetch_market_supply_demand("kospi", days=70)

    def test_missing_kis_key_raises_config_error(self, monkeypatch):
        from services import supply_demand_service as svc
        monkeypatch.setattr("services.supply_demand_service.KIS_APP_KEY", "")
        with pytest.raises(ConfigError):
            svc.fetch_market_supply_demand("kospi", days=20)

    def test_wrapper_external_error_propagates(self):
        from services import supply_demand_service as svc
        with patch("services.supply_demand_service.get_market_investor_daily",
                   side_effect=ExternalAPIError("KIS down")):
            with pytest.raises(ExternalAPIError):
                svc.fetch_market_supply_demand("kospi", days=20)

    def test_unit_conversion_rounding(self):
        """백만원 720787 → 7208억원 (반올림)."""
        from services import supply_demand_service as svc
        rows = [_wrapper_market_row(date="2024-05-17", p=720787, f=-597490, o=-150685)]
        with patch("services.supply_demand_service.get_market_investor_daily",
                   return_value=rows):
            r = svc.fetch_market_supply_demand("kospi", days=10)
        d = r["daily"][0]
        # 720787 / 100 = 7207.87 → 반올림 7208
        assert d["personal_net"] == 7208
        # -597490 / 100 = -5974.9 → 반올림 -5975
        assert d["foreign_net"] == -5975

    def test_cumulative_starts_from_zero(self):
        """cumulative는 기간 시작일부터 누적합."""
        from services import supply_demand_service as svc
        rows = [
            {**_wrapper_market_row(date="2024-05-17"), "personal_net_amt": 100, "foreign_net_amt": 200, "institution_net_amt": -300},
            {**_wrapper_market_row(date="2024-05-18"), "personal_net_amt": 150, "foreign_net_amt": -50, "institution_net_amt": 100},
        ]
        with patch("services.supply_demand_service.get_market_investor_daily",
                   return_value=rows):
            r = svc.fetch_market_supply_demand("kospi", days=10)
        # day0: personal_net = 1 (100/100), cum = 1
        # day1: personal_net = 2 (150/100=1.5→2), cum = 3
        assert r["cumulative"][0]["personal_cum"] == r["daily"][0]["personal_net"]
        assert r["cumulative"][1]["personal_cum"] == \
            r["daily"][0]["personal_net"] + r["daily"][1]["personal_net"]

    def test_partial_response_short(self):
        """KIS가 휴장 등으로 days보다 적게 반환 → 그대로 표시."""
        from services import supply_demand_service as svc
        rows = [_wrapper_market_row(date=f"2024-05-{i:02d}") for i in [15, 16]]
        with patch("services.supply_demand_service.get_market_investor_daily",
                   return_value=rows):
            r = svc.fetch_market_supply_demand("kospi", days=20)
        assert r["days"] == 20  # 요청값 유지
        assert len(r["daily"]) == 2  # 실제 응답 일수
        assert len(r["cumulative"]) == 2


# ── REQ-SUPPLY-STOCK-01: fetch_stock_supply_demand ───────────────────────────

class TestFetchStockSupplyDemand:

    def test_stock_ok_with_advisory_note(self):
        from services import supply_demand_service as svc
        rows = [_wrapper_stock_row()]
        with patch("services.supply_demand_service.get_stock_investor_daily",
                   return_value=rows):
            r = svc.fetch_stock_supply_demand("005930", days=10)
        # advisory_note 고정 문구
        assert "advisory_note" in r
        assert "참고용" in r["advisory_note"]
        assert "Graham" in r["advisory_note"]
        # 매매 액션 키 금지(OrderAdvisor 자문)
        for forbidden in ("recommendation", "action", "buy_signal", "trade_signal"):
            assert forbidden not in r, f"매매 액션 키 금지: {forbidden}"
        # color_map
        assert r["color_map"]["personal"] == "#EF4444"
        # 매수/매도 분리 단위 변환 (262790 / 100 = 2628)
        first = r["daily"][0]
        assert first["personal_buy"] == 2628
        assert first["personal_sell"] == 1427  # 142680/100=1426.8 → 1427
        assert first["close"] == 71000

    def test_non_domestic_code_raises_service_error(self):
        from services import supply_demand_service as svc
        with pytest.raises(ServiceError):
            svc.fetch_stock_supply_demand("AAPL", days=30)

    def test_days_out_of_range_raises_service_error(self):
        from services import supply_demand_service as svc
        with pytest.raises(ServiceError):
            svc.fetch_stock_supply_demand("005930", days=5)
        with pytest.raises(ServiceError):
            svc.fetch_stock_supply_demand("005930", days=100)

    def test_missing_kis_key_raises_config_error(self, monkeypatch):
        from services import supply_demand_service as svc
        monkeypatch.setattr("services.supply_demand_service.KIS_APP_KEY", "")
        with pytest.raises(ConfigError):
            svc.fetch_stock_supply_demand("005930", days=30)

    def test_kis_error_raises_not_found(self):
        """KIS rt_cd!="0"는 wrapper에서 ExternalAPIError로 올라오지만,
        서비스 레이어는 종목 미존재 경우(빈 응답)와 일관성을 위해 NotFoundError로 매핑."""
        from services import supply_demand_service as svc
        with patch("services.supply_demand_service.get_stock_investor_daily",
                   return_value=[]):
            with pytest.raises(NotFoundError):
                svc.fetch_stock_supply_demand("999999", days=30)

    def test_kis_500_raises_external_api(self):
        from services import supply_demand_service as svc
        with patch("services.supply_demand_service.get_stock_investor_daily",
                   side_effect=ExternalAPIError("KIS 500")):
            with pytest.raises(ExternalAPIError):
                svc.fetch_stock_supply_demand("005930", days=30)

    def test_new_listing_partial_response(self):
        from services import supply_demand_service as svc
        rows = [_wrapper_stock_row(date=f"2025-08-0{i+1}") for i in range(7)]
        with patch("services.supply_demand_service.get_stock_investor_daily",
                   return_value=rows):
            r = svc.fetch_stock_supply_demand("005930", days=30)
        assert len(r["daily"]) == 7  # 부분 응답 그대로

    def test_buy_minus_sell_equals_net_consistency(self):
        """매수/매도/순매수 일관성 — 백만원→억원 단위 변환 후에도 유지."""
        from services import supply_demand_service as svc
        # 백만원 단위로 일관된 값: foreign_net_amt = buy(180172) - sell(324535) = -144363
        # 억원 환산: buy=1802, sell=3245, net=-1444 → 1802-3245=-1443 (반올림 차 ±1 허용)
        rows = [_wrapper_stock_row()]
        with patch("services.supply_demand_service.get_stock_investor_daily",
                   return_value=rows):
            r = svc.fetch_stock_supply_demand("005930", days=10)
        d = r["daily"][0]
        # 반올림 차 ±1 허용
        assert abs((d["foreign_buy"] - d["foreign_sell"]) - d["foreign_net"]) <= 1


# ── REQ-SUPPLY-CACHE-01: 영속 캐시 + 장중 in-memory ───────────────────────

class TestSupplyDemandCache:

    def test_persistent_cache_hit_skips_kis(self):
        """macro_store에 같은 카테고리 데이터 있으면 wrapper 호출 0회."""
        from services import supply_demand_service as svc
        # 캐시된 응답 (이미 표준화된 wrapper 결과 그대로 저장)
        cached_rows = [_wrapper_market_row(date="2024-05-17")]
        # autouse fixture를 override
        with patch("services.supply_demand_service.macro_store.get_today",
                   return_value=cached_rows), \
             patch("services.supply_demand_service.macro_store.save_today"), \
             patch("services.supply_demand_service.get_market_investor_daily") as wrapper_mock:
            r = svc.fetch_market_supply_demand("kospi", days=20)
            assert wrapper_mock.call_count == 0
        assert len(r["daily"]) == 1

    def test_cache_miss_calls_kis_and_saves(self):
        """캐시 미스 시 wrapper 호출 + macro_store.save_today 호출."""
        from services import supply_demand_service as svc
        rows = [_wrapper_market_row(date="2024-05-17")]
        with patch("services.supply_demand_service.macro_store.get_today",
                   return_value=None), \
             patch("services.supply_demand_service.macro_store.save_today") as save_mock, \
             patch("services.supply_demand_service.get_market_investor_daily",
                   return_value=rows) as wrapper_mock:
            svc.fetch_market_supply_demand("kospi", days=20)
        assert wrapper_mock.call_count == 1
        assert save_mock.call_count == 1
        # 카테고리 키 명명 확인
        call_args = save_mock.call_args[0]
        assert call_args[0] == "supply_demand:market:kospi"

    def test_stock_cache_key_includes_code(self):
        from services import supply_demand_service as svc
        rows = [_wrapper_stock_row()]
        with patch("services.supply_demand_service.macro_store.get_today",
                   return_value=None), \
             patch("services.supply_demand_service.macro_store.save_today") as save_mock, \
             patch("services.supply_demand_service.get_stock_investor_daily",
                   return_value=rows):
            svc.fetch_stock_supply_demand("005930", days=30)
        assert save_mock.call_args[0][0] == "supply_demand:stock:005930"


# ── 회귀 가드: 결함 응답(zero-row) 영속 캐시 방지 ─────────────────────────────
#
# 결함 이력(2026-05-12): wrapper의 KIS 파라미터 결함으로 KIS가 전 행
# personal/foreign/institution net_amt=0을 반환했고, 그 결과가
# macro_store에 KST 일자 캐시로 영속 저장되어 wrapper 수정 후에도
# 캐시 hit으로 UI에 빈 데이터가 계속 노출됨.
#
# 가드 정책:
# - wrapper 응답이 전 행 zero-row → 캐시 저장 거부 + ExternalAPIError 표면화
# - 캐시 hit이 전 행 zero-row → 자동 폐기 + wrapper 재호출 (영속 결함 자동 회복)
# - 일부 행만 0(휴장일 등)은 정상으로 간주 (false positive 방지)


def _zero_market_row(date: str = "2026-05-12") -> dict:
    """전 net_amt가 0인 결함 응답 행(시장)."""
    return _wrapper_market_row(date=date, p=0, f=0, o=0, idx=7920.97)


def _zero_stock_row(date: str = "2026-05-12") -> dict:
    return _wrapper_stock_row(date=date, p=0, f=0, o=0)


class TestZeroRowGuard:
    """REQ-SUPPLY-CACHE-01 회귀: zero-row 영속 캐시 방지."""

    def test_is_all_zero_net_helper(self):
        """_is_all_zero_net 헬퍼 단독 검증."""
        from services.supply_demand_service import _is_all_zero_net
        assert _is_all_zero_net([_zero_market_row() for _ in range(5)]) is True
        assert _is_all_zero_net([_wrapper_market_row() for _ in range(5)]) is False
        # 빈 배열은 False (신규 상장 케이스는 별도 분기)
        assert _is_all_zero_net([]) is False
        # 일부 행만 0(휴장일 가정): 한 행이라도 비-0이면 정상
        mixed = [_zero_market_row(), _zero_market_row(), _wrapper_market_row()]
        assert _is_all_zero_net(mixed) is False

    def test_wrapper_returns_zero_rows_raises_external_api_error(self):
        """wrapper 응답이 전 행 zero-row → ExternalAPIError + 캐시 저장 거부."""
        from services import supply_demand_service as svc
        zero_rows = [_zero_market_row(date=f"2026-05-{1+i:02d}") for i in range(20)]

        with patch("services.supply_demand_service.macro_store.get_today",
                   return_value=None), \
             patch("services.supply_demand_service.macro_store.save_today") as save_mock, \
             patch("services.supply_demand_service.get_market_investor_daily",
                   return_value=zero_rows):
            with pytest.raises(ExternalAPIError):
                svc.fetch_market_supply_demand("kospi", days=20)

        # 캐시 저장 안 됨 — 핵심 가드
        assert save_mock.call_count == 0

    def test_cached_zero_rows_invalidate_and_refetch(self):
        """캐시 hit + zero-row → delete_today 호출 + wrapper 재호출 → 정상 응답으로 회복."""
        from services import supply_demand_service as svc
        cached_zero = [_zero_market_row(date=f"2026-05-{1+i:02d}") for i in range(60)]
        healthy_rows = [_wrapper_market_row(date=f"2026-05-{1+i:02d}",
                                            p=100000, f=-50000, o=-50000)
                        for i in range(60)]

        with patch("services.supply_demand_service.macro_store.get_today",
                   return_value=cached_zero), \
             patch("services.supply_demand_service.macro_store.delete_today") as del_mock, \
             patch("services.supply_demand_service.macro_store.save_today") as save_mock, \
             patch("services.supply_demand_service.get_market_investor_daily",
                   return_value=healthy_rows) as wrapper_mock:
            r = svc.fetch_market_supply_demand("kospi", days=20)

        # 결함 캐시 폐기
        assert del_mock.call_count == 1
        assert del_mock.call_args[0][0] == "supply_demand:market:kospi"
        # wrapper 재호출
        assert wrapper_mock.call_count == 1
        # 새 정상 데이터 캐시 저장
        assert save_mock.call_count == 1
        # 응답 정상화 확인
        assert r["daily"][-1]["personal_net"] == 1000  # 100000백만원 ÷ 100 = 1000억원

    def test_cached_zero_and_refetch_also_zero_raises(self):
        """캐시 hit zero-row → wrapper 재호출도 zero-row → ExternalAPIError (무한 루프 방지)."""
        from services import supply_demand_service as svc
        cached_zero = [_zero_market_row() for _ in range(10)]
        wrapper_zero = [_zero_market_row(date=f"2026-05-{1+i:02d}") for i in range(20)]

        with patch("services.supply_demand_service.macro_store.get_today",
                   return_value=cached_zero), \
             patch("services.supply_demand_service.macro_store.delete_today"), \
             patch("services.supply_demand_service.macro_store.save_today") as save_mock, \
             patch("services.supply_demand_service.get_market_investor_daily",
                   return_value=wrapper_zero) as wrapper_mock:
            with pytest.raises(ExternalAPIError):
                svc.fetch_market_supply_demand("kospi", days=20)

        # wrapper는 한 번만 호출(재시도 루프 없음)
        assert wrapper_mock.call_count == 1
        # 결함 응답은 캐시 저장 거부
        assert save_mock.call_count == 0

    def test_partial_zero_rows_pass_through(self):
        """일부 행만 0(휴장일 등) → 정상 통과 (false positive 방지)."""
        from services import supply_demand_service as svc
        # 처음 3행은 0(휴장일 가정), 이후 17행은 정상
        mixed = [_zero_market_row(date=f"2026-05-{1+i:02d}") for i in range(3)]
        mixed += [_wrapper_market_row(date=f"2026-05-{4+i:02d}",
                                       p=100000, f=-50000, o=-50000)
                  for i in range(17)]

        with patch("services.supply_demand_service.macro_store.get_today",
                   return_value=None), \
             patch("services.supply_demand_service.macro_store.save_today") as save_mock, \
             patch("services.supply_demand_service.get_market_investor_daily",
                   return_value=mixed):
            r = svc.fetch_market_supply_demand("kospi", days=20)

        # 정상 동작 + 캐시 저장
        assert save_mock.call_count == 1
        assert len(r["daily"]) == 20

    def test_stock_zero_rows_also_guarded(self):
        """종목 TR도 동일하게 zero-row 시 ExternalAPIError."""
        from services import supply_demand_service as svc
        zero_rows = [_zero_stock_row(date=f"2026-05-{1+i:02d}") for i in range(20)]

        with patch("services.supply_demand_service.macro_store.get_today",
                   return_value=None), \
             patch("services.supply_demand_service.macro_store.save_today") as save_mock, \
             patch("services.supply_demand_service.get_stock_investor_daily",
                   return_value=zero_rows):
            with pytest.raises(ExternalAPIError):
                svc.fetch_stock_supply_demand("005930", days=20)

        assert save_mock.call_count == 0
