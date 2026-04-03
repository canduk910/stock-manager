"""AI자문 API 라우터.

자문종목 CRUD + 데이터 새로고침 + AI 리포트 생성.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from services import advisory_service
from services.exceptions import ServiceError, NotFoundError, ConflictError
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
    raw = body.code.strip()
    market = body.market.upper()

    # KR 종목: 종목명 입력 시 symbol_map으로 코드 변환
    if market == "KR":
        import re as _re
        if not _re.match(r"^\d{6}$", raw):
            # 6자리 코드가 아닌 경우 → 종목명으로 검색
            try:
                from stock.symbol_map import name_to_results
                results = name_to_results(raw)
                # 정확히 이름이 일치하는 항목 우선
                exact = [r for r in results if r[1] == raw]
                if len(exact) == 1:
                    code, name = exact[0][0], exact[0][1]
                elif len(results) == 1:
                    code, name = results[0][0], results[0][1]
                elif results:
                    candidates = ", ".join(f"{r[1]}({r[0]})" for r in results[:3])
                    raise ServiceError(
                        f"'{raw}' 검색 결과가 여러 개입니다: {candidates}. 6자리 종목코드로 입력해주세요.",
                    )
                else:
                    raise ServiceError(
                        f"'{raw}' 종목을 찾을 수 없습니다. 6자리 종목코드로 입력해주세요.",
                    )
            except ServiceError:
                raise
            except Exception:
                raise ServiceError(
                    f"'{raw}' 종목을 찾을 수 없습니다. 6자리 종목코드로 입력해주세요.",
                )
        else:
            code = raw
            name = _resolve_name(code, market)
    else:
        code = raw.upper()
        name = _resolve_name(code, market)

    ok = advisory_store.add_stock(code, market, name, body.memo)
    if not ok:
        raise ConflictError("이미 등록된 종목입니다.")
    return advisory_store.get_stock(code, market)


@router.delete("/{code}")
def remove_stock(code: str, market: str = Query("KR")):
    """자문종목 삭제."""
    ok = advisory_store.remove_stock(code.upper(), market.upper())
    if not ok:
        raise NotFoundError("종목을 찾을 수 없습니다.")
    return {"ok": True}


@router.post("/{code}/refresh")
def refresh_data(code: str, market: str = Query("KR"), name: str = Query(None)):
    """데이터 새로고침 (30초+ 소요). 기본적/기술적 분석 전체 수집.

    advisory_stocks 미등록 종목도 허용 (DetailPage에서 직접 호출 가능).
    name 파라미터로 종목명 전달 가능; 미등록 & name 없으면 code를 사용.
    """
    code = code.upper()
    market = market.upper()

    stock = advisory_store.get_stock(code, market)
    stock_name = stock["name"] if stock else (name or code)

    result = advisory_service.refresh_stock_data(code, market, stock_name)
    return result


@router.get("/{code}/data")
def get_data(code: str, market: str = Query("KR")):
    """캐시된 분석 데이터 조회."""
    cache = advisory_store.get_cache(code.upper(), market.upper())
    if not cache:
        raise NotFoundError("데이터 없음. 새로고침을 먼저 해주세요.")
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


@router.get("/{code}/ohlcv")
def get_ohlcv(
    code: str,
    market: str = Query("KR"),
    interval: str = Query("15m"),
    period: str = Query("60d"),
):
    """타임프레임/기간 지정 OHLCV + 기술지표 조회.

    interval: '15m' | '60m' | '1d' | '1wk'
    period: yfinance period 문자열
    """
    from stock.advisory_fetcher import fetch_ohlcv_by_interval
    result = fetch_ohlcv_by_interval(code.upper(), market.upper(), interval, period)
    return {**result, "interval": interval, "period": period}


@router.get("/{code}/reports")
def get_report_history(code: str, market: str = Query("KR"), limit: int = Query(20)):
    """AI 리포트 히스토리 목록 (최신순, 본문 제외)."""
    return advisory_store.get_report_history(code.upper(), market.upper(), limit)


@router.get("/{code}/reports/{report_id}")
def get_report_by_id(code: str, report_id: int, market: str = Query("KR")):
    """특정 ID의 AI 리포트 조회."""
    report = advisory_store.get_report_by_id(report_id)
    if not report or report["code"] != code.upper():
        raise NotFoundError("리포트를 찾을 수 없습니다.")
    return report


@router.get("/{code}/report")
def get_report(code: str, market: str = Query("KR")):
    """최신 AI 리포트 조회."""
    report = advisory_store.get_latest_report(code.upper(), market.upper())
    if not report:
        raise NotFoundError("생성된 리포트가 없습니다.")
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
