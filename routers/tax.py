"""해외주식 양도소득세 API 라우터."""

from typing import List

from fastapi import APIRouter, Query
from pydantic import BaseModel

from services import tax_service

router = APIRouter(prefix="/api/tax", tags=["Tax"])


# ── Request 스키마 ────────────────────────────────────────────────────────────

class ManualTransactionRequest(BaseModel):
    symbol: str
    symbol_name: str = ""
    side: str  # buy | sell
    quantity: int
    price_foreign: float
    trade_date: str  # YYYY-MM-DD
    currency: str = "USD"
    commission: float = 0
    memo: str = ""


class SimulationItem(BaseModel):
    symbol: str
    quantity: int
    price_foreign: float
    currency: str = "USD"


class SimulationRequest(BaseModel):
    year: int
    simulations: List[SimulationItem]


# ── 엔드포인트 ────────────────────────────────────────────────────────────────

@router.get("/summary")
def get_summary(
    year: int = Query(..., description="조회 연도"),
):
    """연간 양도세 요약 (FIFO)."""
    return tax_service.get_annual_summary(year)


@router.get("/transactions")
def get_transactions(
    year: int = Query(..., description="조회 연도"),
    side: str = Query(None, description="매매구분 (buy|sell, 미지정 시 전체)"),
):
    """매매내역 목록 조회."""
    transactions = tax_service.get_transactions(year, side)
    return {"transactions": transactions, "count": len(transactions)}


@router.post("/transactions")
def add_transaction(req: ManualTransactionRequest):
    """매매내역 수동 추가."""
    tx = tax_service.add_manual_transaction(
        symbol=req.symbol,
        symbol_name=req.symbol_name,
        side=req.side,
        quantity=req.quantity,
        price_foreign=req.price_foreign,
        trade_date=req.trade_date,
        currency=req.currency,
        commission=req.commission,
        memo=req.memo,
    )
    return tx


@router.delete("/transactions/{tx_id}")
def remove_transaction(tx_id: int):
    """매매내역 삭제."""
    tax_service.delete_transaction(tx_id)
    return {"deleted": True}


@router.post("/sync")
def sync_transactions(
    year: int = Query(..., description="동기화 연도"),
):
    """KIS API 또는 로컬 DB에서 체결내역 동기화."""
    return tax_service.sync_transactions(year)


@router.post("/recalculate")
def recalculate(
    year: int = Query(..., description="재계산 연도"),
):
    """양도세 재계산 (FIFO)."""
    results = tax_service.calculate_tax(year)
    return {"calculations": results, "count": len(results)}


@router.get("/calculations")
def get_calculations(
    year: int = Query(..., description="조회 연도"),
    symbol: str = Query(None, description="종목코드 필터"),
):
    """계산 상세 결과 조회 (FIFO). lots 포함."""
    calculations = tax_service.get_calculations(year, symbol)
    return {"calculations": calculations, "count": len(calculations)}


@router.get("/simulate/holdings")
def get_simulation_holdings():
    """시뮬레이션용 현재 보유종목 목록."""
    return tax_service.get_simulation_holdings()


@router.post("/simulate")
def simulate_tax(req: SimulationRequest):
    """가상 매도 시뮬레이션 (DB 저장 없음)."""
    return tax_service.simulate_tax(
        year=req.year,
        simulations=[s.model_dump() for s in req.simulations],
    )
