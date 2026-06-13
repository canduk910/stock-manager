"""semi_collectors — 반도체 사이클 선행지표 수집기 (Phase 1, 5종).

각 수집기는 단순 함수 패턴(`collect()`)으로 `list[CollectorResult]`를 반환한다.
`COLLECTORS` 레지스트리로 ID(`indicator_name`) → callable 매핑.
"""

from __future__ import annotations

from .base import CollectorResult, apply_outlier_guard, pct_change_or_none

# 지연 import — 외부 의존(SEC/pykrx/yfinance) 로딩 비용 회피.
# services/semiconductor_service.py 에서 dispatch.

INDICATOR_LABELS = {
    "hyperscaler_capex": "하이퍼스케일러 캐펙스",
    "memory_inventory": "메모리 재고일수",
    "hbm_contracts": "HBM 공시",
    "ai_ipo": "AI IPO 추적",
    "market_breadth": "KOSPI 시장폭",
    "composite": "반도체 종합 신호",
}

# Phase 1 — 5개 지표 (collector function 이름 매핑).
# 실제 모듈 import는 service layer에서 한다.
COLLECTOR_REGISTRY = {
    "hyperscaler_capex": "stock.semi_collectors.hyperscaler_capex:collect",
    "memory_inventory": "stock.semi_collectors.memory_inventory:collect",
    "hbm_contracts": "stock.semi_collectors.hbm_contracts:collect",
    "ai_ipo": "stock.semi_collectors.ai_ipo_tracker:collect",
    "market_breadth": "stock.semi_collectors.market_breadth:collect",
}

__all__ = [
    "CollectorResult",
    "apply_outlier_guard",
    "pct_change_or_none",
    "INDICATOR_LABELS",
    "COLLECTOR_REGISTRY",
]
