"""advisory_fetcher.fetch_segments_history_kr 회귀 테스트.

2026-05-10 변경 (사용자 결정 — AI API 사용 최소화):
- GPT fallback 제거. DART 단독 사용.
- Phase A GPT 추정 흐름 deprecated.
- 본 테스트는 새 동작(DART 단독) 회귀 가드.
"""

from unittest.mock import patch

import pytest

from stock import advisory_fetcher


@pytest.fixture(autouse=True)
def _clear_segments_cache():
    yield
    try:
        from stock.cache import delete_prefix
        delete_prefix("advisor:segments_history_kr:")
    except Exception:
        pass


def test_dart_failure_returns_empty_no_gpt():
    """DART 실패 시 빈 결과 + GPT 호출 0건 (fallback 제거)."""
    dart_empty = {
        "years_data": [], "highlights": {"growing": [], "shrinking": []},
        "confidence": "high", "source": "dart_parsed", "covered_years": 0,
    }
    with patch("stock.cache.get_cached", return_value=None), \
         patch("stock.cache.set_cached"), \
         patch("stock.dart_segments.fetch_segments_history_dart", return_value=dart_empty), \
         patch("stock.advisory_fetcher.OPENAI_API_KEY", "sk-test"), \
         patch("services.ai_gateway.call_openai_chat") as gpt_mock:
        result = advisory_fetcher.fetch_segments_history_kr("999999", "Unknown", years=5)
    assert result["years_data"] == []
    assert result["source"] == "dart_parsed"
    gpt_mock.assert_not_called()


def test_dart_success_returns_unchanged():
    """DART 성공 시 결과 그대로 + 캐시 7일."""
    dart_result = {
        "years_data": [
            {"year": 2024, "segments": [{"segment": "주력", "revenue_pct": 100, "raw_amount": None, "note": "DART실측"}]},
            {"year": 2025, "segments": [{"segment": "주력", "revenue_pct": 100, "raw_amount": None, "note": "DART실측"}]},
        ],
        "highlights": {"growing": [], "shrinking": []},
        "confidence": "high",
        "source": "dart_parsed",
        "covered_years": 2,
    }
    saved = []
    with patch("stock.cache.get_cached", return_value=None), \
         patch("stock.cache.set_cached", side_effect=lambda k, v, **kw: saved.append((k, v, kw))), \
         patch("stock.dart_segments.fetch_segments_history_dart", return_value=dart_result):
        result = advisory_fetcher.fetch_segments_history_kr("005930", "삼성전자", years=5)
    assert result == dart_result
    # 7일 TTL 캐시 (성공 시)
    assert any(kw.get("ttl_hours") == 24 * 7 for _, _, kw in saved)


def test_cache_hit_skips_dart():
    """캐시 hit 시 DART 호출 안 함."""
    cached = {
        "years_data": [{"year": 2024, "segments": [{"segment": "x", "revenue_pct": 100}]}],
        "highlights": {"growing": [], "shrinking": []},
        "confidence": "high", "source": "dart_parsed", "covered_years": 1,
    }
    with patch("stock.cache.get_cached", return_value=cached), \
         patch("stock.dart_segments.fetch_segments_history_dart") as dart_mock:
        result = advisory_fetcher.fetch_segments_history_kr("005830", "DB손해보험", years=5)
    assert result == cached
    dart_mock.assert_not_called()


def test_compute_segments_highlights_growing_shrinking():
    """첫·끝 ±5%p 임계 성장/축소 식별 헬퍼 (백워드 호환 — Phase A에서 사용)."""
    years_data = [
        {"year": 2021, "segments": [
            {"segment": "반도체", "revenue_pct": 50},
            {"segment": "스마트폰", "revenue_pct": 50},
        ]},
        {"year": 2025, "segments": [
            {"segment": "반도체", "revenue_pct": 70},
            {"segment": "스마트폰", "revenue_pct": 30},
        ]},
    ]
    h = advisory_fetcher._compute_segments_highlights(years_data)
    assert any(g["segment"] == "반도체" and g["delta_pct"] == 20.0 for g in h["growing"])
    assert any(s["segment"] == "스마트폰" and s["delta_pct"] == -20.0 for s in h["shrinking"])


def test_compute_segments_highlights_below_threshold():
    """±5%p 미만 변화는 highlights 제외."""
    years_data = [
        {"year": 2024, "segments": [{"segment": "A", "revenue_pct": 50}, {"segment": "B", "revenue_pct": 50}]},
        {"year": 2025, "segments": [{"segment": "A", "revenue_pct": 52}, {"segment": "B", "revenue_pct": 48}]},
    ]
    h = advisory_fetcher._compute_segments_highlights(years_data)
    assert h["growing"] == []
    assert h["shrinking"] == []


def test_compute_segments_highlights_empty_or_single_year():
    """1년치 또는 빈 데이터 → 빈 highlights."""
    assert advisory_fetcher._compute_segments_highlights([])["growing"] == []
    assert advisory_fetcher._compute_segments_highlights([
        {"year": 2025, "segments": [{"segment": "x", "revenue_pct": 100}]}
    ])["growing"] == []
