"""지표 4 — 메모리 재고일수.

삼성전자(005930) / SK하이닉스(000660) 분기 재고일수 = 재고자산 / (매출원가 / 91).

DART 분기보고서:
- IS `매출원가` 누계 → 직전 분기 차감으로 분기 환산
- BS `재고자산` 당기말 (시점 값이므로 차감 안 함)

분기 ±30% outlier 격리.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from stock import dart_fin
from stock.semi_collectors.base import CollectorResult, apply_outlier_guard

logger = logging.getLogger(__name__)

_KST = timezone(timedelta(hours=9))

_MEMORY_TICKERS = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
}

# 분기보고 reprt_code 매핑 (dart_fin._QUARTERLY_REPRT_CODES 와 동일)
_QUARTERLY_REPRT_CODES = [
    ("11013", 1),  # Q1
    ("11012", 2),  # 반기
    ("11014", 3),  # 3분기
    ("11011", 4),  # 연간
]

_INVENTORY_RE = re.compile(r"^재고자산$")
_COGS_RE = re.compile(r"^매출원가$")


def _parse_amount(s) -> Optional[int]:
    return dart_fin._parse_amount(s)


def _extract_quarterly_bs_is(items: list[dict]) -> dict:
    """단일 분기 보고서 응답에서 BS 재고자산(시점) + IS 매출원가(누계) 추출."""
    inv = None
    cogs = None
    for it in items:
        sj = it.get("sj_div")
        nm = (it.get("account_nm") or "").strip()
        if sj == "BS" and inv is None and _INVENTORY_RE.match(nm):
            inv = _parse_amount(it.get("thstrm_amount"))
        elif sj in ("IS", "CIS") and cogs is None and _COGS_RE.match(nm):
            cogs = _parse_amount(it.get("thstrm_amount"))
    return {"inventory": inv, "cogs_accum": cogs}


def _fetch_quarterly_bs_is(stock_code: str) -> list[dict]:
    """[{year, quarter, inventory, cogs_quarter, period_end}] 오래된순.

    Returns most recent 8 quarters (2 years).
    """
    corp_code = dart_fin._fetch_corp_code(stock_code)
    if not corp_code:
        return []
    today = date.today()
    latest_year = today.year

    rows: list[dict] = []
    for year_offset in range(2):
        year = latest_year - year_offset
        accum: dict[int, dict] = {}
        fs_div_used = None
        for reprt_code, qnum in _QUARTERLY_REPRT_CODES:
            fs_divs = [fs_div_used] if fs_div_used else ["CFS", "OFS"]
            items: list = []
            for fs_div in fs_divs:
                candidate = dart_fin._call_fin_api_reprt(corp_code, year, reprt_code, fs_div)
                if candidate:
                    items = candidate
                    if fs_div_used is None:
                        fs_div_used = fs_div
                    break
            if items:
                accum[qnum] = _extract_quarterly_bs_is(items)

        if not accum:
            continue

        # 분기 환산 (IS COGS만)
        for q in range(1, 5):
            if q not in accum:
                continue
            cur = accum[q]
            prev = accum.get(q - 1) if q > 1 else None
            cogs_quarter = cur["cogs_accum"]
            if cogs_quarter is not None and prev and prev.get("cogs_accum") is not None:
                cogs_quarter = cur["cogs_accum"] - prev["cogs_accum"]
            # BS 재고자산은 시점값 — 차감 안 함
            period_end = _quarter_end_date(year, q)
            rows.append(
                {
                    "year": year,
                    "quarter": q,
                    "inventory": cur["inventory"],
                    "cogs_quarter": cogs_quarter,
                    "period_end": period_end,
                }
            )
    rows.sort(key=lambda r: (r["year"], r["quarter"]))
    return rows[-8:]  # 최근 8분기


def _quarter_end_date(year: int, q: int) -> str:
    return {
        1: f"{year}-03-31",
        2: f"{year}-06-30",
        3: f"{year}-09-30",
        4: f"{year}-12-31",
    }[q]


def _days_in_quarter(year: int, q: int) -> int:
    # 단순화: 모두 91일. dart_fin / 사이클 모두 91 사용.
    return 91


def collect(
    *,
    fetch_fn=_fetch_quarterly_bs_is,
) -> list[CollectorResult]:
    """메모리 2사 분기 재고일수 평균.

    Args:
        fetch_fn: (stock_code) → list[{year, quarter, inventory, cogs_quarter, period_end}]
    """
    raw_at = datetime.now(_KST).isoformat(timespec="seconds")

    # 회사별 row 수집
    per_company: dict[str, list[dict]] = {}
    for code in _MEMORY_TICKERS:
        try:
            rows = fetch_fn(code)
        except Exception as exc:
            logger.warning(f"[memory_inventory] {code} DART 조회 실패: {exc}")
            continue
        per_company[code] = rows

    if not per_company:
        return []

    # 공통 분기 (period_end) 추출
    common_periods = None
    for rows in per_company.values():
        periods = {r["period_end"] for r in rows}
        common_periods = periods if common_periods is None else common_periods & periods
    common_periods = sorted(common_periods or [])

    results: list[CollectorResult] = []
    prev_avg_days = None
    for period in common_periods:
        per_corp_data = {}
        avg_pool = []
        for code, rows in per_company.items():
            row = next((r for r in rows if r["period_end"] == period), None)
            if row is None:
                continue
            inv = row["inventory"]
            cogs_q = row["cogs_quarter"]
            days = None
            if inv is not None and cogs_q and cogs_q > 0:
                days = inv / (cogs_q / _days_in_quarter(row["year"], row["quarter"]))
            per_corp_data[code] = {
                "name": _MEMORY_TICKERS[code],
                "inventory": inv,
                "cogs_quarter": cogs_q,
                "days": days,
            }
            if days is not None:
                avg_pool.append(days)

        if not avg_pool:
            continue
        avg_days = sum(avg_pool) / len(avg_pool)

        if not apply_outlier_guard(avg_days, prev_avg_days, pct=30):
            logger.warning(
                f"[memory_inventory] {period} outlier 격리 "
                f"({prev_avg_days} → {avg_days})"
            )
            continue
        prev_avg_days = avg_days

        results.append(
            CollectorResult(
                indicator_name="memory_inventory",
                observed_at=period,
                value=avg_days,
                value_meta={
                    "unit": "days",
                    "by_company": per_corp_data,
                    "quarter": period,
                },
                source="dart_fin",
                raw_at=raw_at,
            )
        )

    return results
