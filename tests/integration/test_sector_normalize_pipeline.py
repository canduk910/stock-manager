"""REQ-TEST-002 + REQ-BACK-004 + REQ-BACK-005: 데이터 수집 진입점 정규화 통합 테스트.

yfinance/market 진입점에서 영문/혼합 sector raw가 한글 화이트리스트로 정규화되는지 검증.
캐시 키/TTL 동작 + 동일 종목의 다중 경로 일관성 검증.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest


# ──────────────────────────────────────────────────────────────────────
# REQ-BACK-004: 데이터 수집부 정규화 적용
# ──────────────────────────────────────────────────────────────────────

def test_yf_client_normalize_helper_kr_us_split():
    """yf_client._normalize_sector_for_code 헬퍼는 코드 형식으로 시장 자동 추론."""
    from stock.yf_client import _normalize_sector_for_code

    # US 알파벳 코드
    assert _normalize_sector_for_code("Technology", "AAPL") == "정보기술"
    assert _normalize_sector_for_code("Healthcare", "JNJ") == "헬스케어"
    # KR 6자리 숫자 코드 — 코드 직접 매핑 우선
    assert _normalize_sector_for_code("Technology", "005930") == "반도체"
    assert _normalize_sector_for_code("아무거나", "105560") == "은행/금융"
    # 폴백
    assert _normalize_sector_for_code(None, "ZZZ") == "기타"
    assert _normalize_sector_for_code("", "999999") == "기타"


def test_watchlist_norm_sector_helper():
    """watchlist_service._norm_sector idempotent + 시장 자동 추론."""
    from services.watchlist_service import _norm_sector

    # KR 자동 추론
    assert _norm_sector("Technology", "005930") == "반도체"
    # US 자동 추론
    assert _norm_sector("Technology", "AAPL") == "정보기술"
    # 명시 시장 우선
    assert _norm_sector("Energy", "AAPL", "US") == "에너지"
    # idempotent — 이미 한글 라벨 입력
    assert _norm_sector("반도체", "005930") == "반도체"
    # 한글 라벨이 raw로 들어와도 KR 시장 + 정규식 통과
    # ("반도체"는 정규식 매치)
    assert _norm_sector("반도체", "999999", "KR") == "반도체"
    # 빈 입력 → "기타"
    assert _norm_sector(None, "999999", "KR") == "기타"


# ──────────────────────────────────────────────────────────────────────
# 다중 경로 일관성: 동일 종목 → 동일 sector 라벨
# ──────────────────────────────────────────────────────────────────────

def test_normalize_same_code_same_label_across_markets():
    """동일 종목 코드는 어디서 호출해도 동일 라벨."""
    from stock.sector_normalize import normalize_sector

    # 005930 - 삼성전자: KR raw 다양해도 "반도체"
    assert normalize_sector("Technology", "KR", code="005930") == "반도체"
    assert normalize_sector("전기·전자", "KR", code="005930") == "반도체"
    assert normalize_sector(None, "KR", code="005930") == "반도체"


# ──────────────────────────────────────────────────────────────────────
# REQ-BACK-005: 캐시 키 + TTL
# ──────────────────────────────────────────────────────────────────────

def test_cache_key_pattern():
    """캐시 모듈에 정규화 결과 저장/조회 시 키 패턴 sector_norm:{market}:{code}."""
    from stock import sector_normalize as sn
    from stock import cache

    # cache 헬퍼 — 모듈에 노출되어야 함
    assert hasattr(sn, "normalize_sector_cached") or hasattr(sn, "cache_normalized_sector"), (
        "캐시 wrapper 함수 미노출"
    )

    # 캐시 키 빌더
    key = sn.cache_key("KR", "005930")
    assert key == "sector_norm:KR:005930"
    key2 = sn.cache_key("us", "aapl")  # 정규화: 대문자
    assert key2 == "sector_norm:US:AAPL"


def test_normalize_sector_cached_writes_and_reads():
    """normalize_sector_cached 캐시 hit/miss 동작."""
    from stock import sector_normalize as sn
    from stock import cache

    # 사전 정리
    cache.delete_cached(sn.cache_key("KR", "005930"))

    # 첫 호출 — miss → 저장
    label1 = sn.normalize_sector_cached("Technology", "KR", "005930")
    assert label1 == "반도체"

    # 캐시 검증 — value에 sector/raw/source/normalized_at 포함
    raw_cached = cache.get_cached(sn.cache_key("KR", "005930"))
    assert raw_cached is not None
    assert raw_cached.get("sector") == "반도체"
    assert "raw" in raw_cached
    assert "source" in raw_cached
    assert "normalized_at" in raw_cached

    # 두번째 호출 — hit (raw 무관)
    label2 = sn.normalize_sector_cached("아무거나", "KR", "005930")
    assert label2 == "반도체"

    # 정리
    cache.delete_cached(sn.cache_key("KR", "005930"))


def test_normalize_sector_pure_function_does_not_write_cache():
    """REQ-BACK-005: normalize_sector 자체는 순수 함수 — 캐시 비의존."""
    from stock import sector_normalize as sn
    from stock import cache

    code = "111111"  # 임의 코드 (KR_70에 없음)
    cache.delete_cached(sn.cache_key("KR", code))

    # 순수 함수 호출 — 캐시 쓰지 않아야
    sn.normalize_sector("화학", "KR", code=code)

    raw = cache.get_cached(sn.cache_key("KR", code))
    assert raw is None, "normalize_sector는 캐시를 쓰지 않아야 함"
