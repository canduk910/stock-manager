"""종목 검색 API — KR 자동완성 / US 티커 검증."""

import re
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
def search_stocks(
    q: str = Query("", description="검색어 (종목명, 코드, 티커)"),
    market: str = Query("KR", description="시장 구분: KR | US"),
):
    """
    KR: 종목명/코드 부분 검색 → 최대 10건 자동완성 목록
    US: 티커 유효성 검증 → 유효하면 [단일 항목], 무효면 []
    """
    q = q.strip()

    if market == "KR":
        if not q:
            return []

        from stock import symbol_map

        # 6자리 숫자 코드 직접 입력
        if re.match(r"^\d{6}$", q):
            result = symbol_map.resolve(q)
            if result:
                code, name = result
                mkt = symbol_map.code_to_market(code) or "KRX"
                return [{"code": code, "name": name, "market": mkt}]
            return []

        # 2글자 미만은 검색 안 함
        if len(q) < 2:
            return []

        results = symbol_map.name_to_results(q)
        return [
            {"code": c, "name": n, "market": m}
            for c, n, m in results[:10]
        ]

    if market == "US":
        if not q:
            return []

        from stock.yf_client import validate_ticker
        info = validate_ticker(q.upper())
        if info:
            return [{"code": q.upper(), "name": info["name"], "market": info.get("exchange", "US")}]
        return []

    return []
