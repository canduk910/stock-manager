"""KIS wrapper 수급 TR 메서드 단위 테스트.

REQ-SUPPLY-API-01 / REQ-SUPPLY-API-02 수용 기준 검증.
- get_market_investor_daily(market_code, days): FHPTJ04040000
- get_stock_investor_daily(code, days): FHPTJ04160001

KIS API 키 미사용 — requests.get을 monkeypatch로 mock.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from services.exceptions import ExternalAPIError


# ── 공용 mock 응답 빌더 ───────────────────────────────────────────────────────

def _make_market_row(date: str = "20240517") -> dict:
    """REQ-SUPPLY-API-01 시장 TR(FHPTJ04040000) output 한 행."""
    return {
        "stck_bsop_date": date,
        "bstp_nmix_prpr": "2724.62",
        "bstp_nmix_prdy_vrss": "-28.38",
        "prdy_vrss_sign": "5",
        "bstp_nmix_prdy_ctrt": "-1.03",
        # 거래대금(백만원) — 11종 분해 + 합계 3종
        "prsn_ntby_tr_pbmn": "720787",
        "frgn_ntby_tr_pbmn": "-597490",
        "orgn_ntby_tr_pbmn": "-150685",
        "scrt_ntby_tr_pbmn": "-18893",
        "ivtr_ntby_tr_pbmn": "-7246",
        "pe_fund_ntby_tr_pbmn": "-25668",
        "bank_ntby_tr_pbmn": "3326",
        "insu_ntby_tr_pbmn": "-13791",
        "mrbn_ntby_tr_pbmn": "-2742",
        "fund_ntby_tr_pbmn": "-85671",
        "etc_ntby_tr_pbmn": "27388",
        "etc_orgt_ntby_tr_pbmn": "0",
        "etc_corp_ntby_tr_pbmn": "27388",
    }


def _make_stock_row(date: str = "20250811") -> dict:
    """REQ-SUPPLY-API-02 종목 TR(FHPTJ04160001) output2 한 행 (매수/매도 분리 포함)."""
    return {
        "stck_bsop_date": date,
        "stck_clpr": "71000",
        # 순매수 거래대금
        "prsn_ntby_tr_pbmn": "120110",
        "frgn_ntby_tr_pbmn": "-144363",
        "orgn_ntby_tr_pbmn": "-40903",
        # 기관 11종
        "scrt_ntby_tr_pbmn": "-3169",
        "ivtr_ntby_tr_pbmn": "-14641",
        "pe_fund_ntby_tr_pbmn": "-8887",
        "bank_ntby_tr_pbmn": "209",
        "insu_ntby_tr_pbmn": "-6061",
        "mrbn_ntby_tr_pbmn": "-52",
        "fund_ntby_tr_pbmn": "-8301",
        "etc_ntby_tr_pbmn": "65156",
        "etc_orgt_ntby_tr_pbmn": "0",
        "etc_corp_ntby_tr_pbmn": "65156",
        # 매수/매도 분리
        "prsn_seln_tr_pbmn": "142680",
        "prsn_shnu_tr_pbmn": "262790",
        "frgn_seln_tr_pbmn": "324535",
        "frgn_shnu_tr_pbmn": "180172",
        "orgn_seln_tr_pbmn": "334201",
        "orgn_shnu_tr_pbmn": "293298",
    }


class _FakeResp:
    """requests.Response 흉내."""
    def __init__(self, data: Any, status_code: int = 200):
        self._data = data
        self.status_code = status_code
        self.text = str(data)

    def json(self):
        return self._data


# ── REQ-SUPPLY-API-01: 시장별 투자자매매동향(일별) ────────────────────────────

class TestGetMarketInvestorDaily:
    """wrapper.get_market_investor_daily(market_code, days=20)"""

    def test_market_kospi_returns_list_of_dicts(self):
        """KOSPI(U001) 정상 호출 → 표준화 키 모두 포함된 list 반환."""
        from wrapper import get_market_investor_daily

        rows = [_make_market_row(date=f"2024051{d}") for d in range(7)]
        with patch("wrapper.requests.get", return_value=_FakeResp({"rt_cd": "0", "output": rows})), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            result = get_market_investor_daily("U001", days=7)

        assert isinstance(result, list)
        assert len(result) == 7
        first = result[0]
        # 표준화 키 (요건서 REQ-SUPPLY-API-01)
        for key in [
            "date", "index_close", "prev_diff", "prev_pct",
            "personal_net_amt", "foreign_net_amt", "institution_net_amt",
            "securities_net_amt", "inv_trust_net_amt", "private_fund_net_amt",
            "bank_net_amt", "insurance_net_amt", "mrbn_net_amt",
            "pension_net_amt", "etc_finance_net_amt", "etc_corp_net_amt",
            "etc_org_net_amt",
        ]:
            assert key in first, f"missing key: {key}"
        # date 포맷: YYYY-MM-DD
        assert first["date"][4] == "-" and first["date"][7] == "-"
        # 백만원 단위 유지 (서비스 레이어에서 ÷100 변환)
        assert first["personal_net_amt"] == 720787
        assert first["foreign_net_amt"] == -597490
        assert first["institution_net_amt"] == -150685

    def test_market_kosdaq_returns_list(self):
        """KOSDAQ(U201) 정상 호출."""
        from wrapper import get_market_investor_daily
        rows = [_make_market_row() for _ in range(3)]
        with patch("wrapper.requests.get", return_value=_FakeResp({"rt_cd": "0", "output": rows})), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            result = get_market_investor_daily("U201", days=3)
        assert len(result) == 3

    def test_invalid_market_code_raises_value_error(self):
        """허용 외 market_code → ValueError."""
        from wrapper import get_market_investor_daily
        with pytest.raises(ValueError):
            get_market_investor_daily("U999", days=20)
        with pytest.raises(ValueError):
            get_market_investor_daily("kospi", days=20)
        with pytest.raises(ValueError):
            get_market_investor_daily("", days=20)

    def test_invalid_days_raises_value_error(self):
        """days 범위 외(0, 음수, 60 초과) → ValueError."""
        from wrapper import get_market_investor_daily
        with pytest.raises(ValueError):
            get_market_investor_daily("U001", days=0)
        with pytest.raises(ValueError):
            get_market_investor_daily("U001", days=-1)
        with pytest.raises(ValueError):
            get_market_investor_daily("U001", days=70)

    def test_kis_error_raises_external_api_error(self):
        """KIS rt_cd != "0" 또는 HTTP 5xx → ExternalAPIError(502)."""
        from wrapper import get_market_investor_daily

        with patch("wrapper.requests.get", return_value=_FakeResp({"rt_cd": "1", "msg1": "ERR"})), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            with pytest.raises(ExternalAPIError):
                get_market_investor_daily("U001", days=20)

    def test_http_503_raises_external_api_error(self):
        """HTTP 503 → ExternalAPIError."""
        from wrapper import get_market_investor_daily

        with patch("wrapper.requests.get", return_value=_FakeResp({"msg1": "down"}, status_code=503)), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            with pytest.raises(ExternalAPIError):
                get_market_investor_daily("U001", days=20)

    def test_market_iscd_mapping_kospi(self):
        """KOSPI는 FID_INPUT_ISCD=0001, FID_INPUT_ISCD_1=KSP, FID_INPUT_ISCD_2=0001.

        회귀 가드: 과거 ISCD_2에 KSP를 넣어 KIS가 빈 net_amt(전 행 0)와
        엉뚱한 지수값을 반환한 결함(2026-05-12) 재발 방지. KIS 명세상
        FID_INPUT_ISCD_2는 "하위 분류코드(업종분류코드)"이므로 0001/1001.
        """
        from wrapper import get_market_investor_daily

        captured = {}

        def _fake_get(url, headers=None, params=None, timeout=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["params"] = params
            return _FakeResp({"rt_cd": "0", "output": [_make_market_row()]})

        with patch("wrapper.requests.get", side_effect=_fake_get), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            get_market_investor_daily("U001", days=20)

        assert captured["params"]["FID_COND_MRKT_DIV_CODE"] == "U"
        assert captured["params"]["FID_INPUT_ISCD"] == "0001"
        assert captured["params"]["FID_INPUT_ISCD_1"] == "KSP"
        assert captured["params"]["FID_INPUT_ISCD_2"] == "0001"
        assert captured["headers"]["tr_id"] == "FHPTJ04040000"

    def test_market_iscd_mapping_kosdaq(self):
        """KOSDAQ는 FID_INPUT_ISCD=1001, FID_INPUT_ISCD_1=KSQ, FID_INPUT_ISCD_2=1001.

        회귀 가드: KSQ를 ISCD_2에 넣던 결함 재발 방지.
        """
        from wrapper import get_market_investor_daily

        captured = {}

        def _fake_get(url, headers=None, params=None, timeout=None):
            captured["params"] = params
            return _FakeResp({"rt_cd": "0", "output": [_make_market_row()]})

        with patch("wrapper.requests.get", side_effect=_fake_get), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            get_market_investor_daily("U201", days=20)

        assert captured["params"]["FID_INPUT_ISCD"] == "1001"
        assert captured["params"]["FID_INPUT_ISCD_1"] == "KSQ"
        assert captured["params"]["FID_INPUT_ISCD_2"] == "1001"


# ── REQ-SUPPLY-API-02: 종목별 투자자매매동향(일별) ───────────────────────────

class TestGetStockInvestorDaily:
    """wrapper.get_stock_investor_daily(code, days=30)"""

    def test_stock_returns_list_with_buy_sell_split(self):
        """정상 호출 → 표준화 키 + 매수/매도 분리 + close_price 포함."""
        from wrapper import get_stock_investor_daily

        rows = [_make_stock_row(date=f"2025081{d}") for d in range(5)]
        with patch("wrapper.requests.get",
                   return_value=_FakeResp({"rt_cd": "0",
                                           "output1": {"stck_prpr": "71100"},
                                           "output2": rows})), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            result = get_stock_investor_daily("005930", days=5)

        assert isinstance(result, list)
        assert len(result) == 5
        first = result[0]
        for key in [
            "date", "close_price",
            "personal_net_amt", "foreign_net_amt", "institution_net_amt",
            "personal_buy_amt", "personal_sell_amt",
            "foreign_buy_amt", "foreign_sell_amt",
            "institution_buy_amt", "institution_sell_amt",
            "securities_net_amt", "inv_trust_net_amt", "private_fund_net_amt",
            "bank_net_amt", "insurance_net_amt", "mrbn_net_amt",
            "pension_net_amt", "etc_finance_net_amt",
            "etc_corp_net_amt", "etc_org_net_amt",
        ]:
            assert key in first, f"missing key: {key}"
        # close_price 정수형
        assert isinstance(first["close_price"], int)
        # 매수/매도 분리값 정수
        assert first["personal_buy_amt"] == 262790
        assert first["personal_sell_amt"] == 142680
        # 순매수 = 매수 - 매도 (KIS 응답 직접 검증)
        assert first["foreign_buy_amt"] == 180172
        assert first["foreign_sell_amt"] == 324535

    def test_non_6digit_code_raises_value_error(self):
        """6자리 숫자가 아닌 코드 → ValueError."""
        from wrapper import get_stock_investor_daily
        with pytest.raises(ValueError):
            get_stock_investor_daily("AAPL", days=30)
        with pytest.raises(ValueError):
            get_stock_investor_daily("00593", days=30)
        with pytest.raises(ValueError):
            get_stock_investor_daily("0059300", days=30)
        with pytest.raises(ValueError):
            get_stock_investor_daily("00593A", days=30)

    def test_invalid_days_raises_value_error(self):
        """days 범위 외 → ValueError."""
        from wrapper import get_stock_investor_daily
        with pytest.raises(ValueError):
            get_stock_investor_daily("005930", days=0)
        with pytest.raises(ValueError):
            get_stock_investor_daily("005930", days=70)

    def test_new_listing_short_response_ok(self):
        """신규 상장 등으로 7일만 응답 → 길이 7 list 반환(예외 X)."""
        from wrapper import get_stock_investor_daily

        rows = [_make_stock_row() for _ in range(7)]
        with patch("wrapper.requests.get",
                   return_value=_FakeResp({"rt_cd": "0",
                                           "output1": {"stck_prpr": "1000"},
                                           "output2": rows})), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            result = get_stock_investor_daily("005930", days=30)
        assert len(result) == 7  # 응답된 만큼만

    def test_kis_error_raises_external_api_error(self):
        """KIS rt_cd!="0" → ExternalAPIError."""
        from wrapper import get_stock_investor_daily

        with patch("wrapper.requests.get",
                   return_value=_FakeResp({"rt_cd": "1", "msg1": "ERR"})), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            with pytest.raises(ExternalAPIError):
                get_stock_investor_daily("005930", days=30)

    def test_stock_tr_id_and_params(self):
        """TR_ID=FHPTJ04160001 + FID_COND_MRKT_DIV_CODE=J + FID_ETC_CLS_CODE=1."""
        from wrapper import get_stock_investor_daily

        captured = {}

        def _fake_get(url, headers=None, params=None, timeout=None):
            captured["params"] = params
            captured["headers"] = headers
            return _FakeResp({"rt_cd": "0",
                              "output1": {"stck_prpr": "71100"},
                              "output2": [_make_stock_row()]})

        with patch("wrapper.requests.get", side_effect=_fake_get), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            get_stock_investor_daily("005930", days=30)

        assert captured["headers"]["tr_id"] == "FHPTJ04160001"
        assert captured["params"]["FID_COND_MRKT_DIV_CODE"] == "J"
        assert captured["params"]["FID_INPUT_ISCD"] == "005930"
        assert captured["params"]["FID_ETC_CLS_CODE"] == "1"


# ── 회귀: 종목 TR DATE_1 — KST 15:40 cutoff 후퇴 로직 ─────────────────────────
#
# KIS FHPTJ04160001 명세: "해당일 조회는 장 종료 후 정상 조회 가능".
# wrapper는 KST 평일 15:40 이전 또는 주말이면 FID_INPUT_DATE_1을
# 직전 영업일로 자동 후퇴하여 장중에도 TIME LIMIT 회피.
# 결함 이력(2026-05-12): now()로 오늘 날짜만 박아 장중 TIME LIMIT 발생.

import datetime as _real_dt


def _freeze_kst(monkeypatch, year: int, month: int, day: int, hour: int, minute: int = 0) -> None:
    """wrapper.datetime.datetime.now만 KST 고정 — timezone/timedelta는 원본 유지."""
    import wrapper as _wrapper
    _real = _wrapper.datetime.datetime
    frozen = _real_dt.datetime(year, month, day, hour, minute, tzinfo=_real_dt.timezone(_real_dt.timedelta(hours=9)))

    class _Frozen(_real):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return frozen.replace(tzinfo=None)
            return frozen.astimezone(tz)

    monkeypatch.setattr(_wrapper.datetime, "datetime", _Frozen)


class TestStockDateRollback:
    """REQ-SUPPLY-API-02 회귀: KST cutoff 15:40 분기."""

    def _capture_date(self, monkeypatch) -> str:
        """get_stock_investor_daily 호출 시 KIS에 보낸 FID_INPUT_DATE_1 캡처."""
        from wrapper import get_stock_investor_daily
        captured: dict = {}

        def _fake_get(url, headers=None, params=None, timeout=None):
            captured["params"] = params
            return _FakeResp({"rt_cd": "0",
                              "output1": {"stck_prpr": "71100"},
                              "output2": [_make_stock_row()]})

        monkeypatch.setattr("wrapper.requests.get", _fake_get)
        monkeypatch.setattr("wrapper._kis_token", lambda: "DUMMY")
        monkeypatch.setattr("wrapper._kis_app_key", lambda: ("AK", "AS"))
        get_stock_investor_daily("005930", days=30)
        return captured["params"]["FID_INPUT_DATE_1"]

    def test_intraday_falls_back_to_previous_business_day(self, monkeypatch):
        """평일 10:00 KST (장중, 15:40 이전) → DATE_1 = 어제(평일)."""
        # 2026-05-12(화) 10:00 → 어제 2026-05-11(월)
        _freeze_kst(monkeypatch, 2026, 5, 12, 10, 0)
        assert self._capture_date(monkeypatch) == "20260511"

    def test_after_close_uses_today(self, monkeypatch):
        """평일 16:00 KST (15:40 이후) → DATE_1 = 오늘."""
        # 2026-05-12(화) 16:00 → 오늘 2026-05-12
        _freeze_kst(monkeypatch, 2026, 5, 12, 16, 0)
        assert self._capture_date(monkeypatch) == "20260512"

    def test_exactly_at_cutoff_uses_today(self, monkeypatch):
        """평일 15:40:00 KST (cutoff 정각) → 오늘. 경계값."""
        _freeze_kst(monkeypatch, 2026, 5, 12, 15, 40)
        assert self._capture_date(monkeypatch) == "20260512"

    def test_saturday_falls_back_to_friday(self, monkeypatch):
        """토요일 호출 → 직전 금요일."""
        # 2026-05-16(토) 10:00 → 금요일 2026-05-15
        _freeze_kst(monkeypatch, 2026, 5, 16, 10, 0)
        assert self._capture_date(monkeypatch) == "20260515"

    def test_sunday_falls_back_to_friday(self, monkeypatch):
        """일요일 호출 → 직전 금요일 (토 건너뜀)."""
        # 2026-05-17(일) 10:00 → 금요일 2026-05-15
        _freeze_kst(monkeypatch, 2026, 5, 17, 10, 0)
        assert self._capture_date(monkeypatch) == "20260515"

    def test_monday_intraday_falls_back_to_friday(self, monkeypatch):
        """월요일 장중 → 직전 금요일 (일·토 건너뜀)."""
        # 2026-05-18(월) 10:00 → 금요일 2026-05-15
        _freeze_kst(monkeypatch, 2026, 5, 18, 10, 0)
        assert self._capture_date(monkeypatch) == "20260515"
