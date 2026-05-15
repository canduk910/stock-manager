"""KIS wrapper 외국인 보유 TR 메서드 단위 테스트.

REQ-FH-API-01 / REQ-FH-API-02 수용 기준 검증.

- get_foreign_holding_snapshot(code) → FHKST01010100
- get_foreign_holding_daily(code, days=30) → FHKST01010400

KIS API 키 미사용 — requests.get을 monkeypatch로 mock.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from services.exceptions import ExternalAPIError, NotFoundError


# ── 공용 mock 응답 빌더 ───────────────────────────────────────────────────────

def _snapshot_output() -> dict:
    """FHKST01010100 output(주식현재가 시세) 한 행. 외국인 관련 필드 포함."""
    return {
        "lstn_stcn": "5970240000",           # 상장 주수
        "frgn_hldn_qty": "3223990000",       # 외국인 보유 수량
        "hts_frgn_ehrt": "54.00",            # 외국인 소진율 (%)
        # 무관 필드(존재 무시 검증)
        "stck_prpr": "71000",
    }


def _daily_row(date: str = "20240517", close: int = 71000,
               ehrt: str = "54.00", ntby: int = 152000) -> dict:
    """FHKST01010400 output 한 행(주식현재가 일자별)."""
    return {
        "stck_bsop_date": date,
        "stck_clpr": str(close),
        "hts_frgn_ehrt": ehrt,
        "frgn_ntby_qty": str(ntby),
        # 무관 필드
        "acml_vol": "1000000",
    }


class _FakeResp:
    """requests.Response 흉내."""
    def __init__(self, data: Any, status_code: int = 200):
        self._data = data
        self.status_code = status_code
        self.text = str(data)

    def json(self):
        return self._data


# ── REQ-FH-API-01: 종목 현재 스냅샷 헬퍼 ──────────────────────────────────────

class TestGetForeignHoldingSnapshot:
    """wrapper.get_foreign_holding_snapshot(code)"""

    def test_005930_returns_standardized_keys(self):
        """정상 호출 → code/lstn_stcn/frgn_hldn_qty/hts_frgn_ehrt/as_of_date."""
        from wrapper import get_foreign_holding_snapshot

        with patch("wrapper.requests.get",
                   return_value=_FakeResp({"rt_cd": "0", "output": _snapshot_output()})), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            result = get_foreign_holding_snapshot("005930")

        assert result["code"] == "005930"
        assert result["lstn_stcn"] == 5970240000
        assert result["frgn_hldn_qty"] == 3223990000
        assert result["hts_frgn_ehrt"] == 54.00
        # as_of_date: YYYY-MM-DD 형식
        assert isinstance(result["as_of_date"], str)
        assert len(result["as_of_date"]) == 10
        assert result["as_of_date"][4] == "-" and result["as_of_date"][7] == "-"

    def test_code_too_short_raises_value_error(self):
        from wrapper import get_foreign_holding_snapshot
        with pytest.raises(ValueError):
            get_foreign_holding_snapshot("00593")

    def test_code_non_numeric_raises_value_error(self):
        """미국 티커 등 6자리 알파벳 → ValueError."""
        from wrapper import get_foreign_holding_snapshot
        with pytest.raises(ValueError):
            get_foreign_holding_snapshot("AAPL")

    def test_kis_error_rt_cd_raises_external(self):
        from wrapper import get_foreign_holding_snapshot

        with patch("wrapper.requests.get",
                   return_value=_FakeResp({"rt_cd": "1", "msg1": "KIS error", "output": {}})), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            with pytest.raises(ExternalAPIError):
                get_foreign_holding_snapshot("005930")

    def test_empty_output_raises_not_found(self):
        from wrapper import get_foreign_holding_snapshot

        with patch("wrapper.requests.get",
                   return_value=_FakeResp({"rt_cd": "0", "output": {}})), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            with pytest.raises(NotFoundError):
                get_foreign_holding_snapshot("005930")

    def test_empty_fields_normalize_to_none(self):
        """빈 문자열 frgn_hldn_qty/hts_frgn_ehrt → None (예외 X)."""
        from wrapper import get_foreign_holding_snapshot

        output = _snapshot_output()
        output["frgn_hldn_qty"] = ""
        output["hts_frgn_ehrt"] = ""
        with patch("wrapper.requests.get",
                   return_value=_FakeResp({"rt_cd": "0", "output": output})), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            result = get_foreign_holding_snapshot("005930")

        assert result["frgn_hldn_qty"] is None
        assert result["hts_frgn_ehrt"] is None

    def test_http_5xx_raises_external(self):
        from wrapper import get_foreign_holding_snapshot

        with patch("wrapper.requests.get",
                   return_value=_FakeResp({"detail": "err"}, status_code=500)), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            with pytest.raises(ExternalAPIError):
                get_foreign_holding_snapshot("005930")

    def test_request_params_match_spec(self):
        """tr_id=FHKST01010100, FID_COND_MRKT_DIV_CODE=J, FID_INPUT_ISCD=code."""
        from wrapper import get_foreign_holding_snapshot

        captured = {}

        def _mock_get(url, **kw):
            captured["url"] = url
            captured["headers"] = kw.get("headers", {})
            captured["params"] = kw.get("params", {})
            return _FakeResp({"rt_cd": "0", "output": _snapshot_output()})

        with patch("wrapper.requests.get", side_effect=_mock_get), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            get_foreign_holding_snapshot("005930")

        assert captured["headers"].get("tr_id") == "FHKST01010100"
        params_norm = {k.upper(): v for k, v in captured["params"].items()}
        assert params_norm.get("FID_COND_MRKT_DIV_CODE") == "J"
        assert params_norm.get("FID_INPUT_ISCD") == "005930"


# ── REQ-FH-API-02: 종목 외국인 보유율 일별 시계열 헬퍼 ────────────────────────

class TestGetForeignHoldingDaily:
    """wrapper.get_foreign_holding_daily(code, days=30)"""

    def test_005930_returns_ascending_rows(self):
        from wrapper import get_foreign_holding_daily

        # KIS는 최신→과거. 정렬 검증을 위해 의도적으로 역순 mock.
        rows = [
            _daily_row("20240520", 71500, "54.10", 152000),
            _daily_row("20240517", 71000, "54.00", 100000),
            _daily_row("20240516", 70500, "53.90", 80000),
        ]
        with patch("wrapper.requests.get",
                   return_value=_FakeResp({"rt_cd": "0", "output": rows})), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            result = get_foreign_holding_daily("005930", days=30)

        assert isinstance(result, list)
        assert len(result) == 3
        # 오름차순
        assert result[0]["date"] < result[-1]["date"]
        first = result[0]
        for key in ("date", "close", "hts_frgn_ehrt", "frgn_ntby_qty"):
            assert key in first
        assert first["close"] == 70500
        assert first["hts_frgn_ehrt"] == 53.90
        assert first["frgn_ntby_qty"] == 80000

    def test_days_param_slicing(self):
        from wrapper import get_foreign_holding_daily

        rows = [_daily_row(f"202405{d:02d}") for d in range(1, 21)]
        with patch("wrapper.requests.get",
                   return_value=_FakeResp({"rt_cd": "0", "output": rows})), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            result = get_foreign_holding_daily("005930", days=5)
        assert len(result) == 5
        # 최근 5개 유지
        assert result[-1]["date"] == "2024-05-20"

    def test_days_zero_raises_value_error(self):
        from wrapper import get_foreign_holding_daily
        with pytest.raises(ValueError):
            get_foreign_holding_daily("005930", days=0)

    def test_days_over_30_raises_value_error(self):
        from wrapper import get_foreign_holding_daily
        with pytest.raises(ValueError):
            get_foreign_holding_daily("005930", days=60)

    def test_non_numeric_code_raises(self):
        from wrapper import get_foreign_holding_daily
        with pytest.raises(ValueError):
            get_foreign_holding_daily("AAPL", days=30)

    def test_kis_error_raises_external(self):
        from wrapper import get_foreign_holding_daily
        with patch("wrapper.requests.get",
                   return_value=_FakeResp({"rt_cd": "1", "msg1": "err", "output": []})), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            with pytest.raises(ExternalAPIError):
                get_foreign_holding_daily("005930", days=30)

    def test_empty_output_returns_empty_list(self):
        """신규 상장/거래정지 종목 → 빈 list 반환(예외 X)."""
        from wrapper import get_foreign_holding_daily
        with patch("wrapper.requests.get",
                   return_value=_FakeResp({"rt_cd": "0", "output": []})), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            result = get_foreign_holding_daily("005930", days=30)
        assert result == []

    def test_empty_ehrt_normalizes_to_none(self):
        """빈 문자열 hts_frgn_ehrt → None."""
        from wrapper import get_foreign_holding_daily
        rows = [_daily_row("20240517", 71000, "", 100000)]
        with patch("wrapper.requests.get",
                   return_value=_FakeResp({"rt_cd": "0", "output": rows})), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            result = get_foreign_holding_daily("005930", days=30)
        assert len(result) == 1
        assert result[0]["hts_frgn_ehrt"] is None

    def test_empty_ntby_normalizes_to_zero(self):
        """빈 문자열 frgn_ntby_qty → 0."""
        from wrapper import get_foreign_holding_daily
        row = _daily_row("20240517", 71000, "54.00", 0)
        row["frgn_ntby_qty"] = ""
        with patch("wrapper.requests.get",
                   return_value=_FakeResp({"rt_cd": "0", "output": [row]})), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            result = get_foreign_holding_daily("005930", days=30)
        assert result[0]["frgn_ntby_qty"] == 0

    def test_request_params_match_spec(self):
        """tr_id=FHKST01010400, 기간코드 D, 수정주가 0000000001."""
        from wrapper import get_foreign_holding_daily

        captured = {}

        def _mock_get(url, **kw):
            captured["headers"] = kw.get("headers", {})
            captured["params"] = kw.get("params", {})
            return _FakeResp({"rt_cd": "0", "output": []})

        with patch("wrapper.requests.get", side_effect=_mock_get), \
             patch("wrapper._kis_token", return_value="DUMMY"), \
             patch("wrapper._kis_app_key", return_value=("AK", "AS")):
            get_foreign_holding_daily("005930", days=30)

        assert captured["headers"].get("tr_id") == "FHKST01010400"
        params_norm = {k.upper(): v for k, v in captured["params"].items()}
        assert params_norm.get("FID_COND_MRKT_DIV_CODE") == "J"
        assert params_norm.get("FID_INPUT_ISCD") == "005930"
        assert params_norm.get("FID_PERIOD_DIV_CODE") == "D"
