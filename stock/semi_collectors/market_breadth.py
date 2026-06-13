"""지표 8 — KOSPI 시장폭 ADR + 삼성/SK 시총 집중도.

당일 1회 호출 (스케줄러 평일 16:00):
- pykrx로 당일 KOSPI 전종목 등락 → 일별 up/down count 저장
- ORM 시계열에서 직전 19일치 + 당일 합산 → ADR(20)
- 삼성+SK하이닉스 시총 / KOSPI 전체 시총 → 집중도
- KOSPI 종가 252일 신고치 비교

2 개 row 생성:
- market_breadth_adr20  : value=ADR(20)
- market_breadth_concentration : value=집중도(0~1)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from db.session import get_session
from db.repositories.semiconductor_repo import SemiconductorRepository
from stock.semi_collectors.base import CollectorResult, apply_outlier_guard

logger = logging.getLogger(__name__)

_KST = timezone(timedelta(hours=9))

_SAMSUNG = "005930"
_HYNIX = "000660"


def _today_kst_date() -> str:
    return datetime.now(_KST).strftime("%Y-%m-%d")


def _to_yyyymmdd(date_str: str) -> str:
    return date_str.replace("-", "")


def _fetch_kospi_breadth(date_yyyymmdd: str) -> dict:
    """pykrx 의존 분리 — 테스트 mock 주입 가능.

    Returns:
        {
            "trading_date": "YYYY-MM-DD",
            "up_count": int,
            "down_count": int,
            "kospi_close": float,
            "samsung_mc": float,
            "hynix_mc": float,
            "kospi_total_mc": float,
        }
    """
    from pykrx import stock
    from screener.krx import _find_latest_trading_day

    actual = _find_latest_trading_day(date_yyyymmdd)
    # 시장별 OHLCV
    ohlcv_df = stock.get_market_ohlcv(actual, market="KOSPI")
    if ohlcv_df is None or ohlcv_df.empty:
        raise RuntimeError(f"pykrx KOSPI OHLCV 빈 응답: {actual}")
    # 등락은 종가 변화율 부호로 판정
    chg = ohlcv_df.get("등락률")
    if chg is None:
        raise RuntimeError("pykrx OHLCV 응답에 '등락률' 컬럼 없음")
    up_count = int((chg > 0).sum())
    down_count = int((chg < 0).sum())

    # KOSPI 지수 종가
    kospi_idx = stock.get_index_ohlcv(actual, actual, "1001")  # 코스피 지수 종합
    kospi_close = float(kospi_idx["종가"].iloc[-1]) if (kospi_idx is not None and not kospi_idx.empty) else None

    # 시총
    cap_df = stock.get_market_cap(actual, market="KOSPI")
    if cap_df is None or cap_df.empty:
        raise RuntimeError(f"pykrx KOSPI 시총 빈 응답: {actual}")
    kospi_total_mc = float(cap_df["시가총액"].sum())
    samsung_mc = float(cap_df["시가총액"].loc[_SAMSUNG]) if _SAMSUNG in cap_df.index else 0.0
    hynix_mc = float(cap_df["시가총액"].loc[_HYNIX]) if _HYNIX in cap_df.index else 0.0

    return {
        "trading_date": f"{actual[:4]}-{actual[4:6]}-{actual[6:8]}",
        "up_count": up_count,
        "down_count": down_count,
        "kospi_close": kospi_close,
        "samsung_mc": samsung_mc,
        "hynix_mc": hynix_mc,
        "kospi_total_mc": kospi_total_mc,
    }


def collect(
    *,
    observed_at: Optional[str] = None,
    fetch_fn=_fetch_kospi_breadth,
) -> list[CollectorResult]:
    """KOSPI 시장폭 ADR(20) + 집중도.

    Args:
        observed_at: YYYY-MM-DD. None → KST 오늘.
        fetch_fn: 테스트 주입용 pykrx 호출 함수.

    Returns:
        2개 CollectorResult — market_breadth_adr20, market_breadth_concentration.
    """
    if observed_at is None:
        observed_at = _today_kst_date()

    snapshot = fetch_fn(_to_yyyymmdd(observed_at))
    # snapshot.trading_date 는 실제 거래일 (소급될 수 있음)
    actual_date = snapshot["trading_date"]
    up = snapshot["up_count"]
    down = snapshot["down_count"]
    kospi_close = snapshot["kospi_close"]
    samsung_mc = snapshot["samsung_mc"]
    hynix_mc = snapshot["hynix_mc"]
    kospi_total_mc = snapshot["kospi_total_mc"]

    # 직전 19개 + 당일 → 20일 합산
    with get_session() as db:
        repo = SemiconductorRepository(db)
        prev_adr_history = repo.list_values("market_breadth_adr20", limit=200, order="asc")
        prev_conc_history = repo.list_values(
            "market_breadth_concentration", limit=252, order="asc"
        )

    # 직전 19일 up/down 누적 (meta 에 저장된 값 활용)
    up_sum = up
    down_sum = down
    for r in prev_adr_history[-19:]:
        meta = r.get("value_meta") or {}
        up_sum += int(meta.get("up_count", 0) or 0)
        down_sum += int(meta.get("down_count", 0) or 0)

    adr20 = (up_sum / down_sum) if down_sum > 0 else None

    # KOSPI 252일 신고가 여부
    closes = [
        (r.get("value_meta") or {}).get("kospi_close")
        for r in prev_adr_history[-251:]
    ]
    closes = [c for c in closes if isinstance(c, (int, float))]
    kospi_252d_high = max([kospi_close, *closes]) if kospi_close is not None and closes else kospi_close
    is_kospi_252d_high = (
        kospi_close is not None
        and kospi_252d_high is not None
        and abs(kospi_close - kospi_252d_high) < 1e-6
    )

    # 집중도
    concentration = (
        (samsung_mc + hynix_mc) / kospi_total_mc if kospi_total_mc > 0 else None
    )

    # 집중도 252일 신고치
    prev_conc_values = [
        r["value"] for r in prev_conc_history[-251:] if isinstance(r.get("value"), (int, float))
    ]
    is_conc_252d_high = (
        concentration is not None
        and (not prev_conc_values or concentration > max(prev_conc_values))
    )

    # 집중도 sanity (±30%)
    last_conc = prev_conc_values[-1] if prev_conc_values else None
    if not apply_outlier_guard(concentration, last_conc, pct=30):
        logger.warning(
            f"[market_breadth] 집중도 outlier 격리: {last_conc} → {concentration}"
        )
        # 집중도만 폐기 (ADR은 유지). meta에 격리 사유 기록.
        outlier_conc = concentration
        concentration = None
    else:
        outlier_conc = None

    raw_at = datetime.now(_KST).isoformat(timespec="seconds")

    return [
        CollectorResult(
            indicator_name="market_breadth_adr20",
            observed_at=actual_date,
            value=adr20,
            value_meta={
                "unit": "ratio",
                "up_count": up,
                "down_count": down,
                "up_20d_sum": up_sum,
                "down_20d_sum": down_sum,
                "kospi_close": kospi_close,
                "kospi_252d_high": kospi_252d_high,
                "is_kospi_252d_high": bool(is_kospi_252d_high),
            },
            source="pykrx",
            raw_at=raw_at,
        ),
        CollectorResult(
            indicator_name="market_breadth_concentration",
            observed_at=actual_date,
            value=concentration,
            value_meta={
                "unit": "ratio",
                "samsung_mc": samsung_mc,
                "hynix_mc": hynix_mc,
                "kospi_total_mc": kospi_total_mc,
                "is_252d_high": bool(is_conc_252d_high) if concentration is not None else False,
                "outlier_excluded": outlier_conc,
            },
            source="pykrx",
            raw_at=raw_at,
        ),
    ]
