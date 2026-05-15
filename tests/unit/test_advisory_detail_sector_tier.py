"""REQ-SECTOR-03 — 서비스 응답에 sector_tier 통과 검증.

도메인 결정 §D-7: dart_fin에서 sector_tier를 부착하면 services는 그대로 통과.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest


class TestAdvisorySectorTierPassthrough:
    """advisory_service: fundamental 응답에 sector_tier 노출."""

    def test_extract_sector_tier_from_income_stmt(self):
        from services.advisory_service import _extract_sector_tier_from_fundamental
        income_stmt = [
            {"year": 2024, "revenue": 100, "sector_tier": "bank_holding"},
            {"year": 2023, "revenue": 90, "sector_tier": "bank_holding"},
        ]
        bs_cf = {"balance_sheet": [], "cashflow": []}
        assert _extract_sector_tier_from_fundamental(income_stmt, bs_cf) == "bank_holding"

    def test_extract_sector_tier_from_bs_cf_dict(self):
        from services.advisory_service import _extract_sector_tier_from_fundamental
        # income_stmt에 sector_tier 없으면 bs_cf dict 최상위 검사
        income_stmt = [{"year": 2024}]
        bs_cf = {"balance_sheet": [], "cashflow": [], "sector_tier": "insurance"}
        assert _extract_sector_tier_from_fundamental(income_stmt, bs_cf) == "insurance"

    def test_extract_sector_tier_general_default(self):
        from services.advisory_service import _extract_sector_tier_from_fundamental
        # 둘 다 sector_tier 없음 → "general" 보수적 기본값
        assert _extract_sector_tier_from_fundamental([], {}) == "general"
        assert _extract_sector_tier_from_fundamental(None, None) == "general"
        # row가 dict 아닐 때도 graceful
        assert _extract_sector_tier_from_fundamental([None, "string"], None) == "general"

    def test_extract_sector_tier_prefers_income_over_bs(self):
        """income_stmt 우선 — 첫 매칭 행에서 즉시 결정."""
        from services.advisory_service import _extract_sector_tier_from_fundamental
        income_stmt = [{"year": 2024, "sector_tier": "bank_holding"}]
        bs_cf = {"sector_tier": "general"}  # 다른 값 (이론상 불가능하지만 가드)
        assert _extract_sector_tier_from_fundamental(income_stmt, bs_cf) == "bank_holding"


class TestDetailServiceSectorTier:
    """detail_service: get_financials 응답에 sector_tier 노출."""

    def test_get_financials_kr_includes_sector_tier_bank_holding(self):
        """REQ-SECTOR-03: KR 금융지주 → sector_tier='bank_holding' 응답 노출."""
        from services.detail_service import DetailService

        # fetch_financials_multi_year가 sector_tier="bank_holding" 행을 반환한다고 mock
        mock_rows = [
            {"year": 2023, "revenue": 25000000000000, "operating_income": 4200000000000,
             "net_income": 3000000000000, "rcept_no": "20240315000123",
             "dart_url": "https://dart.fss.or.kr/...", "sector_tier": "bank_holding"},
            {"year": 2024, "revenue": 28330000000000, "operating_income": 4850000000000,
             "net_income": 3770000000000, "rcept_no": "20250317000456",
             "dart_url": "https://dart.fss.or.kr/...", "sector_tier": "bank_holding"},
        ]
        with patch("services.detail_service.fetch_financials_multi_year", return_value=mock_rows):
            svc = DetailService()
            result = svc._get_financials_kr("086790", years=2)

        assert result.get("sector_tier") == "bank_holding"
        assert len(result["rows"]) == 2

    def test_get_financials_kr_general_when_dart_returns_general(self):
        """REQ-SECTOR-03 회귀: 일반 제조업은 sector_tier='general'."""
        from services.detail_service import DetailService

        mock_rows = [
            {"year": 2024, "revenue": 300000000000000, "operating_income": 30000000000000,
             "net_income": 25000000000000, "rcept_no": "20250317000789",
             "dart_url": "", "sector_tier": "general"},
        ]
        with patch("services.detail_service.fetch_financials_multi_year", return_value=mock_rows):
            svc = DetailService()
            result = svc._get_financials_kr("005930", years=1)

        assert result.get("sector_tier") == "general"

    def test_get_financials_kr_default_general_when_no_sector_tier(self):
        """legacy 캐시 호환: sector_tier 키 부재 시 'general'."""
        from services.detail_service import DetailService

        mock_rows = [
            {"year": 2024, "revenue": 100, "operating_income": 10, "net_income": 5,
             "rcept_no": "", "dart_url": ""},
        ]
        with patch("services.detail_service.fetch_financials_multi_year", return_value=mock_rows):
            svc = DetailService()
            result = svc._get_financials_kr("999999", years=1)

        assert result.get("sector_tier") == "general"

    def test_get_financials_us_always_general(self):
        """REQ-SECTOR-03: US 종목은 sector_tier='general'."""
        from services import detail_service
        from services.detail_service import DetailService

        mock_rows = [
            {"year": 2024, "revenue": 100000000000, "operating_income": 20000000000,
             "net_income": 15000000000},
        ]
        with patch.object(detail_service.yf_client, "fetch_financials_multi_year_yf", return_value=mock_rows):
            svc = DetailService()
            result = svc._get_financials_us("AAPL", years=1)

        assert result.get("sector_tier") == "general"
