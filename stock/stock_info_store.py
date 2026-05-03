"""종목 정보 영속 캐시 — SQLAlchemy ORM adapter.

기존 함수 시그니처 100% 유지. 내부는 StockInfoRepository에 위임.
services/, routers/ 변경 없음.

Docker 재시작에도 유지되는 종목별 시세/지표/재무/수익률 정보.
cache.db(TTL 캐시, 재시작 시 초기화)와 별도로 운용.
"""

from typing import Optional

from db.repositories.stock_info_repo import (
    StockInfoRepository,
    is_stale_from_dict as _is_stale_from_dict,
)
from db.session import get_session


def is_stale(code: str, market: str, field: str) -> bool:
    """해당 영역의 데이터가 갱신이 필요한지 판별."""
    with get_session() as db:
        return StockInfoRepository(db).is_stale(code, market, field)


def is_stale_from_dict(info, field: str) -> bool:
    """순수 함수 위임: dict + field만으로 stale 판정 (DB 쿼리 없음).

    QW-1: 대시보드 렌더링에서 동일 종목 4 SELECT → 1 SELECT 단축.
    """
    return _is_stale_from_dict(info, field)


def get_stock_info(code: str, market: str = "KR") -> Optional[dict]:
    """종목 정보 조회. 없으면 None."""
    with get_session() as db:
        return StockInfoRepository(db).get_stock_info(code, market)


def batch_get(codes_markets: list[tuple]) -> dict:
    """여러 종목 한 번에 조회. {(code, market): dict}."""
    with get_session() as db:
        return StockInfoRepository(db).batch_get(codes_markets)


def upsert_price(code: str, market: str, data: dict) -> None:
    """시세 영역 갱신."""
    with get_session() as db:
        StockInfoRepository(db).upsert_price(code, market, data)


def upsert_metrics(code: str, market: str, data: dict) -> None:
    """밸류에이션 지표 영역 갱신."""
    with get_session() as db:
        StockInfoRepository(db).upsert_metrics(code, market, data)


def upsert_financials(code: str, market: str, data: dict) -> None:
    """재무 영역 갱신."""
    with get_session() as db:
        StockInfoRepository(db).upsert_financials(code, market, data)


def upsert_returns(code: str, market: str, data: dict) -> None:
    """수익률 영역 갱신."""
    with get_session() as db:
        StockInfoRepository(db).upsert_returns(code, market, data)
