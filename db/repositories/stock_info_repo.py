"""StockInfoRepository — 1:1 mapping to stock/stock_info_store.py functions."""

import logging
from datetime import datetime, time, timedelta
from typing import Optional

from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from db.models.stock_info import StockInfo
from db.utils import KST, now_kst, now_kst_iso

logger = logging.getLogger(__name__)

# ── TTL policy (hours) ──────────────────────────────────────────────────────
_TTL = {
    "price":      {"trading": 0.167, "off": 12.0},
    "metrics":    {"trading": 6.0,   "off": 24.0},
    "financials": {"trading": 168.0, "off": 168.0},
    "returns":    {"trading": 0.5,   "off": 12.0},
}

# 영역명 → DB 컬럼명 매핑 (financials는 fin_updated_at 변형)
_FIELD_TO_COLUMN = {
    "price":      "price_updated_at",
    "metrics":    "metrics_updated_at",
    "financials": "fin_updated_at",
    "returns":    "returns_updated_at",
}


def _is_kr_trading_hours(now: Optional[datetime] = None) -> bool:
    if now is None:
        now = datetime.now(KST)
    elif now.tzinfo is None:
        # naive datetime은 KST로 간주
        now = now.replace(tzinfo=KST)
    return now.weekday() < 5 and time(9, 0) <= now.time() <= time(15, 30)


def is_stale_from_dict(
    info: Optional[dict],
    field: str,
    *,
    now: Optional[datetime] = None,
) -> bool:  # noqa: D401
    # T-3: N+1 회귀 감시 카운터 (호출 횟수만 누적, 본 로직 미터치)
    try:
        from services import _telemetry
        _telemetry.record_event(f"stock_info.is_stale_from_dict.{field}")
    except Exception:
        pass
    return _is_stale_from_dict_impl(info, field, now=now)


def _is_stale_from_dict_impl(
    info: Optional[dict],
    field: str,
    *,
    now: Optional[datetime] = None,
) -> bool:
    """순수 함수: dict + field만으로 stale 여부 판정 (DB 쿼리 없음).

    QW-1: 26종목 × 4 SELECT(get_stock_info × 1 + is_stale × 3 = 104) →
    fetch 1회 + dict 판정 3회 = 26 SELECT 로 N+1 제거.

    `is_stale(code, market, field)` 와 결과 동일성 보장 (TTL/거래시간 로직 동일).

    Args:
        info: stock_info 영속 캐시 dict (StockInfoRepository.get_stock_info 결과).
              None/빈 dict는 stale.
        field: "price" / "metrics" / "financials" / "returns".
        now: 트레이딩 시간 판정용 KST datetime (테스트 주입). None이면 datetime.now(KST).
    """
    if not info:
        return True

    col_name = _FIELD_TO_COLUMN.get(field, f"{field}_updated_at")
    updated_str = info.get(col_name)
    if not updated_str:
        return True

    try:
        updated = datetime.fromisoformat(updated_str).replace(tzinfo=None)
    except (ValueError, TypeError):
        return True

    cur = now if now is not None else now_kst()
    cur_naive = cur.replace(tzinfo=None) if cur.tzinfo else cur
    ttl_cfg = _TTL.get(field, {"trading": 1.0, "off": 6.0})
    ttl_h = ttl_cfg["trading"] if _is_kr_trading_hours(cur) else ttl_cfg["off"]
    return (cur_naive - updated) > timedelta(hours=ttl_h)


class StockInfoRepository:
    def __init__(self, db: Session):
        self.db = db

    def is_stale(self, code: str, market: str, field: str) -> bool:
        """Check if the given data region needs refresh.

        QW-1: 내부적으로 get_stock_info → is_stale_from_dict 위임 (단일 SELECT).
        시그니처 보존(후방 호환).
        """
        info = self.get_stock_info(code, market)
        return is_stale_from_dict(info, field)

    def get_stock_info(self, code: str, market: str = "KR") -> Optional[dict]:
        # T-3: N+1 회귀 감시 (단일 SELECT 호출 횟수)
        try:
            from services import _telemetry
            _telemetry.record_event("stock_info.get_stock_info")
        except Exception:
            pass
        row = (
            self.db.query(StockInfo)
            .filter_by(code=code, market=market)
            .first()
        )
        return row.to_dict() if row else None

    def batch_get(self, codes_markets: list[tuple]) -> dict:
        if not codes_markets:
            return {}
        conditions = [
            and_(StockInfo.code == code, StockInfo.market == market)
            for code, market in codes_markets
        ]
        rows = self.db.query(StockInfo).filter(or_(*conditions)).all()
        return {(r.code, r.market): r.to_dict() for r in rows}

    def _ensure_row(self, code: str, market: str) -> StockInfo:
        """Get or create a StockInfo row (check-then-insert, F2 pattern)."""
        row = (
            self.db.query(StockInfo)
            .filter_by(code=code, market=market)
            .first()
        )
        if not row:
            row = StockInfo(code=code, market=market)
            self.db.add(row)
            self.db.flush()
        return row

    def upsert_price(self, code: str, market: str, data: dict) -> None:
        try:
            row = self._ensure_row(code, market)
            row.price = data.get("close") or data.get("price")
            row.change_val = data.get("change") or data.get("change_val")
            row.change_pct = data.get("change_pct")
            row.mktcap = data.get("mktcap")
            row.shares = data.get("shares")
            row.price_updated_at = now_kst_iso()
        except Exception as e:
            logger.warning("stock_info upsert_price error: %s", e)

    def upsert_metrics(self, code: str, market: str, data: dict) -> None:
        try:
            row = self._ensure_row(code, market)
            row.per = data.get("per")
            row.pbr = data.get("pbr")
            row.roe = data.get("roe")
            row.dividend_yield = data.get("dividend_yield")
            row.dividend_per_share = data.get("dividend_per_share")
            row.market_type = data.get("market_type")
            row.sector = data.get("sector")
            row.high_52 = data.get("high_52")
            row.low_52 = data.get("low_52")
            row.metrics_updated_at = now_kst_iso()
        except Exception as e:
            logger.warning("stock_info upsert_metrics error: %s", e)

    def upsert_financials(self, code: str, market: str, data: dict) -> None:
        try:
            row = self._ensure_row(code, market)
            row.revenue = data.get("revenue")
            row.operating_income = data.get("operating_income")
            row.net_income = data.get("net_income")
            row.bsns_year = data.get("bsns_year")
            row.fin_updated_at = now_kst_iso()
        except Exception as e:
            logger.warning("stock_info upsert_financials error: %s", e)

    def upsert_returns(self, code: str, market: str, data: dict) -> None:
        try:
            row = self._ensure_row(code, market)
            row.return_3m = data.get("return_3m")
            row.return_6m = data.get("return_6m")
            row.return_1y = data.get("return_1y")
            row.returns_updated_at = now_kst_iso()
        except Exception as e:
            logger.warning("stock_info upsert_returns error: %s", e)
