"""시세판 별도 등록 종목 CRUD — SQLAlchemy ORM adapter.

user_id 파라미터 추가. 내부는 MarketBoardRepository에 위임.
"""

from db.repositories.market_board_repo import MarketBoardRepository
from db.session import get_session


def all_items(user_id: int) -> list[dict]:
    with get_session() as db:
        return MarketBoardRepository(db).all_items(user_id)


def add_item(user_id: int, code: str, name: str, market: str = "KR") -> bool:
    """추가. 중복이면 False 반환."""
    with get_session() as db:
        return MarketBoardRepository(db).add_item(user_id, code, name, market)


def remove_item(user_id: int, code: str, market: str = "KR") -> bool:
    """삭제. 해당 항목이 없으면 False 반환."""
    with get_session() as db:
        return MarketBoardRepository(db).remove_item(user_id, code, market)


# ── 종목 순서 관리 ──────────────────────────────────────────────────────────────

def get_order(user_id: int) -> list[dict]:
    """순서 테이블 조회 (position ASC)."""
    with get_session() as db:
        return MarketBoardRepository(db).get_order(user_id)


def save_order(user_id: int, items: list[dict]) -> None:
    """순서 전체 교체. items: [{code, market}, ...] — 인덱스가 position."""
    with get_session() as db:
        MarketBoardRepository(db).save_order(user_id, items)
