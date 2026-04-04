"""시세판 별도 등록 종목 CRUD — SQLAlchemy ORM adapter.

기존 함수 시그니처 100% 유지. 내부는 MarketBoardRepository에 위임.
services/, routers/ 변경 없음.
"""

from db.repositories.market_board_repo import MarketBoardRepository
from db.session import get_session


def all_items() -> list[dict]:
    with get_session() as db:
        return MarketBoardRepository(db).all_items()


def add_item(code: str, name: str, market: str = "KR") -> bool:
    """추가. 중복이면 False 반환."""
    with get_session() as db:
        return MarketBoardRepository(db).add_item(code, name, market)


def remove_item(code: str, market: str = "KR") -> bool:
    """삭제. 해당 항목이 없으면 False 반환."""
    with get_session() as db:
        return MarketBoardRepository(db).remove_item(code, market)


# ── 종목 순서 관리 ──────────────────────────────────────────────────────────────

def get_order() -> list[dict]:
    """순서 테이블 조회 (position ASC)."""
    with get_session() as db:
        return MarketBoardRepository(db).get_order()


def save_order(items: list[dict]) -> None:
    """순서 전체 교체. items: [{code, market}, ...] — 인덱스가 position."""
    with get_session() as db:
        MarketBoardRepository(db).save_order(items)
