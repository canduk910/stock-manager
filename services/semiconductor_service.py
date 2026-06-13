"""반도체 사이클 모니터링 — 서비스 오케스트레이션.

책임:
- run_all_collectors() : 5종 수집기 try/except 격리 실행 + DB upsert
- evaluate_and_persist(): 시그널 평가 + 상태 변경 감지 + Signal insert
- get_dashboard()      : 카드 섹션용 통합 응답
- get_indicator_history(name, days)
- get_signals(...) / ack_signal(...)
- upsert_threshold(...)

예외 정책: HTTPException raise 금지. ServiceError 계열 사용.
"""

from __future__ import annotations

import logging
from typing import Optional

from config import AI_IPO_TICKERS
from db.session import get_session
from db.repositories.semiconductor_repo import SemiconductorRepository
from services import semiconductor_signals as sig
from services.exceptions import ConfigError, NotFoundError, ServiceError
from stock.semi_collectors import INDICATOR_LABELS
from stock.semi_collectors.base import CollectorResult

logger = logging.getLogger(__name__)

# 수집기 ID → indicator_name(s) 매핑
_COLLECTOR_INDICATOR_GROUPS = {
    "hyperscaler_capex": ["hyperscaler_capex"],
    "memory_inventory": ["memory_inventory"],
    "hbm_contracts": ["hbm_contracts"],
    "ai_ipo": [],  # 동적: ai_ipo:{TICKER}
    "market_breadth": ["market_breadth_adr20", "market_breadth_concentration"],
}


# ── Collector dispatch ────────────────────────────────────────


def _dispatch_collector(name: str) -> list[CollectorResult]:
    if name == "hyperscaler_capex":
        from stock.semi_collectors import hyperscaler_capex
        return hyperscaler_capex.collect()
    if name == "memory_inventory":
        from stock.semi_collectors import memory_inventory
        return memory_inventory.collect()
    if name == "hbm_contracts":
        from stock.semi_collectors import hbm_contracts
        return hbm_contracts.collect()
    if name == "ai_ipo":
        from stock.semi_collectors import ai_ipo_tracker
        return ai_ipo_tracker.collect()
    if name == "market_breadth":
        from stock.semi_collectors import market_breadth
        return market_breadth.collect()
    raise ServiceError(f"알 수 없는 수집기: {name}")


def _persist_results(results: list[CollectorResult]) -> int:
    """ORM upsert. 처리 row 수 반환."""
    if not results:
        return 0
    n = 0
    with get_session() as db:
        repo = SemiconductorRepository(db)
        for r in results:
            repo.upsert_indicator_value(
                indicator_name=r.indicator_name,
                observed_at=r.observed_at,
                value=r.value,
                value_meta=r.value_meta,
                source=r.source,
            )
            n += 1
    return n


def run_all_collectors() -> dict:
    """5종 수집기 try/except 격리.

    Returns:
        {
            "ran": [name, ...],
            "failures": {name: error_msg},
            "rows_persisted": int,
        }
    """
    ran: list[str] = []
    failures: dict[str, str] = {}
    rows_total = 0
    for name in ["hyperscaler_capex", "memory_inventory", "hbm_contracts", "ai_ipo", "market_breadth"]:
        try:
            results = _dispatch_collector(name)
            rows = _persist_results(results)
            rows_total += rows
            ran.append(name)
        except Exception as exc:
            failures[name] = str(exc)
            logger.error(f"[semiconductor] {name} 수집 실패: {exc}", exc_info=True)
    return {"ran": ran, "failures": failures, "rows_persisted": rows_total}


def run_collector(name: str) -> dict:
    """단일 수집기 강제 실행 (관리자 수동 트리거)."""
    try:
        results = _dispatch_collector(name)
        rows = _persist_results(results)
        return {"ran": name, "rows_persisted": rows}
    except Exception as exc:
        logger.error(f"[semiconductor] {name} 강제 실행 실패: {exc}", exc_info=True)
        raise ServiceError(f"{name} 수집 실패: {exc}")


# ── Signal evaluation ────────────────────────────────────────


def _ai_ipo_tickers() -> list[str]:
    return [t.strip().upper() for t in (AI_IPO_TICKERS or "").split(",") if t.strip()]


def evaluate_all(db_repo: Optional[SemiconductorRepository] = None) -> dict:
    """5종 + 종합 평가. dict 반환 (DB persist 없음).

    `evaluate_and_persist`는 본 함수 호출 후 상태 변경 시 Signal insert.
    """
    def _run_with(repo: SemiconductorRepository) -> dict:
        # capex
        capex_th = repo.thresholds_as_map("hyperscaler_capex")
        capex_h = repo.list_values("hyperscaler_capex", limit=12, order="asc")
        capex_eval = sig.evaluate_hyperscaler_capex(capex_th, capex_h)

        # memory_inventory
        inv_th = repo.thresholds_as_map("memory_inventory")
        inv_h = repo.list_values("memory_inventory", limit=8, order="asc")
        inv_eval = sig.evaluate_memory_inventory(inv_th, inv_h)

        # hbm_contracts (당일 1건)
        hbm_th = repo.thresholds_as_map("hbm_contracts")
        hbm_h = repo.list_values("hbm_contracts", limit=14, order="asc")
        hbm_eval = sig.evaluate_hbm_contracts(hbm_th, hbm_h)

        # ai_ipo (티커별)
        ipo_th = repo.thresholds_as_map("ai_ipo")
        ipo_per_ticker = {}
        for t in _ai_ipo_tickers():
            history = repo.list_values(f"ai_ipo:{t}", limit=30, order="asc")
            ipo_per_ticker[t] = {"history": history}
        ipo_eval = sig.evaluate_ai_ipo(ipo_th, ipo_per_ticker)

        # market_breadth
        mb_th = repo.thresholds_as_map("market_breadth")
        adr_h = repo.list_values("market_breadth_adr20", limit=252, order="asc")
        conc_h = repo.list_values("market_breadth_concentration", limit=252, order="asc")
        mb_eval = sig.evaluate_market_breadth(mb_th, adr_h, conc_h)

        per = {
            "hyperscaler_capex": capex_eval,
            "memory_inventory": inv_eval,
            "hbm_contracts": hbm_eval,
            "ai_ipo": ipo_eval,
            "market_breadth": mb_eval,
        }
        composite = sig.evaluate_composite(per)
        return {"per_indicator": per, "composite": composite}

    if db_repo is not None:
        return _run_with(db_repo)
    with get_session() as db:
        return _run_with(SemiconductorRepository(db))


def evaluate_and_persist() -> dict:
    """평가 + 상태 변경 시 Signal insert. dashboard 진입/스케줄러 단일 진입점."""
    with get_session() as db:
        repo = SemiconductorRepository(db)
        evaluation = evaluate_all(repo)
        per = evaluation["per_indicator"]
        composite = evaluation["composite"]

        signals_inserted: list[dict] = []

        # 개별 5종
        for name, eval_result in per.items():
            new_level = eval_result.get("level", "INFO")
            last = repo.get_last_signal(name)
            prev_level = (last or {}).get("level", "GREEN")
            if new_level != prev_level:
                msg = sig.format_indicator_message(name, prev_level, eval_result)
                snapshot = {
                    "recent_4": eval_result.get("recent_4", []),
                    "threshold": eval_result.get("threshold", {}),
                    "reason": eval_result.get("reason", ""),
                }
                sid = repo.insert_signal(
                    indicator_name=name,
                    level=new_level,
                    message=msg,
                    value_snapshot=snapshot,
                )
                signals_inserted.append(
                    {"id": sid, "indicator_name": name, "level": new_level, "message": msg}
                )

        # 종합
        new_composite_level = composite.get("level", "GREEN")
        last_composite = repo.get_last_signal("composite")
        prev_composite_level = (last_composite or {}).get("level", "GREEN")
        if new_composite_level != prev_composite_level:
            msg = sig.format_composite_message(prev_composite_level, composite)
            sid = repo.insert_signal(
                indicator_name="composite",
                level=new_composite_level,
                message=msg,
                value_snapshot={
                    "per_indicator_levels": composite.get("per_indicator_levels", {}),
                    "reason": composite.get("reason", ""),
                },
            )
            signals_inserted.append(
                {"id": sid, "indicator_name": "composite", "level": new_composite_level, "message": msg}
            )

    return {
        "per_indicator": {k: {kk: vv for kk, vv in (v or {}).items() if kk != "items"} for k, v in per.items()},
        "composite": composite,
        "signals_inserted": signals_inserted,
    }


# ── Dashboard ────────────────────────────────────────────────


def get_dashboard() -> dict:
    """카드 섹션용 통합 응답."""
    with get_session() as db:
        repo = SemiconductorRepository(db)
        evaluation = evaluate_all(repo)
        per = evaluation["per_indicator"]
        composite = evaluation["composite"]

        # 각 지표 last_signal 메타 부착
        indicators_out = {}
        for name, eval_result in per.items():
            last = repo.get_last_signal(name)
            indicators_out[name] = {
                "level": eval_result.get("level"),
                "label": eval_result.get("label"),
                "value": eval_result.get("value"),
                "threshold": eval_result.get("threshold"),
                "recent_4": eval_result.get("recent_4"),
                "reason": eval_result.get("reason"),
                "last_signal": last,
                # AI IPO 상세 / HBM items / market_breadth concentration 확장
                **({"details": eval_result.get("details")} if "details" in eval_result else {}),
                **({"items": eval_result.get("items")} if "items" in eval_result else {}),
                **(
                    {"concentration": eval_result.get("concentration"),
                     "concentration_meta": eval_result.get("concentration_meta"),
                     "is_kospi_252d_high": eval_result.get("is_kospi_252d_high")}
                    if name == "market_breadth"
                    else {}
                ),
            }

    return {
        "composite": composite,
        "indicators": indicators_out,
        "partial_failure": [],
        "labels": INDICATOR_LABELS,
    }


# ── History / Signals / Thresholds ───────────────────────────


def get_indicator_history(indicator_name: str, days: int = 180) -> dict:
    with get_session() as db:
        repo = SemiconductorRepository(db)
        rows = repo.list_values(indicator_name, limit=days, order="asc")
    return {"indicator_name": indicator_name, "points": rows}


def get_signals(
    indicator_name: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = 50,
) -> dict:
    with get_session() as db:
        repo = SemiconductorRepository(db)
        rows = repo.list_signals(
            indicator_name=indicator_name, since=since, until=until, limit=limit
        )
    return {"signals": rows, "count": len(rows)}


def ack_signal(signal_id: int, user_id: Optional[int] = None) -> bool:
    with get_session() as db:
        repo = SemiconductorRepository(db)
        ok = repo.ack_signal(signal_id, user_id=user_id)
    if not ok:
        raise NotFoundError(f"신호를 찾을 수 없습니다: {signal_id}")
    return True


def list_thresholds(indicator_name: Optional[str] = None) -> dict:
    with get_session() as db:
        repo = SemiconductorRepository(db)
        rows = repo.list_thresholds(indicator_name)
    return {"thresholds": rows}


def upsert_threshold(
    indicator_name: str,
    threshold_key: str,
    value,
    *,
    comment: Optional[str] = None,
    updated_by: Optional[int] = None,
) -> dict:
    with get_session() as db:
        repo = SemiconductorRepository(db)
        tid = repo.upsert_threshold(
            indicator_name=indicator_name,
            threshold_key=threshold_key,
            value=value,
            comment=comment,
            updated_by=updated_by,
        )
        row = repo.get_threshold(indicator_name, threshold_key)
    return {"id": tid, "threshold": row}
