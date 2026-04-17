"""AI자문 종목 목록 + 캐시 + 리포트 + 포트폴리오 자문 CRUD — SQLAlchemy ORM adapter.

기존 함수 시그니처 100% 유지. 내부는 AdvisoryRepository에 위임.
services/, routers/ 변경 없음.
"""

from typing import Optional

from db.repositories.advisory_repo import AdvisoryRepository
from db.session import get_session


# ── 자문종목 CRUD ─────────────────────────────────────────────────────────────

def add_stock(code: str, market: str, name: str, memo: str = "") -> bool:
    """종목 추가. 이미 존재하면 False."""
    with get_session() as db:
        return AdvisoryRepository(db).add_stock(code, market, name, memo)


def remove_stock(code: str, market: str) -> bool:
    """종목 삭제. 삭제된 행이 있으면 True."""
    with get_session() as db:
        return AdvisoryRepository(db).remove_stock(code, market)


def all_stocks() -> list[dict]:
    """전체 자문종목 목록 (added_date 역순)."""
    with get_session() as db:
        return AdvisoryRepository(db).all_stocks()


def get_stock(code: str, market: str) -> Optional[dict]:
    """단일 종목 조회."""
    with get_session() as db:
        return AdvisoryRepository(db).get_stock(code, market)


# ── 캐시 CRUD ─────────────────────────────────────────────────────────────────

def save_cache(code: str, market: str, fundamental: dict, technical: dict) -> None:
    """분석 데이터 캐시 저장 (upsert)."""
    with get_session() as db:
        AdvisoryRepository(db).save_cache(code, market, fundamental, technical)


def get_cache(code: str, market: str) -> Optional[dict]:
    """캐시 조회. 없으면 None."""
    with get_session() as db:
        return AdvisoryRepository(db).get_cache(code, market)


# ── 리포트 CRUD ───────────────────────────────────────────────────────────────

def save_report(
    code: str,
    market: str,
    model: str,
    report: dict,
    grade: str | None = None,
    grade_score: int | None = None,
    composite_score: float | None = None,
    regime_alignment: float | None = None,
    schema_version: str = "v1",
    value_trap_warning: bool = False,
) -> int:
    """AI 리포트 저장. 생성된 ID 반환."""
    with get_session() as db:
        return AdvisoryRepository(db).save_report(
            code, market, model, report,
            grade=grade, grade_score=grade_score,
            composite_score=composite_score, regime_alignment=regime_alignment,
            schema_version=schema_version, value_trap_warning=value_trap_warning,
        )


def get_report_history(code: str, market: str, limit: int = 20) -> list[dict]:
    """AI 리포트 히스토리 목록 (최신순, 본문 제외)."""
    with get_session() as db:
        return AdvisoryRepository(db).get_report_history(code, market, limit)


def get_report_by_id(report_id: int) -> Optional[dict]:
    """특정 ID의 AI 리포트 조회."""
    with get_session() as db:
        return AdvisoryRepository(db).get_report_by_id(report_id)


def get_latest_report(code: str, market: str) -> Optional[dict]:
    """최신 AI 리포트 조회."""
    with get_session() as db:
        return AdvisoryRepository(db).get_latest_report(code, market)


# ── 포트폴리오 자문 리포트 CRUD ──────────────────────────────────────────────

def save_portfolio_report(
    model: str,
    report: dict,
    weighted_grade_avg: float | None = None,
    regime: str | None = None,
    schema_version: str = "v1",
) -> int:
    """포트폴리오 자문 리포트 저장. 생성된 ID 반환."""
    with get_session() as db:
        return AdvisoryRepository(db).save_portfolio_report(
            model, report,
            weighted_grade_avg=weighted_grade_avg, regime=regime,
            schema_version=schema_version,
        )


def get_portfolio_report_history(limit: int = 20) -> list[dict]:
    """포트폴리오 자문 이력 목록 (최신순, 본문 제외)."""
    with get_session() as db:
        return AdvisoryRepository(db).get_portfolio_report_history(limit)


def get_portfolio_report_by_id(report_id: int) -> Optional[dict]:
    """특정 ID의 포트폴리오 자문 리포트 조회."""
    with get_session() as db:
        return AdvisoryRepository(db).get_portfolio_report_by_id(report_id)


def get_latest_portfolio_report() -> Optional[dict]:
    """최신 포트폴리오 자문 리포트 조회."""
    with get_session() as db:
        return AdvisoryRepository(db).get_latest_portfolio_report()
