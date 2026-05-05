"""매크로 GPT 결과 일일 캐시 — SQLAlchemy ORM adapter.

기존 함수 시그니처 100% 유지. 내부는 MacroRepository에 위임.
services/, routers/ 변경 없음.

당일(KST) 이미 GPT 결과가 있으면 재호출하지 않는다.
카테고리 예: 'nyt_translation', 'investor:Warren Buffett'
"""
from __future__ import annotations

from typing import Optional

from db.repositories.macro_repo import MacroRepository
from db.session import get_session


def get_today(category: str) -> Optional[any]:
    """당일(KST) GPT 결과 조회. 없으면 None."""
    with get_session() as db:
        return MacroRepository(db).get_today(category)


def save_today(category: str, result) -> None:
    """당일(KST) GPT 결과 저장 (upsert)."""
    with get_session() as db:
        MacroRepository(db).save_today(category, result)


def cleanup_old(days: int = 30) -> int:
    """N일 이전 캐시 삭제. 삭제 건수 반환."""
    with get_session() as db:
        return MacroRepository(db).cleanup_old(days)


def delete_today(category: str) -> int:
    """오늘자 캐시 강제 삭제 (외부 키 갱신/장애 복구용)."""
    with get_session() as db:
        return MacroRepository(db).delete_today(category)
