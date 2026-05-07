"""advisory_fetcher.fetch_business_model 단위 테스트."""

from unittest.mock import patch, MagicMock

import pytest

from stock import advisory_fetcher


def _ai_resp(payload: dict) -> MagicMock:
    import json as _json
    msg = MagicMock()
    msg.content = _json.dumps(payload, ensure_ascii=False)
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.fixture(autouse=True)
def _reset_cache(monkeypatch):
    """캐시 격리: get_cached → None, set_cached은 리스트에 기록."""
    captured = {}

    def fake_get(key):
        return captured.get(key)

    def fake_set(key, value, ttl_hours=24):
        captured[key] = value
        captured[f"__ttl__{key}"] = ttl_hours

    monkeypatch.setattr("stock.cache.get_cached", fake_get)
    monkeypatch.setattr("stock.cache.set_cached", fake_set)
    return captured


class TestFetchBusinessModel:
    def test_returns_three_keys_on_gpt_success(self, _reset_cache):
        payload = {
            "revenue_model": "B2C 직판 + 일부 B2B 위탁판매로 매출 발생.",
            "cash_generation": "OCF/NI 1.1, FCF 마진 8% 양호. capex/OCF 25%로 자산경량.",
            "rd_strategy": "신소재 R&D 비중 6%, 산업 평균 대비 적정.",
        }
        with patch.object(advisory_fetcher, "OPENAI_API_KEY", "sk-test"), \
             patch("services.ai_gateway.call_openai_chat", return_value=_ai_resp(payload)) as m:
            result = advisory_fetcher.fetch_business_model(
                "005930", "삼성전자", "KR",
                segments_dict={"segments": [], "description": "반도체", "keywords": ["반도체"]},
                financial_dict={"income_stmt": [], "cashflow": []},
                user_id=42,
            )
        assert result["revenue_model"].startswith("B2C")
        assert "FCF" in result["cash_generation"]
        assert result["rd_strategy"].startswith("신소재")
        kwargs = m.call_args.kwargs
        assert kwargs["service_name"] == "advisory_business_model"
        assert kwargs["user_id"] == 42
        assert kwargs["max_completion_tokens"] == 1500
        # response_format이 json_object여야 함
        assert kwargs["response_format"] == {"type": "json_object"}
        # 시스템 프롬프트에 도메인 가이드 키워드 포함
        sys_msg = kwargs["messages"][0]
        assert sys_msg["role"] == "system"
        assert "MarginAnalyst" in sys_msg["content"]
        assert "ValueScreener" in sys_msg["content"]
        assert "OCF" in sys_msg["content"]
        assert "Value trap" in sys_msg["content"]

    def test_cache_hit_skips_gpt(self, _reset_cache):
        # 미리 캐시에 값 주입
        cached = {"revenue_model": "X", "cash_generation": "Y", "rd_strategy": "Z"}
        _reset_cache["advisor:business_model:KR:005930"] = cached
        with patch.object(advisory_fetcher, "OPENAI_API_KEY", "sk-test"), \
             patch("services.ai_gateway.call_openai_chat") as m:
            result = advisory_fetcher.fetch_business_model(
                "005930", "삼성전자", "KR",
                segments_dict={}, financial_dict={}, user_id=1,
            )
        assert result == cached
        m.assert_not_called()

    def test_no_openai_key_returns_empty(self, _reset_cache):
        with patch.object(advisory_fetcher, "OPENAI_API_KEY", ""):
            result = advisory_fetcher.fetch_business_model(
                "005930", "삼성전자", "KR",
                segments_dict={}, financial_dict={}, user_id=1,
            )
        assert result == {"revenue_model": None, "cash_generation": None, "rd_strategy": None}

    def test_gpt_exception_returns_empty(self, _reset_cache):
        with patch.object(advisory_fetcher, "OPENAI_API_KEY", "sk-test"), \
             patch("services.ai_gateway.call_openai_chat", side_effect=RuntimeError("boom")):
            result = advisory_fetcher.fetch_business_model(
                "005930", "삼성전자", "KR",
                segments_dict={}, financial_dict={}, user_id=1,
            )
        assert all(v is None for v in result.values())

    def test_partial_response_keeps_present_fields(self, _reset_cache):
        payload = {
            "revenue_model": "A",
            # cash_generation 없음
            "rd_strategy": "C",
        }
        with patch.object(advisory_fetcher, "OPENAI_API_KEY", "sk-test"), \
             patch("services.ai_gateway.call_openai_chat", return_value=_ai_resp(payload)):
            result = advisory_fetcher.fetch_business_model(
                "AAPL", "Apple", "US",
                segments_dict={}, financial_dict={}, user_id=1,
            )
        assert result["revenue_model"] == "A"
        assert result["cash_generation"] is None
        assert result["rd_strategy"] == "C"

    def test_empty_response_not_cached(self, _reset_cache):
        # 모든 키 None 반환 시 캐시 저장하지 않아 다음 호출에서 재시도
        with patch.object(advisory_fetcher, "OPENAI_API_KEY", "sk-test"), \
             patch("services.ai_gateway.call_openai_chat", return_value=_ai_resp({})):
            advisory_fetcher.fetch_business_model(
                "AAPL", "Apple", "US",
                segments_dict={}, financial_dict={}, user_id=1,
            )
        assert "advisor:business_model:US:AAPL" not in _reset_cache

    def test_cache_ttl_seven_days(self, _reset_cache):
        payload = {"revenue_model": "X", "cash_generation": "Y", "rd_strategy": "Z"}
        with patch.object(advisory_fetcher, "OPENAI_API_KEY", "sk-test"), \
             patch("services.ai_gateway.call_openai_chat", return_value=_ai_resp(payload)):
            advisory_fetcher.fetch_business_model(
                "AAPL", "Apple", "US",
                segments_dict={}, financial_dict={}, user_id=1,
            )
        assert _reset_cache.get("__ttl__advisor:business_model:US:AAPL") == 7 * 24

    def test_financial_context_includes_cf_keys(self, _reset_cache):
        """프롬프트에 영업CF·CAPEX 같은 재무 컨텍스트가 들어가야 함."""
        payload = {"revenue_model": "x", "cash_generation": "y", "rd_strategy": "z"}
        captured_messages = {}

        def _capture(**kwargs):
            captured_messages.update(kwargs)
            return _ai_resp(payload)

        with patch.object(advisory_fetcher, "OPENAI_API_KEY", "sk-test"), \
             patch("services.ai_gateway.call_openai_chat", side_effect=_capture):
            advisory_fetcher.fetch_business_model(
                "005930", "삼성전자", "KR",
                segments_dict={"segments": [{"segment": "반도체", "revenue_pct": 60.0}]},
                financial_dict={
                    "income_stmt": [
                        {"year": 2023, "revenue": 1e12, "net_income": 1e11},
                        {"year": 2024, "revenue": 1.1e12, "net_income": 1.2e11},
                    ],
                    "cashflow": [
                        {"year": 2023, "operating_cf": 9e10, "investing_cf": -3e10,
                         "financing_cf": -2e10, "capex": 2.5e10, "free_cf": 6.5e10},
                    ],
                },
                user_id=1,
            )
        user_msg = captured_messages["messages"][1]["content"]
        assert "영업CF" in user_msg
        assert "CAPEX" in user_msg
        assert "FCF" in user_msg
