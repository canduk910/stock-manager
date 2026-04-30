"""AnalystRepository — 증권사 리포트 메타데이터 + 시간축 추이 영속화.

REQ-ANALYST-06:
  - upsert_report(...) — 유니크 충돌 시 UPDATE (summary/target_price/opinion/fetched_at만 갱신)
  - list_reports(code, market, since=None, limit=20) — 최신순
  - get_target_price_history(code, market, days=180) — 시간축 조회 (REQ-05용)
  - published_at 미래/5년 이전 → fetched_at 날짜로 보정
"""

import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from db.models.analyst import AnalystReport
from db.utils import now_kst, now_kst_iso

logger = logging.getLogger(__name__)


def _today_iso() -> str:
    return date.today().isoformat()


def _normalize_published_at(published_at: str) -> str:
    """미래 날짜 또는 5년 이전 → 오늘 날짜로 대체 (네이버 파싱 오류 대응)."""
    if not published_at:
        return _today_iso()
    try:
        # YYYY-MM-DD or YY.MM.DD
        if len(published_at) == 8 and "." in published_at:
            # 26.04.28 → 2026-04-28
            yy, mm, dd = published_at.split(".")
            yyyy = 2000 + int(yy) if int(yy) < 70 else 1900 + int(yy)
            d = date(yyyy, int(mm), int(dd))
        else:
            d = date.fromisoformat(published_at[:10])
    except Exception:
        return _today_iso()

    today = date.today()
    if d > today:
        return today.isoformat()
    if (today - d).days > 365 * 5:
        return today.isoformat()
    return d.isoformat()


class AnalystRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── upsert ────────────────────────────────────────────────

    def upsert_report(
        self,
        code: str,
        market: str,
        broker: str,
        target_price: Optional[int],
        opinion: Optional[str],
        title: str,
        pdf_url: str,
        summary: str,
        published_at: str,
    ) -> bool:
        """동일 (code, market, broker, published_at, title) 행이 있으면 UPDATE,
        없으면 INSERT.

        Update 시 summary/target_price/opinion/fetched_at만 갱신, 나머지는 보존.
        """
        code_u, market_u = code.upper(), market.upper()
        pub = _normalize_published_at(published_at)
        title_n = (title or "").strip()
        broker_n = (broker or "").strip()

        existing = (
            self.db.query(AnalystReport)
            .filter_by(
                code=code_u, market=market_u, broker=broker_n,
                published_at=pub, title=title_n,
            )
            .first()
        )
        if existing:
            existing.summary = summary or ""
            existing.target_price = target_price
            existing.opinion = opinion
            existing.fetched_at = now_kst_iso()
            return True

        row = AnalystReport(
            code=code_u, market=market_u, broker=broker_n,
            target_price=target_price, opinion=opinion,
            title=title_n,
            pdf_url=pdf_url or "",
            summary=summary or "",
            published_at=pub,
            fetched_at=now_kst_iso(),
        )
        self.db.add(row)
        return True

    # ── 조회 ─────────────────────────────────────────────────

    def list_reports(
        self,
        code: str,
        market: str,
        since: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict]:
        """최신순(published_at desc) 조회."""
        code_u, market_u = code.upper(), market.upper()
        q = (
            self.db.query(AnalystReport)
            .filter_by(code=code_u, market=market_u)
        )
        if since:
            q = q.filter(AnalystReport.published_at >= since)
        rows = q.order_by(AnalystReport.published_at.desc()).limit(limit).all()
        return [r.to_dict() for r in rows]

    def get_target_price_history(
        self,
        code: str,
        market: str,
        days: int = 180,
    ) -> list[dict]:
        """REQ-ANALYST-05: 시간축 조회. days 윈도, 최신순.

        반환: [{broker, date, target_price, opinion}, ...]
        """
        code_u, market_u = code.upper(), market.upper()
        cutoff = (now_kst().date() - timedelta(days=days)).isoformat()
        rows = (
            self.db.query(AnalystReport)
            .filter_by(code=code_u, market=market_u)
            .filter(AnalystReport.published_at >= cutoff)
            .order_by(AnalystReport.published_at.desc())
            .all()
        )
        return [
            {
                "broker": r.broker,
                "date": r.published_at,
                "target_price": r.target_price,
                "opinion": r.opinion,
            }
            for r in rows
        ]
