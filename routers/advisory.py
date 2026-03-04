"""AI자문 API 라우터.

자문종목 CRUD + 데이터 새로고침 + AI 리포트 생성.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from services import advisory_service
from stock import advisory_store
from stock.utils import is_domestic

router = APIRouter(prefix="/api/advisory", tags=["advisory"])


# ── 요청 바디 ─────────────────────────────────────────────────────────────────

class AddStockBody(BaseModel):
    code: str
    market: str = "KR"
    memo: str = ""


# ── 엔드포인트 ────────────────────────────────────────────────────────────────

@router.get("")
def list_stocks():
    """자문종목 목록 (캐시 updated_at 포함)."""
    stocks = advisory_store.all_stocks()
    result = []
    for s in stocks:
        cache = advisory_store.get_cache(s["code"], s["market"])
        result.append({
            **s,
            "updated_at": cache["updated_at"] if cache else None,
            "has_report": advisory_store.get_latest_report(s["code"], s["market"]) is not None,
        })
    return result


@router.post("")
def add_stock(body: AddStockBody):
    """자문종목 추가."""
    code = body.code.strip().upper()
    market = body.market.upper()

    # 종목명 조회
    name = _resolve_name(code, market)

    ok = advisory_store.add_stock(code, market, name, body.memo)
    if not ok:
        raise HTTPException(status_code=409, detail="이미 등록된 종목입니다.")
    return advisory_store.get_stock(code, market)


@router.delete("/{code}")
def remove_stock(code: str, market: str = Query("KR")):
    """자문종목 삭제."""
    ok = advisory_store.remove_stock(code.upper(), market.upper())
    if not ok:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다.")
    return {"ok": True}


@router.post("/{code}/refresh")
def refresh_data(code: str, market: str = Query("KR")):
    """데이터 새로고침 (30초+ 소요). 기본적/기술적 분석 전체 수집."""
    code = code.upper()
    market = market.upper()

    stock = advisory_store.get_stock(code, market)
    if not stock:
        raise HTTPException(status_code=404, detail="자문종목 목록에 없는 종목입니다.")

    result = advisory_service.refresh_stock_data(code, market, stock["name"])
    return result


@router.get("/{code}/data")
def get_data(code: str, market: str = Query("KR")):
    """캐시된 분석 데이터 조회."""
    cache = advisory_store.get_cache(code.upper(), market.upper())
    if not cache:
        raise HTTPException(status_code=404, detail="데이터 없음. 새로고침을 먼저 해주세요.")
    return cache


@router.post("/{code}/analyze")
def analyze(code: str, market: str = Query("KR")):
    """OpenAI GPT-4o 리포트 생성 (10~30초 소요).

    OPENAI_API_KEY 미설정 시 503 반환.
    캐시 없을 시 404 반환.
    """
    code = code.upper()
    market = market.upper()

    stock = advisory_store.get_stock(code, market)
    name = stock["name"] if stock else code

    result = advisory_service.generate_ai_report(code, market, name)
    return result


@router.get("/{code}/report")
def get_report(code: str, market: str = Query("KR")):
    """최신 AI 리포트 조회."""
    report = advisory_store.get_latest_report(code.upper(), market.upper())
    if not report:
        raise HTTPException(status_code=404, detail="생성된 리포트가 없습니다.")
    return report


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _resolve_name(code: str, market: str) -> str:
    """종목코드 → 종목명 조회."""
    try:
        if market == "KR":
            from stock.symbol_map import code_to_name
            name = code_to_name(code)
            return name or code
        else:
            from stock.yf_client import validate_ticker
            info = validate_ticker(code)
            return info["name"] if info else code
    except Exception:
        return code
