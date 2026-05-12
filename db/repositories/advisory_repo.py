"""AdvisoryRepository — 1:1 mapping to stock/advisory_store.py functions."""

from typing import Optional

from sqlalchemy.orm import Session

from db.models.advisory import (
    AdvisoryCache,
    AdvisoryReport,
    AdvisoryStock,
    PortfolioReport,
)
from db.utils import now_kst_iso


class AdvisoryRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Advisory Stocks CRUD ────────────────────────────────────

    def add_stock(self, user_id: int, code: str, market: str, name: str, memo: str = "") -> bool:
        code_u, market_u = code.upper(), market.upper()
        existing = (
            self.db.query(AdvisoryStock)
            .filter_by(user_id=user_id, code=code_u, market=market_u)
            .first()
        )
        if existing:
            return False
        self.db.add(AdvisoryStock(
            user_id=user_id,
            code=code_u,
            market=market_u,
            name=name,
            added_date=now_kst_iso(),
            memo=memo,
        ))
        return True

    def remove_stock(self, user_id: int, code: str, market: str) -> bool:
        count = (
            self.db.query(AdvisoryStock)
            .filter_by(user_id=user_id, code=code.upper(), market=market.upper())
            .delete()
        )
        return count > 0

    def all_stocks(self, user_id: int) -> list[dict]:
        rows = (
            self.db.query(AdvisoryStock)
            .filter_by(user_id=user_id)
            .order_by(AdvisoryStock.added_date.desc())
            .all()
        )
        return [r.to_dict() for r in rows]

    def get_stock(self, user_id: int, code: str, market: str) -> Optional[dict]:
        row = (
            self.db.query(AdvisoryStock)
            .filter_by(user_id=user_id, code=code.upper(), market=market.upper())
            .first()
        )
        return row.to_dict() if row else None

    # ── Cache CRUD (공유 캐시: 2026-05-12) ────────────────────────
    # PK = (code, market). user_id 파라미터는 시그니처 호환 유지를 위해 받지만 lookup/upsert에서 무시.
    # 최초 저장 시 user_id는 호출자 값으로 기록(audit 용도), 이후 갱신 시 덮어쓰지 않음.

    def save_cache(self, user_id: int, code: str, market: str, fundamental: dict, technical: dict,
                   strategy_signals: dict = None, research_data: dict = None) -> None:
        code_u, market_u = code.upper(), market.upper()
        row = (
            self.db.query(AdvisoryCache)
            .filter_by(code=code_u, market=market_u)
            .first()
        )
        if not row:
            row = AdvisoryCache(user_id=user_id, code=code_u, market=market_u)
            self.db.add(row)
        row.updated_at = now_kst_iso()
        row.fundamental = fundamental
        row.technical = technical
        if hasattr(row, 'strategy_signals'):
            row.strategy_signals = strategy_signals
        if hasattr(row, 'research_data') and research_data is not None:
            row.research_data = research_data

    def save_research_data(self, user_id: int, code: str, market: str,
                           research_data: dict) -> None:
        """리서치 데이터만 별도 저장 (기존 fundamental/technical 유지). 공유 캐시."""
        code_u, market_u = code.upper(), market.upper()
        row = (
            self.db.query(AdvisoryCache)
            .filter_by(code=code_u, market=market_u)
            .first()
        )
        if not row:
            row = AdvisoryCache(user_id=user_id, code=code_u, market=market_u,
                                updated_at=now_kst_iso(),
                                fundamental={}, technical={})
            self.db.add(row)
        row.research_data = research_data

    def get_cache(self, user_id: int, code: str, market: str) -> Optional[dict]:
        """공유 캐시 조회 — user_id 파라미터는 시그니처 호환 유지(무시)."""
        row = (
            self.db.query(AdvisoryCache)
            .filter_by(code=code.upper(), market=market.upper())
            .first()
        )
        return row.to_dict() if row else None

    # ── Report CRUD ─────────────────────────────────────────────

    def save_report(
        self,
        user_id: int,
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
        r = AdvisoryReport(
            user_id=user_id,
            code=code.upper(),
            market=market.upper(),
            generated_at=now_kst_iso(),
            model=model,
            report=report,
            grade=grade,
            grade_score=grade_score,
            composite_score=composite_score,
            regime_alignment=regime_alignment,
            schema_version=schema_version,
            value_trap_warning=value_trap_warning,
        )
        self.db.add(r)
        self.db.flush()
        return r.id

    def get_report_history(self, user_id: int, code: str, market: str, limit: int = 20) -> list[dict]:
        rows = (
            self.db.query(AdvisoryReport)
            .filter_by(user_id=user_id, code=code.upper(), market=market.upper())
            .order_by(AdvisoryReport.id.desc())
            .limit(limit)
            .all()
        )
        return [r.to_summary_dict() for r in rows]

    def get_report_by_id(self, report_id: int, user_id: Optional[int] = None) -> Optional[dict]:
        query = self.db.query(AdvisoryReport).filter_by(id=report_id)
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        row = query.first()
        return row.to_dict() if row else None

    def get_latest_report(self, user_id: int, code: str, market: str) -> Optional[dict]:
        row = (
            self.db.query(AdvisoryReport)
            .filter_by(user_id=user_id, code=code.upper(), market=market.upper())
            .order_by(AdvisoryReport.id.desc())
            .first()
        )
        return row.to_dict() if row else None

    # ── Portfolio Report CRUD ───────────────────────────────────
    # 2026-05-12: user_id 격리 추가. user_id=None은 백워드 호환 (마이그레이션 전 호출).

    def save_portfolio_report(
        self,
        model: str,
        report: dict,
        weighted_grade_avg: float | None = None,
        regime: str | None = None,
        schema_version: str = "v1",
        user_id: int | None = None,
    ) -> int:
        r = PortfolioReport(
            user_id=user_id,
            generated_at=now_kst_iso(),
            model=model,
            report=report,
            weighted_grade_avg=weighted_grade_avg,
            regime=regime,
            schema_version=schema_version,
        )
        self.db.add(r)
        self.db.flush()
        return r.id

    def get_portfolio_report_history(
        self, limit: int = 20, user_id: int | None = None,
    ) -> list[dict]:
        """포트폴리오 자문 이력. user_id 지정 시 본인 보고서만 반환."""
        query = self.db.query(PortfolioReport)
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        rows = query.order_by(PortfolioReport.id.desc()).limit(limit).all()
        return [r.to_summary_dict() for r in rows]

    def get_portfolio_report_by_id(
        self, report_id: int, user_id: int | None = None,
    ) -> Optional[dict]:
        """ID로 포트폴리오 자문 조회. user_id 지정 시 본인 보고서만 반환(권한 검증)."""
        query = self.db.query(PortfolioReport).filter_by(id=report_id)
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        row = query.first()
        return row.to_dict() if row else None

    def get_latest_portfolio_report(self, user_id: int | None = None) -> Optional[dict]:
        query = self.db.query(PortfolioReport)
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        row = query.order_by(PortfolioReport.id.desc()).first()
        return row.to_dict() if row else None
