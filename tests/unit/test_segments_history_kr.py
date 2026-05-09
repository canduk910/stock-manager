"""advisory_fetcher.fetch_segments_history_kr (Phase 1A) 회귀 테스트.

2026-05-10 ValueScreener 자문: 5년치 사업부문 매출비중 추이 GPT 통합 추론.
- composite_score 미반영 (디스플레이 한정)
- "AI 추정" 면책 의무 (source="gpt_inference", confidence="low")
- DART 본문 파싱(Phase B)에서 source="dart_parsed"로 교체 예정
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from stock import advisory_fetcher


def _mock_chat_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.fixture(autouse=True)
def _clear_segments_cache():
    """각 테스트 후 segments_history 캐시 prefix 정리."""
    yield
    try:
        from stock.cache import delete_prefix
        delete_prefix("advisor:segments_history_kr:")
    except Exception:
        pass


def test_returns_empty_when_no_api_key():
    """OPENAI_API_KEY None → years_data=[]."""
    with patch("stock.advisory_fetcher.OPENAI_API_KEY", ""):
        result = advisory_fetcher.fetch_segments_history_kr("005930", "삼성전자", years=5)
        assert result["years_data"] == []
        assert result["confidence"] == "low"
        assert result["source"] == "gpt_inference"


def test_cache_hit_skips_gpt_call():
    """캐시 prefill 후 ai_gateway mock 미호출."""
    cached_value = {
        "years_data": [{"year": 2024, "segments": [{"segment": "반도체", "revenue_pct": 100.0, "note": "AI추정"}]}],
        "highlights": {"growing": [], "shrinking": []},
        "confidence": "low",
        "source": "gpt_inference",
    }
    with patch("stock.advisory_fetcher.OPENAI_API_KEY", "sk-test"), \
         patch("stock.cache.get_cached", return_value=cached_value), \
         patch("services.ai_gateway.call_openai_chat") as mock_chat:
        result = advisory_fetcher.fetch_segments_history_kr("005930", "삼성전자", years=5)
        assert result == cached_value
        mock_chat.assert_not_called()


def test_cache_key_includes_years_param():
    """years=3 vs years=5 캐시 키 분리."""
    captured_keys = []

    def fake_get_cached(key):
        captured_keys.append(key)
        return None

    with patch("stock.advisory_fetcher.OPENAI_API_KEY", ""), \
         patch("stock.cache.get_cached", side_effect=fake_get_cached):
        advisory_fetcher.fetch_segments_history_kr("005930", "삼성전자", years=3)
        advisory_fetcher.fetch_segments_history_kr("005930", "삼성전자", years=5)
    assert "advisor:segments_history_kr:005930:3" in captured_keys
    assert "advisor:segments_history_kr:005930:5" in captured_keys


def test_parses_years_data_array():
    """GPT 응답 mock JSON → years_data 정상 파싱."""
    gpt_response = json.dumps({
        "years_data": [
            {"year": 2023, "segments": [
                {"segment": "반도체", "revenue_pct": 60},
                {"segment": "스마트폰", "revenue_pct": 30},
                {"segment": "디스플레이", "revenue_pct": 10},
            ]},
            {"year": 2024, "segments": [
                {"segment": "반도체", "revenue_pct": 70},
                {"segment": "스마트폰", "revenue_pct": 25},
                {"segment": "디스플레이", "revenue_pct": 5},
            ]},
        ]
    })
    with patch("stock.advisory_fetcher.OPENAI_API_KEY", "sk-test"), \
         patch("stock.cache.get_cached", return_value=None), \
         patch("stock.cache.set_cached"), \
         patch("services.ai_gateway.call_openai_chat", return_value=_mock_chat_response(gpt_response)):
        result = advisory_fetcher.fetch_segments_history_kr("005930", "삼성전자", years=2)
    assert len(result["years_data"]) == 2
    assert result["years_data"][0]["year"] == 2023
    assert result["years_data"][1]["year"] == 2024
    # 정렬 검증 (과거 → 최신)
    assert result["years_data"][-1]["segments"][0]["segment"] == "반도체"
    assert result["years_data"][-1]["segments"][0]["note"] == "AI추정"


def test_handles_malformed_gpt_response():
    """비정상 JSON → 빈 결과 + 예외 미전파."""
    with patch("stock.advisory_fetcher.OPENAI_API_KEY", "sk-test"), \
         patch("stock.cache.get_cached", return_value=None), \
         patch("services.ai_gateway.call_openai_chat", return_value=_mock_chat_response("not a json")):
        result = advisory_fetcher.fetch_segments_history_kr("005930", "삼성전자", years=5)
    assert result["years_data"] == []
    assert result["source"] == "gpt_inference"


def test_highlights_identifies_growing_segment():
    """첫 vs 끝 ±5%p 임계 — 성장 사업 식별."""
    gpt_response = json.dumps({
        "years_data": [
            {"year": 2021, "segments": [
                {"segment": "반도체", "revenue_pct": 50},
                {"segment": "스마트폰", "revenue_pct": 50},
            ]},
            {"year": 2025, "segments": [
                {"segment": "반도체", "revenue_pct": 70},
                {"segment": "스마트폰", "revenue_pct": 30},
            ]},
        ]
    })
    with patch("stock.advisory_fetcher.OPENAI_API_KEY", "sk-test"), \
         patch("stock.cache.get_cached", return_value=None), \
         patch("stock.cache.set_cached"), \
         patch("services.ai_gateway.call_openai_chat", return_value=_mock_chat_response(gpt_response)):
        result = advisory_fetcher.fetch_segments_history_kr("005930", "삼성전자", years=5)
    growing = result["highlights"]["growing"]
    shrinking = result["highlights"]["shrinking"]
    assert any(s["segment"] == "반도체" and s["delta_pct"] == 20.0 for s in growing)
    assert any(s["segment"] == "스마트폰" and s["delta_pct"] == -20.0 for s in shrinking)


def test_highlights_below_threshold_excluded():
    """±5%p 미만 변화는 highlights 제외."""
    gpt_response = json.dumps({
        "years_data": [
            {"year": 2024, "segments": [{"segment": "주력", "revenue_pct": 50}, {"segment": "보조", "revenue_pct": 50}]},
            {"year": 2025, "segments": [{"segment": "주력", "revenue_pct": 52}, {"segment": "보조", "revenue_pct": 48}]},
        ]
    })
    with patch("stock.advisory_fetcher.OPENAI_API_KEY", "sk-test"), \
         patch("stock.cache.get_cached", return_value=None), \
         patch("stock.cache.set_cached"), \
         patch("services.ai_gateway.call_openai_chat", return_value=_mock_chat_response(gpt_response)):
        result = advisory_fetcher.fetch_segments_history_kr("005930", "삼성전자", years=2)
    assert result["highlights"]["growing"] == []
    assert result["highlights"]["shrinking"] == []


def test_invalid_year_entry_skipped():
    """year가 숫자 변환 불가능하면 해당 entry skip — 다른 정상 entry는 보존."""
    gpt_response = json.dumps({
        "years_data": [
            {"year": "abc", "segments": [{"segment": "x", "revenue_pct": 100}]},
            {"year": 2025, "segments": [{"segment": "y", "revenue_pct": 100}]},
        ]
    })
    with patch("stock.advisory_fetcher.OPENAI_API_KEY", "sk-test"), \
         patch("stock.cache.get_cached", return_value=None), \
         patch("stock.cache.set_cached"), \
         patch("services.ai_gateway.call_openai_chat", return_value=_mock_chat_response(gpt_response)):
        result = advisory_fetcher.fetch_segments_history_kr("005930", "삼성전자", years=5)
    assert len(result["years_data"]) == 1
    assert result["years_data"][0]["year"] == 2025
