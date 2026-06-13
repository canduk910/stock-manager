"""지표 6 — AI IPO 추적.

화이트리스트 종목(config.AI_IPO_TICKERS)에 대해:
- 현재가 (yfinance) + IPO 공모가 (semi_thresholds 수동 시드) → 수익률
- SEC EDGAR full-text search 에서 락업 해제일 추출

값 메타:
- value = 수익률 % (티커별 1 row → indicator_name = "ai_ipo:{ticker}")
- value_meta: ticker / current_price / ipo_price / lockup_release_date / dminus_days
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import requests

from config import AI_IPO_TICKERS, SEC_EDGAR_USER_AGENT_CONTACT
from db.session import get_session
from db.repositories.semiconductor_repo import SemiconductorRepository
from stock.semi_collectors.base import CollectorResult, apply_outlier_guard

logger = logging.getLogger(__name__)

_KST = timezone(timedelta(hours=9))

# 락업 키워드: "180-day lock-up", "180 day lockup"
_LOCKUP_PATTERN = re.compile(r"(\d{2,3})[\s-]day\s+lock[\s-]?up", re.IGNORECASE)


def _today_kst_date() -> str:
    return datetime.now(_KST).strftime("%Y-%m-%d")


def _parse_ticker_list(raw: str) -> list[str]:
    tickers = [t.strip().upper() for t in (raw or "").split(",")]
    return [t for t in tickers if t]


def _fetch_current_price(ticker: str) -> Optional[float]:
    """yfinance 의존 분리. 테스트에서 mock 주입."""
    try:
        from stock.yf_client import fetch_price_yf
        return fetch_price_yf(ticker)
    except Exception as exc:
        logger.warning(f"[ai_ipo] {ticker} yfinance 조회 실패: {exc}")
        return None


def _fetch_lockup_release(ticker: str, cik: Optional[str] = None) -> Optional[str]:
    """SEC EDGAR full-text search 에서 락업 일수 검색.

    Returns:
        해제일 ISO YYYY-MM-DD or None.
    """
    try:
        params = {
            "q": f'"{ticker}" lock-up',
            "forms": "S-1,424B4",
        }
        headers = {
            "User-Agent": f"stock-manager/1.0 (contact={SEC_EDGAR_USER_AGENT_CONTACT})"
        }
        resp = requests.get(
            "https://efts.sec.gov/LATEST/search-index",
            params=params,
            headers=headers,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])
        for hit in hits[:5]:
            src = hit.get("_source", {})
            file_date = src.get("file_date") or ""
            # 본문 미포함 응답 — display_names 우선 후 file_date 파싱
            display = " ".join(src.get("display_names", []) or [])
            text = " ".join([display, src.get("description", "") or ""])
            m = _LOCKUP_PATTERN.search(text)
            if not m or not file_date:
                continue
            days = int(m.group(1))
            try:
                filed = date.fromisoformat(file_date)
            except ValueError:
                continue
            release = filed + timedelta(days=days)
            return release.isoformat()
        return None
    except Exception as exc:
        logger.warning(f"[ai_ipo] {ticker} SEC 락업 검색 실패: {exc}")
        return None


def _get_ipo_price(ticker: str) -> Optional[float]:
    try:
        with get_session() as db:
            repo = SemiconductorRepository(db)
            val = repo.get_threshold_value("ai_ipo", f"{ticker}/ipo_price", default=None)
        if val is None:
            return None
        return float(val)
    except Exception as exc:
        logger.warning(f"[ai_ipo] {ticker} ipo_price 조회 실패: {exc}")
        return None


def _get_last_price(ticker: str) -> Optional[float]:
    try:
        with get_session() as db:
            repo = SemiconductorRepository(db)
            row = repo.get_latest_value(f"ai_ipo:{ticker}")
        if row is None:
            return None
        meta = row.get("value_meta") or {}
        return meta.get("current_price")
    except Exception as exc:
        logger.warning(f"[ai_ipo] {ticker} 직전가 조회 실패: {exc}")
        return None


def collect(
    *,
    price_fn=_fetch_current_price,
    lockup_fn=_fetch_lockup_release,
    ipo_price_fn=_get_ipo_price,
    last_price_fn=_get_last_price,
    tickers: Optional[list[str]] = None,
    observed_at: Optional[str] = None,
) -> list[CollectorResult]:
    """AI IPO 화이트리스트 종목별 수익률 + 락업 D-N.

    Args:
        price_fn:        ticker → current_price
        lockup_fn:       ticker → 락업 해제일 ISO 문자열 or None
        ipo_price_fn:    ticker → IPO 공모가 (semi_thresholds 수동 시드)
        last_price_fn:   ticker → 직전 관측가 (outlier guard 용)
        tickers:         None → config.AI_IPO_TICKERS 사용
        observed_at:     None → KST 오늘
    """
    if tickers is None:
        tickers = _parse_ticker_list(AI_IPO_TICKERS)
    if not tickers:
        return []
    if observed_at is None:
        observed_at = _today_kst_date()

    raw_at = datetime.now(_KST).isoformat(timespec="seconds")
    results: list[CollectorResult] = []

    today = date.fromisoformat(observed_at)

    for ticker in tickers:
        price = price_fn(ticker)
        if price is None:
            logger.info(f"[ai_ipo] {ticker} 현재가 None — skip")
            continue
        ipo = ipo_price_fn(ticker)
        if ipo is None or ipo <= 0:
            # 공모가 미시드 — 수익률 계산 불가, 락업만 조회
            return_pct = None
        else:
            return_pct = (price - ipo) / ipo * 100.0

        # outlier (±30%) — 첫 5거래일 우회 (관측치 < 5 시)
        last_price = last_price_fn(ticker)
        with get_session() as db:
            repo = SemiconductorRepository(db)
            history_count = len(repo.list_values(f"ai_ipo:{ticker}", limit=10))
        if history_count >= 5 and not apply_outlier_guard(price, last_price, pct=30):
            logger.warning(
                f"[ai_ipo] {ticker} 가격 outlier 격리 ({last_price} → {price})"
            )
            continue

        release_iso = lockup_fn(ticker)
        dminus = None
        if release_iso:
            try:
                release = date.fromisoformat(release_iso)
                dminus = (release - today).days
            except ValueError:
                release_iso = None

        results.append(
            CollectorResult(
                indicator_name=f"ai_ipo:{ticker}",
                observed_at=observed_at,
                value=return_pct,
                value_meta={
                    "unit": "pct",
                    "ticker": ticker,
                    "current_price": price,
                    "ipo_price": ipo,
                    "lockup_release_date": release_iso,
                    "dminus_days": dminus,
                },
                source="yfinance+sec_edgar",
                raw_at=raw_at,
            )
        )

    return results
