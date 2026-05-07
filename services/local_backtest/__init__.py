"""local_backtest — 4개 KR 전략 + 균등 배분 포트폴리오 일봉 시뮬레이터.

외부 MCP 백테스트(`backtest_service.py`)와 별개로, stock-manager 내부에서
완결되는 일봉 단위 백테스트 엔진. KR market 전용(MVP).

공개 API:
  - run_local_backtest(): plan 단순화 룰 기반 4개 전략 실행
  - list_local_presets(): 4개 프리셋 메타데이터

도메인 룰: plan ai-sleepy-pancake.md 표 준수 (임의 변경 금지).
"""

from services.local_backtest.engine import simulate
from services.local_backtest.presets import LOCAL_PRESETS, get_preset

__all__ = ["simulate", "LOCAL_PRESETS", "get_preset"]
