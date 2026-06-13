"""지표 6 — AI IPO 수집기 테스트."""

import pytest
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
import db.models  # noqa: F401
from stock.semi_collectors import ai_ipo_tracker


@pytest.fixture
def ipo_session(monkeypatch):
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

    monkeypatch.setattr(ai_ipo_tracker, "get_session", fake_get_session)
    yield Session
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_no_tickers_returns_empty():
    results = ai_ipo_tracker.collect(
        tickers=[],
        price_fn=lambda t: 100.0,
        lockup_fn=lambda t: None,
        ipo_price_fn=lambda t: 50.0,
        last_price_fn=lambda t: None,
    )
    assert results == []


def test_basic_positive_return(ipo_session):
    results = ai_ipo_tracker.collect(
        tickers=["RDDT"],
        price_fn=lambda t: 75.0,
        lockup_fn=lambda t: None,
        ipo_price_fn=lambda t: 50.0,
        last_price_fn=lambda t: None,
        observed_at="2026-06-13",
    )
    assert len(results) == 1
    r = results[0]
    assert r.indicator_name == "ai_ipo:RDDT"
    assert r.value == pytest.approx(50.0)  # +50%
    assert r.value_meta["ticker"] == "RDDT"
    assert r.value_meta["current_price"] == 75.0
    assert r.value_meta["ipo_price"] == 50.0
    assert r.value_meta["lockup_release_date"] is None
    assert r.value_meta["dminus_days"] is None


def test_negative_return_no_ipo_price_yields_none_value(ipo_session):
    results = ai_ipo_tracker.collect(
        tickers=["ARM"],
        price_fn=lambda t: 30.0,
        lockup_fn=lambda t: None,
        ipo_price_fn=lambda t: None,  # 미시드
        last_price_fn=lambda t: None,
        observed_at="2026-06-13",
    )
    assert results[0].value is None
    assert results[0].value_meta["current_price"] == 30.0
    assert results[0].value_meta["ipo_price"] is None


def test_lockup_dminus(ipo_session):
    results = ai_ipo_tracker.collect(
        tickers=["RDDT"],
        price_fn=lambda t: 100.0,
        lockup_fn=lambda t: "2026-06-20",  # D-7
        ipo_price_fn=lambda t: 50.0,
        last_price_fn=lambda t: None,
        observed_at="2026-06-13",
    )
    r = results[0]
    assert r.value_meta["lockup_release_date"] == "2026-06-20"
    assert r.value_meta["dminus_days"] == 7


def test_lockup_pattern_matches():
    pat = ai_ipo_tracker._LOCKUP_PATTERN
    assert pat.search("180-day lock-up").group(1) == "180"
    assert pat.search("180 day lockup").group(1) == "180"
    assert pat.search("90-day Lock Up").group(1) == "90"


def test_price_fn_none_skips(ipo_session):
    results = ai_ipo_tracker.collect(
        tickers=["XX"],
        price_fn=lambda t: None,
        lockup_fn=lambda t: None,
        ipo_price_fn=lambda t: 50.0,
        last_price_fn=lambda t: None,
    )
    assert results == []


def test_outlier_guard_after_5_observations(ipo_session):
    Session = ipo_session
    s = Session()
    from db.repositories.semiconductor_repo import SemiconductorRepository
    repo = SemiconductorRepository(s)
    # 5개 관측 적재 (가격 100 부근)
    for i, d in enumerate(["2026-06-08", "2026-06-09", "2026-06-10", "2026-06-11", "2026-06-12"]):
        repo.upsert_indicator_value(
            indicator_name="ai_ipo:RDDT",
            observed_at=d,
            value=0.0,
            value_meta={"unit": "pct", "current_price": 100.0},
        )
    s.commit()
    s.close()

    # 갑작스러운 200% 상승 → 격리
    results = ai_ipo_tracker.collect(
        tickers=["RDDT"],
        price_fn=lambda t: 300.0,
        lockup_fn=lambda t: None,
        ipo_price_fn=lambda t: 50.0,
        last_price_fn=lambda t: 100.0,
        observed_at="2026-06-13",
    )
    assert results == []  # 격리됨


def test_no_outlier_guard_first_5_observations(ipo_session):
    # 관측 < 5 시 격리 안 함
    results = ai_ipo_tracker.collect(
        tickers=["RDDT"],
        price_fn=lambda t: 200.0,
        lockup_fn=lambda t: None,
        ipo_price_fn=lambda t: 50.0,
        last_price_fn=lambda t: 100.0,  # 직전 100 → 200 (+100%) outlier-level
        observed_at="2026-06-13",
    )
    # history_count < 5 → 첫 5거래일 우회
    assert len(results) == 1
    assert results[0].value == pytest.approx(300.0)
