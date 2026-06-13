"""지표 8 — 시장폭 수집기 테스트.

DB 세션을 in-memory SQLite로 재구성한 monkeypatch fixture가 필요.
"""

import pytest
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
import db.models  # noqa: F401
from stock.semi_collectors import market_breadth
from db.repositories.semiconductor_repo import SemiconductorRepository


@pytest.fixture
def mb_session(monkeypatch):
    """get_session() 패치 — collector 내부 세션이 in-memory를 사용하게."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    @contextmanager
    def fake_get_session():
        s = Session()
        try:
            yield s
            s.commit()
        finally:
            s.close()

    monkeypatch.setattr(market_breadth, "get_session", fake_get_session)
    yield Session
    Base.metadata.drop_all(engine)
    engine.dispose()


def _fixed_fetch(payload):
    def _fn(date_yyyymmdd):
        return payload
    return _fn


def test_adr_and_concentration_first_observation(mb_session):
    snap = {
        "trading_date": "2026-06-13",
        "up_count": 600,
        "down_count": 400,
        "kospi_close": 2700.0,
        "samsung_mc": 500_000_000_000_000,
        "hynix_mc": 200_000_000_000_000,
        "kospi_total_mc": 2_000_000_000_000_000,
    }
    results = market_breadth.collect(
        observed_at="2026-06-13", fetch_fn=_fixed_fetch(snap)
    )
    by_name = {r.indicator_name: r for r in results}

    adr = by_name["market_breadth_adr20"]
    # 첫 관측 — 당일만 합산 → 600/400 = 1.5
    assert adr.value == pytest.approx(1.5)
    assert adr.value_meta["up_20d_sum"] == 600
    assert adr.value_meta["down_20d_sum"] == 400

    conc = by_name["market_breadth_concentration"]
    # (500조 + 200조) / 2000조 = 0.35
    assert conc.value == pytest.approx(0.35)
    # 첫 관측이라 252일 신고치 = 본인
    assert conc.value_meta["is_252d_high"] is True


def test_adr_uses_prior_history(mb_session):
    Session = mb_session
    s = Session()
    repo = SemiconductorRepository(s)
    # 직전 5거래일 적재 — 각 100up/100down (합 500up/500down)
    for d in ["2026-06-06", "2026-06-09", "2026-06-10", "2026-06-11", "2026-06-12"]:
        repo.upsert_indicator_value(
            indicator_name="market_breadth_adr20",
            observed_at=d,
            value=1.0,
            value_meta={
                "unit": "ratio",
                "up_count": 100,
                "down_count": 100,
                "kospi_close": 2650.0,
            },
        )
    s.commit()
    s.close()

    snap = {
        "trading_date": "2026-06-13",
        "up_count": 200,
        "down_count": 300,  # 약세
        "kospi_close": 2700.0,  # 신고가 갱신
        "samsung_mc": 500_000_000_000_000,
        "hynix_mc": 200_000_000_000_000,
        "kospi_total_mc": 2_000_000_000_000_000,
    }
    results = market_breadth.collect(
        observed_at="2026-06-13", fetch_fn=_fixed_fetch(snap)
    )
    by_name = {r.indicator_name: r for r in results}
    adr = by_name["market_breadth_adr20"]
    # 누적: up = 200 + 500 = 700, down = 300 + 500 = 800
    assert adr.value_meta["up_20d_sum"] == 700
    assert adr.value_meta["down_20d_sum"] == 800
    assert adr.value == pytest.approx(700 / 800)
    # KOSPI 신고가
    assert adr.value_meta["is_kospi_252d_high"] is True


def test_concentration_outlier_guard(mb_session):
    Session = mb_session
    s = Session()
    repo = SemiconductorRepository(s)
    # 직전 집중도 = 0.35
    repo.upsert_indicator_value(
        indicator_name="market_breadth_concentration",
        observed_at="2026-06-12",
        value=0.35,
        value_meta={"unit": "ratio"},
    )
    s.commit()
    s.close()

    # 당일 집중도 갑자기 0.60 (+71%) → outlier 격리
    snap = {
        "trading_date": "2026-06-13",
        "up_count": 500,
        "down_count": 500,
        "kospi_close": 2700.0,
        "samsung_mc": 800_000_000_000_000,
        "hynix_mc": 400_000_000_000_000,
        "kospi_total_mc": 2_000_000_000_000_000,
    }
    results = market_breadth.collect(
        observed_at="2026-06-13", fetch_fn=_fixed_fetch(snap)
    )
    conc = next(r for r in results if r.indicator_name == "market_breadth_concentration")
    assert conc.value is None  # 격리됨
    assert conc.value_meta["outlier_excluded"] == pytest.approx(0.60)


def test_zero_down_handled_gracefully(mb_session):
    snap = {
        "trading_date": "2026-06-13",
        "up_count": 800,
        "down_count": 0,  # 전종목 상승
        "kospi_close": 2700.0,
        "samsung_mc": 500_000_000_000_000,
        "hynix_mc": 200_000_000_000_000,
        "kospi_total_mc": 2_000_000_000_000_000,
    }
    results = market_breadth.collect(
        observed_at="2026-06-13", fetch_fn=_fixed_fetch(snap)
    )
    adr = next(r for r in results if r.indicator_name == "market_breadth_adr20")
    assert adr.value is None  # divide-by-zero 가드
