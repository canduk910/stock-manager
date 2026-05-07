"""전략 인터페이스 + 신호/포지션 데이터클래스."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import pandas as pd


@dataclass
class EntrySignal:
    """매수 신호 — 전략이 idx일에 진입하라고 결정했을 때 반환."""

    price: float  # 체결가
    reason: str = "entry"  # 디버깅/로그용


@dataclass
class ExitSignal:
    """매도 신호 — 전략이 idx일에 청산하라고 결정했을 때 반환."""

    price: float  # 체결가
    reason: str = "exit"  # next_open / close / stop_loss / channel_break / take_profit


@dataclass
class Position:
    """보유 포지션 (1종목 단위)."""

    symbol: str
    entry_date: date
    entry_price: float
    qty: int
    extra: dict = field(default_factory=dict)  # 전략별 메타(예: long_tail의 +29% 도달 여부)


class Strategy(ABC):
    """전략 추상 베이스.

    구현체는 다음을 정의:
      - id: 전략 ID 문자열
      - default_params: 룰 기본 파라미터
      - required_history_days(): 시그널 계산에 필요한 최소 과거 일수
      - check_entry(df, idx, params): idx일 매수 여부
      - check_exit(df, idx, position, params): idx일 청산 여부 (손절 우선)
    """

    id: str = ""
    default_params: dict = {}

    def required_history_days(self) -> int:
        return 1

    @abstractmethod
    def check_entry(
        self, df: pd.DataFrame, idx: int, params: dict
    ) -> Optional[EntrySignal]:
        """idx일 종가 시그널 평가."""

    @abstractmethod
    def check_exit(
        self, df: pd.DataFrame, idx: int, position: Position, params: dict
    ) -> Optional[ExitSignal]:
        """idx일 청산 평가. 손절가 도달 시 손절가 우선 체결."""
