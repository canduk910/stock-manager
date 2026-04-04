"""관심종목 목록 CRUD — SQLAlchemy ORM adapter.

기존 함수 시그니처 100% 유지. 내부는 WatchlistRepository에 위임.
services/, routers/ 변경 없음.
"""

from typing import Optional

from db.repositories.watchlist_repo import WatchlistRepository
from db.session import get_session


def all_items() -> list[dict]:
    with get_session() as db:
        return WatchlistRepository(db).all_items()


def get_item(code: str, market: str = "KR") -> Optional[dict]:
    with get_session() as db:
        return WatchlistRepository(db).get_item(code, market)


def add_item(code: str, name: str, memo: str = "", market: str = "KR") -> bool:
    """이미 존재하면 False, 새로 추가하면 True."""
    with get_session() as db:
        return WatchlistRepository(db).add_item(code, name, memo, market)


def remove_item(code: str, market: str = "KR") -> bool:
    with get_session() as db:
        return WatchlistRepository(db).remove_item(code, market)


def update_memo(code: str, memo: str, market: str = "KR") -> bool:
    with get_session() as db:
        return WatchlistRepository(db).update_memo(code, memo, market)


# ── 종목 순서 관리 ──────────────────────────────────────────────────────────────

def get_order() -> list[dict]:
    """순서 테이블 조회 (position ASC)."""
    with get_session() as db:
        return WatchlistRepository(db).get_order()


def save_order(items: list[dict]) -> None:
    """순서 전체 교체. items: [{code, market}, ...] — 인덱스가 position."""
    with get_session() as db:
        WatchlistRepository(db).save_order(items)
