"""관심종목 목록 CRUD — SQLAlchemy ORM adapter.

기존 함수 시그니처에 user_id 파라미터 추가. 내부는 WatchlistRepository에 위임.
"""

from typing import Optional

from db.repositories.watchlist_repo import WatchlistRepository
from db.session import get_session


def all_items(user_id: int) -> list[dict]:
    with get_session() as db:
        return WatchlistRepository(db).all_items(user_id)


def get_item(user_id: int, code: str, market: str = "KR") -> Optional[dict]:
    with get_session() as db:
        return WatchlistRepository(db).get_item(user_id, code, market)


def add_item(user_id: int, code: str, name: str, memo: str = "", market: str = "KR") -> bool:
    """이미 존재하면 False, 새로 추가하면 True."""
    with get_session() as db:
        return WatchlistRepository(db).add_item(user_id, code, name, memo, market)


def remove_item(user_id: int, code: str, market: str = "KR") -> bool:
    with get_session() as db:
        return WatchlistRepository(db).remove_item(user_id, code, market)


def update_memo(user_id: int, code: str, memo: str, market: str = "KR") -> bool:
    with get_session() as db:
        return WatchlistRepository(db).update_memo(user_id, code, memo, market)


# ── 종목 순서 관리 ──────────────────────────────────────────────────────────────

def get_order(user_id: int) -> list[dict]:
    """순서 테이블 조회 (position ASC)."""
    with get_session() as db:
        return WatchlistRepository(db).get_order(user_id)


def save_order(user_id: int, items: list[dict]) -> None:
    """순서 전체 교체. items: [{code, market}, ...] — 인덱스가 position."""
    with get_session() as db:
        WatchlistRepository(db).save_order(user_id, items)
