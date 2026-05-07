"""4개 KR 전략 프리셋 메타데이터.

기존 MCP `list_presets()` 응답과 동일 키 사용 (`id`, `name`, `description`,
`category`, `tags`, `default_params`).
"""

from __future__ import annotations

from services.local_backtest.strategies import STRATEGY_REGISTRY


LOCAL_PRESETS = [
    {
        "id": "momentum",
        "name": "상한가 모멘텀",
        "description": (
            "전일 종가 대비 +29% 이상 상승하되 상한가에 도달하지 않은 종목을 "
            "당일 종가에 매수, 익일 시가에 청산. 손절 -7.5%."
        ),
        "category": "momentum",
        "tags": ["모멘텀", "단기", "추세추종"],
        "default_params": dict(STRATEGY_REGISTRY["momentum"]().default_params),
        "param_schema": {
            "rise_threshold": {"type": "number", "min": 0.10, "max": 0.50, "step": 0.01,
                               "default": 0.29, "label": "매수 상승률 임계값(소수)"},
            "limit_up_threshold": {"type": "number", "min": 0.20, "max": 0.40, "step": 0.01,
                                    "default": 0.30, "label": "상한가 임계값(소수)"},
            "stop_loss_pct": {"type": "number", "min": 0.85, "max": 0.99, "step": 0.005,
                               "default": 0.925, "label": "손절가 비율 (매수가 대비)"},
        },
    },
    {
        "id": "volatility_breakout",
        "name": "변동성 돌파 (래리 윌리엄스)",
        "description": (
            "당일 시가 + 전일Range × K20 평균노이즈를 돌파하면 진입, "
            "당일 종가 강제 청산. 손절 -3%."
        ),
        "category": "volatility",
        "tags": ["변동성돌파", "당일청산", "래리윌리엄스"],
        "default_params": dict(STRATEGY_REGISTRY["volatility_breakout"]().default_params),
        "param_schema": {
            "k_window": {"type": "integer", "min": 5, "max": 60, "step": 1,
                          "default": 20, "label": "K 평균 윈도우 (일)"},
            "stop_loss_pct": {"type": "number", "min": 0.85, "max": 0.99, "step": 0.005,
                               "default": 0.97, "label": "손절가 비율"},
        },
    },
    {
        "id": "donchian_swing",
        "name": "20일 신고가 스윙",
        "description": (
            "직전 20일 고가를 종가가 돌파하고 60일 EMA가 우상향 + 거래대금 1.5배 + "
            "갭 +3% 미만일 때 진입. 직전 20일 저가 이탈 시 매도. 손절 -7%."
        ),
        "category": "trend",
        "tags": ["돈치안", "스윙", "추세추종", "거래대금필터"],
        "default_params": dict(STRATEGY_REGISTRY["donchian_swing"]().default_params),
        "param_schema": {
            "channel_period": {"type": "integer", "min": 10, "max": 60, "step": 1,
                                "default": 20, "label": "채널 기간 (일)"},
            "ema_period": {"type": "integer", "min": 20, "max": 200, "step": 1,
                            "default": 60, "label": "EMA 기간 (일)"},
            "ema_change_window": {"type": "integer", "min": 1, "max": 20, "step": 1,
                                   "default": 5, "label": "EMA 변화율 측정 (일)"},
            "volume_factor": {"type": "number", "min": 1.0, "max": 5.0, "step": 0.1,
                               "default": 1.5, "label": "거래대금 배수"},
            "gap_max": {"type": "number", "min": 0.01, "max": 0.10, "step": 0.005,
                         "default": 0.03, "label": "허용 갭 한도(소수)"},
            "stop_loss_pct": {"type": "number", "min": 0.85, "max": 0.99, "step": 0.005,
                               "default": 0.93, "label": "손절가 비율"},
        },
    },
    {
        "id": "long_tail_volatility",
        "name": "롱테일 변동성",
        "description": (
            "변동성 돌파 진입 + 전일 대비 +3% 추가 필터. 당일 +29% 도달 시 익일 "
            "시가 매도, 그 외 당일 종가 매도. 손절 당일 -3% / 익일 -5%."
        ),
        "category": "volatility",
        "tags": ["변동성돌파", "롱테일", "스파이크"],
        "default_params": dict(STRATEGY_REGISTRY["long_tail_volatility"]().default_params),
        "param_schema": {
            "k_window": {"type": "integer", "min": 5, "max": 60, "step": 1,
                          "default": 20, "label": "K 평균 윈도우 (일)"},
            "rise_filter": {"type": "number", "min": 0.0, "max": 0.20, "step": 0.005,
                             "default": 0.03, "label": "전일 대비 종가 상승 필터(소수)"},
            "spike_threshold": {"type": "number", "min": 0.10, "max": 0.40, "step": 0.01,
                                 "default": 0.29, "label": "스파이크 임계값(소수)"},
            "stop_loss_same_day": {"type": "number", "min": 0.85, "max": 0.99, "step": 0.005,
                                    "default": 0.97, "label": "당일 손절가 비율"},
            "stop_loss_next_day": {"type": "number", "min": 0.85, "max": 0.99, "step": 0.005,
                                    "default": 0.95, "label": "익일 손절가 비율"},
        },
    },
]


def get_preset(preset_id: str) -> dict:
    """preset_id로 메타 dict 반환. 없으면 KeyError."""
    for p in LOCAL_PRESETS:
        if p["id"] == preset_id:
            return p
    raise KeyError(f"unknown local preset: {preset_id}")
