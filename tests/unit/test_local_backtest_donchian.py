"""local_backtest.strategies.donchian_swing (20일 신고가 스윙) 단위 테스트.

룰:
  매수: 종가가 직전 20일 고가 돌파 + 60일 EMA 5일 변화율 ≥ 0
        + 거래대금 ≥ 20일 평균×1.5 + 갭 +3% 미만
  매수가: 당일 종가
  매도: 종가 ≤ 직전 20일 저가
  매도가: 당일 종가
  손절: 종가 ≤ 매수가×0.93
"""

from __future__ import annotations

import pandas as pd
import pytest


def _make_df(rows):
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()


def _flat_history(days: int, base: float = 100.0, vol: int = 1000):
    rows = []
    for i in range(days):
        d = pd.Timestamp("2024-01-01") + pd.Timedelta(days=i)
        rows.append((d.strftime("%Y-%m-%d"), base, base + 1, base - 1, base, vol))
    return rows


def _replace_last(rows, n_back: int, row):
    """마지막에서 n_back번째 행을 덮어쓰면서 그 행의 날짜는 보존."""
    idx = len(rows) - n_back
    orig_date = rows[idx][0]
    rows[idx] = (orig_date,) + tuple(row[1:])


def test_donchian_entry_breakout_20d_high_with_filters():
    """20일 신고가 돌파 + EMA 우상향 + 거래대금 1.5배 + 갭<3% → 매수."""
    from services.local_backtest.strategies import donchian_swing as ds

    # 60일 평탄 히스토리(EMA 일정), 마지막 봉이 20일 신고가 + 거래량 5배
    rows = _flat_history(70, base=100.0, vol=1000)
    # 60-day EMA가 정확히 평탄이 아닌 살짝 우상향이 되도록 마지막 5일 미세 상승.
    # _replace_last로 날짜 보존(원본 날짜를 그대로 두어 정렬 시 마지막에 위치).
    _replace_last(rows, 5, ("_", 100.5, 101.0, 100.0, 100.5, 1000))
    _replace_last(rows, 4, ("_", 100.8, 101.5, 100.0, 100.8, 1000))
    _replace_last(rows, 3, ("_", 101.0, 102.0, 100.5, 101.0, 1000))
    _replace_last(rows, 2, ("_", 101.2, 102.3, 100.8, 101.2, 1000))
    # 진입일: 시가 101.5 (전일종가 101.2 대비 +0.3% 갭<3%), 종가 105 → 직전 20일 고가(약 102.3) 돌파
    _replace_last(rows, 1, ("_", 101.5, 106.0, 101.0, 105.0, 6000))
    df = _make_df(rows)

    strat = ds.DonchianSwingStrategy()
    sig = strat.check_entry(df, idx=len(df) - 1, params=strat.default_params)
    assert sig is not None
    assert sig.price == pytest.approx(105.0)


def test_donchian_entry_skip_when_volume_low():
    """거래대금이 20일 평균×1.5 미만이면 매수 스킵."""
    from services.local_backtest.strategies import donchian_swing as ds

    rows = _flat_history(70, base=100.0, vol=1000)
    # 진입봉 거래량을 평균과 동일(1000) → 1.5배 필터 통과 못함
    rows[-1] = ("2024-02-29", 101.5, 106.0, 101.0, 105.0, 1000)
    df = _make_df(rows)

    strat = ds.DonchianSwingStrategy()
    sig = strat.check_entry(df, idx=len(df) - 1, params=strat.default_params)
    assert sig is None


def test_donchian_entry_skip_when_gap_too_large():
    """갭 +3% 이상이면 매수 스킵."""
    from services.local_backtest.strategies import donchian_swing as ds

    rows = _flat_history(70, base=100.0, vol=1000)
    rows[-2] = ("2024-02-28", 100.0, 101.0, 99.0, 100.0, 1000)
    # 갭 +5%: 시가 105 (전일종가 100 → +5%)
    rows[-1] = ("2024-02-29", 105.0, 110.0, 104.5, 109.0, 6000)
    df = _make_df(rows)

    strat = ds.DonchianSwingStrategy()
    sig = strat.check_entry(df, idx=len(df) - 1, params=strat.default_params)
    assert sig is None


def test_donchian_exit_close_below_20d_low():
    """종가 ≤ 직전 20일 저가 → 동가 매도."""
    from services.local_backtest.strategies import donchian_swing as ds
    from services.local_backtest.strategies._base import Position

    rows = _flat_history(70, base=100.0, vol=1000)
    # 진입일 종가는 무관, 매도 평가 시점만 보면 됨
    # 마지막 봉 종가 90 → 직전 20일 저가(99)보다 낮음 → 매도
    _replace_last(rows, 1, ("_", 95.0, 96.0, 89.0, 90.0, 1000))
    df = _make_df(rows)
    pos = Position(symbol="005930", entry_date=df.index[0].date(), entry_price=100.0, qty=10)

    strat = ds.DonchianSwingStrategy()
    sig = strat.check_exit(df, idx=len(df) - 1, position=pos, params=strat.default_params)
    assert sig is not None
    assert sig.price == pytest.approx(90.0)


def test_donchian_exit_stop_loss():
    """종가 ≤ 매수가×0.93 → 손절."""
    from services.local_backtest.strategies import donchian_swing as ds
    from services.local_backtest.strategies._base import Position

    rows = _flat_history(70, base=100.0, vol=1000)
    # 매수가 100, 손절가 93. 마지막 종가 92.5 → 손절.
    # 직전 20일 저가는 99이지만 92.5도 저가 이하이긴 함 — 여기선 손절가/저가 둘 다 만족.
    # 더 명확히 분리: 채널 저가는 그대로지만 손절가가 더 결정적
    _replace_last(rows, 1, ("_", 95.0, 95.0, 92.0, 92.5, 1000))
    df = _make_df(rows)
    pos = Position(symbol="005930", entry_date=df.index[0].date(), entry_price=100.0, qty=10)

    strat = ds.DonchianSwingStrategy()
    sig = strat.check_exit(df, idx=len(df) - 1, position=pos, params=strat.default_params)
    assert sig is not None
    # 둘 다 만족할 경우 stop_loss 우선이거나 채널이탈 우선이거나는 구현 선택
    # 종가 92.5 동가 매도 가정 → price는 92.5
    assert sig.price == pytest.approx(92.5)


def test_donchian_required_history_at_least_60():
    """60일 EMA를 위해 최소 60일 필요."""
    from services.local_backtest.strategies import donchian_swing as ds

    strat = ds.DonchianSwingStrategy()
    assert strat.required_history_days() >= 60
