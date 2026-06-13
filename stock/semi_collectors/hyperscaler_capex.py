"""지표 2 — 하이퍼스케일러 capex (SEC EDGAR companyfacts XBRL).

MSFT / GOOGL / AMZN / META 4사 분기 PaymentsToAcquirePropertyPlantAndEquipment 합산.
FY 누적 → Q4 도출.
YoY = 분기 합산 / 4분기 전 - 1.

스케줄러: 매일 08:30 KST (분기 보고 도착 시 멱등 upsert).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

from config import SEC_EDGAR_USER_AGENT_CONTACT
from services.exceptions import ConfigError
from stock.semi_collectors.base import (
    CollectorResult,
    apply_outlier_guard,
    pct_change_or_none,
)

logger = logging.getLogger(__name__)

_KST = timezone(timedelta(hours=9))

# CIK 0-padded 10 digit
_HYPERSCALER_CIK = {
    "MSFT": "0000789019",
    "GOOGL": "0001652044",
    "AMZN": "0001018724",
    "META": "0001326801",
}

_CAPEX_TAG = "PaymentsToAcquirePropertyPlantAndEquipment"


def _user_agent() -> str:
    contact = SEC_EDGAR_USER_AGENT_CONTACT or ""
    if "@" not in contact:
        raise ConfigError(
            "SEC_EDGAR_USER_AGENT_CONTACT 가 이메일 형식이 아닙니다 — SEC 정책 위반 위험"
        )
    return f"stock-manager/1.0 (contact={contact})"


def _fetch_companyfacts(cik_padded: str) -> dict:
    """SEC EDGAR XBRL companyfacts JSON. 테스트에서 주입."""
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json"
    resp = requests.get(
        url,
        headers={"User-Agent": _user_agent(), "Accept": "application/json"},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def _quarterly_capex_from_facts(facts: dict) -> dict:
    """XBRL facts → `{quarter_end_iso: {fp, val}}`.

    XBRL fp 코드: Q1/Q2/Q3 + FY(누적 전체).
    FY 응답 = full year 누적이므로 Q1+Q2+Q3 차감으로 Q4 도출.

    Returns:
        {"2025-12-31": {"fp": "Q4", "val": 16_500_000_000}, ...}
    """
    try:
        units = facts["facts"]["us-gaap"][_CAPEX_TAG]["units"]
    except (KeyError, TypeError):
        return {}
    # USD 우선 (구버전 일부 회사는 USD-CD 등)
    usd_rows = units.get("USD") or []

    # form 별 dedup (10-Q, 10-K). 최신 filed 우선.
    # key: (fy, fp), value: 가장 최근 filed
    best: dict[tuple, dict] = {}
    for row in usd_rows:
        fp = row.get("fp")
        fy = row.get("fy")
        end = row.get("end")
        val = row.get("val")
        filed = row.get("filed", "")
        if fp not in ("Q1", "Q2", "Q3", "FY") or fy is None or end is None or val is None:
            continue
        key = (int(fy), fp)
        existing = best.get(key)
        if existing is None or filed > existing.get("filed", ""):
            best[key] = {"fy": int(fy), "fp": fp, "end": end, "val": float(val), "filed": filed}

    # 연도별 그룹화 → FY 에서 Q1+Q2+Q3 차감 → Q4 도출
    by_year: dict[int, dict] = defaultdict(dict)
    for (fy, fp), row in best.items():
        by_year[fy][fp] = row

    out: dict[str, dict] = {}
    for fy, quarters in by_year.items():
        for fp in ("Q1", "Q2", "Q3"):
            if fp in quarters:
                row = quarters[fp]
                out[row["end"]] = {"fp": fp, "val": row["val"], "fy": fy}
        if "FY" in quarters and {"Q1", "Q2", "Q3"}.issubset(quarters.keys()):
            fy_row = quarters["FY"]
            q4_val = fy_row["val"] - sum(quarters[q]["val"] for q in ("Q1", "Q2", "Q3"))
            if q4_val > 0:
                out[fy_row["end"]] = {"fp": "Q4", "val": q4_val, "fy": fy}
    return out


def _quarter_end_date(end_iso: str) -> str:
    """end_iso를 그대로 반환 (이미 ISO YYYY-MM-DD)."""
    return end_iso


def collect(
    *,
    observed_at: Optional[str] = None,
    fetch_fn=_fetch_companyfacts,
) -> list[CollectorResult]:
    """4사 분기 capex 합산 + YoY.

    Args:
        observed_at: 무시됨. SEC 응답의 quarter end 를 사용.
        fetch_fn:   테스트 주입 (ticker → companyfacts dict).

    Returns:
        CollectorResult 0..N 개 (각 분기 1개). 일반 cron 호출 시 가장 최근 분기 1개.
    """
    raw_at = datetime.now(_KST).isoformat(timespec="seconds")

    per_company: dict[str, dict[str, float]] = {}  # ticker → {end → val}
    for ticker, cik in _HYPERSCALER_CIK.items():
        try:
            facts = fetch_fn(cik)
        except Exception as exc:
            logger.warning(f"[hyperscaler_capex] {ticker} SEC fetch 실패: {exc}")
            continue
        per_company[ticker] = {k: v["val"] for k, v in _quarterly_capex_from_facts(facts).items()}

    if not per_company:
        return []

    # 4사 공통 분기 합산 — 한 회사라도 미보고 분기는 제외
    common_quarters = set.intersection(*[set(d.keys()) for d in per_company.values()])

    # ASC 정렬
    sorted_quarters = sorted(common_quarters)

    results: list[CollectorResult] = []
    quarter_sums: dict[str, float] = {}
    for q in sorted_quarters:
        total = sum(per_company[t].get(q, 0.0) for t in per_company)
        quarter_sums[q] = total

    # YoY 계산 + outlier 격리. 가장 최근 분기 + 직전 ≤7분기까지 결과 발행.
    sorted_keys = sorted(quarter_sums.keys())
    for idx, q_end in enumerate(sorted_keys):
        curr = quarter_sums[q_end]
        # YoY: 4분기 전 (인덱스 -4)
        prev_idx = idx - 4
        prev = quarter_sums[sorted_keys[prev_idx]] if prev_idx >= 0 else None
        yoy = pct_change_or_none(curr, prev)

        # outlier (prev 가 있을 때 ±30%)
        prev_qtr_val = quarter_sums[sorted_keys[idx - 1]] if idx > 0 else None
        if not apply_outlier_guard(curr, prev_qtr_val, pct=30):
            logger.warning(
                f"[hyperscaler_capex] {q_end} outlier 격리 ({prev_qtr_val} → {curr})"
            )
            continue

        results.append(
            CollectorResult(
                indicator_name="hyperscaler_capex",
                observed_at=q_end,
                value=curr,
                value_meta={
                    "unit": "USD",
                    "by_company": {t: per_company[t].get(q_end) for t in per_company},
                    "yoy_pct": yoy,
                    "quarter_end": q_end,
                },
                source="sec_edgar_companyfacts",
                raw_at=raw_at,
            )
        )

    return results
