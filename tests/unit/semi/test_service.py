"""semiconductor_service 단위 테스트.

수집기는 mock으로 대체. ORM 영속 + 시그널 평가 + 상태 변경 감지 검증.
"""

import pytest
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
import db.models  # noqa: F401
from services import semiconductor_service as svc
from stock.semi_collectors.base import CollectorResult


@pytest.fixture
def svc_session(monkeypatch):
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

    monkeypatch.setattr(svc, "get_session", fake_get_session)
    yield Session
    Base.metadata.drop_all(engine)
    engine.dispose()


def _seed_thresholds(Session):
    from db.repositories.semiconductor_repo import SemiconductorRepository
    s = Session()
    repo = SemiconductorRepository(s)
    repo.upsert_threshold(
        indicator_name="hyperscaler_capex", threshold_key="yoy_warning_pct", value=-5.0
    )
    repo.upsert_threshold(
        indicator_name="hyperscaler_capex", threshold_key="yoy_alert_pct", value=-15.0
    )
    repo.upsert_threshold(
        indicator_name="memory_inventory", threshold_key="days_warning_increase_qtr", value=2
    )
    repo.upsert_threshold(
        indicator_name="memory_inventory", threshold_key="days_alert_threshold", value=120.0
    )
    repo.upsert_threshold(
        indicator_name="market_breadth", threshold_key="adr20_warning", value=0.8
    )
    repo.upsert_threshold(
        indicator_name="hbm_contracts", threshold_key="keyword_regex", value="HBM"
    )
    s.commit()
    s.close()


def _seed_indicator(Session, name, rows):
    from db.repositories.semiconductor_repo import SemiconductorRepository
    s = Session()
    repo = SemiconductorRepository(s)
    for r in rows:
        repo.upsert_indicator_value(
            indicator_name=name,
            observed_at=r["observed_at"],
            value=r["value"],
            value_meta=r.get("value_meta", {}),
            source="seed",
        )
    s.commit()
    s.close()


def test_dispatch_collector_unknown(svc_session):
    from services.exceptions import ServiceError
    with pytest.raises(ServiceError):
        svc._dispatch_collector("nonexistent")


def test_run_all_collectors_failure_isolation(svc_session, monkeypatch):
    # 1개 수집기 정상, 1개 raise — 정상은 진행, 실패는 failures에 기록
    def ok_collect():
        return [
            CollectorResult(
                indicator_name="hbm_contracts",
                observed_at="2026-06-13",
                value=0.0,
                value_meta={"unit": "count"},
            )
        ]

    def fail_collect():
        raise RuntimeError("OPENDART_API_KEY 미설정")

    import stock.semi_collectors.hbm_contracts as hbm_mod
    import stock.semi_collectors.market_breadth as mb_mod
    import stock.semi_collectors.memory_inventory as inv_mod
    import stock.semi_collectors.hyperscaler_capex as capex_mod
    import stock.semi_collectors.ai_ipo_tracker as ipo_mod

    monkeypatch.setattr(hbm_mod, "collect", ok_collect)
    monkeypatch.setattr(mb_mod, "collect", fail_collect)
    monkeypatch.setattr(inv_mod, "collect", lambda: [])
    monkeypatch.setattr(capex_mod, "collect", lambda: [])
    monkeypatch.setattr(ipo_mod, "collect", lambda: [])

    result = svc.run_all_collectors()
    assert "hbm_contracts" in result["ran"]
    assert "market_breadth" in result["failures"]
    assert "OPENDART_API_KEY" in result["failures"]["market_breadth"]
    assert result["rows_persisted"] == 1


def test_evaluate_and_persist_emits_signal_on_change(svc_session):
    Session = svc_session
    _seed_thresholds(Session)
    # 메모리 재고 2분기 연속 증가 → WARNING
    _seed_indicator(Session, "memory_inventory", [
        {"observed_at": "2025-03-31", "value": 75.0},
        {"observed_at": "2025-06-30", "value": 82.0},
        {"observed_at": "2025-09-30", "value": 92.0},
    ])

    result = svc.evaluate_and_persist()
    inserted = result["signals_inserted"]
    # 메모리 변경(GREEN→WARNING), 종합(GREEN→YELLOW)
    names = {s["indicator_name"] for s in inserted}
    assert "memory_inventory" in names
    assert "composite" in names

    # 2회 호출 시 변경 없음 → signals 없음
    result2 = svc.evaluate_and_persist()
    assert result2["signals_inserted"] == []


def test_evaluate_composite_red_rule(svc_session):
    Session = svc_session
    _seed_thresholds(Session)
    # capex YoY -6%, -7% 연속 + 메모리 92일(3분기 연속 증가)
    _seed_indicator(Session, "hyperscaler_capex", [
        {"observed_at": "2025-03-31", "value": 80e9, "value_meta": {"yoy_pct": -2.0}},
        {"observed_at": "2025-06-30", "value": 78e9, "value_meta": {"yoy_pct": -6.0}},
        {"observed_at": "2025-09-30", "value": 75e9, "value_meta": {"yoy_pct": -8.0}},
    ])
    _seed_indicator(Session, "memory_inventory", [
        {"observed_at": "2025-03-31", "value": 75.0},
        {"observed_at": "2025-06-30", "value": 82.0},
        {"observed_at": "2025-09-30", "value": 92.0},
    ])

    result = svc.evaluate_and_persist()
    composite_levels = [s for s in result["signals_inserted"] if s["indicator_name"] == "composite"]
    assert len(composite_levels) == 1
    assert composite_levels[0]["level"] == "RED"


def test_get_dashboard_shape(svc_session):
    Session = svc_session
    _seed_thresholds(Session)
    dash = svc.get_dashboard()
    assert "composite" in dash
    assert "indicators" in dash
    for name in ["hyperscaler_capex", "memory_inventory", "hbm_contracts", "ai_ipo", "market_breadth"]:
        assert name in dash["indicators"]
        assert "level" in dash["indicators"][name]


def test_upsert_threshold_persists(svc_session):
    result = svc.upsert_threshold(
        indicator_name="hyperscaler_capex",
        threshold_key="yoy_warning_pct",
        value=-7.0,
        comment="tighten",
        updated_by=1,
    )
    assert result["threshold"]["value"] == -7.0
    assert result["threshold"]["comment"] == "tighten"
    assert result["threshold"]["updated_by"] == 1


def test_ack_signal_not_found_raises(svc_session):
    from services.exceptions import NotFoundError
    with pytest.raises(NotFoundError):
        svc.ack_signal(99999)


def test_get_signals_recent(svc_session):
    Session = svc_session
    from db.repositories.semiconductor_repo import SemiconductorRepository
    s = Session()
    repo = SemiconductorRepository(s)
    repo.insert_signal(indicator_name="composite", level="GREEN", message="ok")
    repo.insert_signal(indicator_name="hbm_contracts", level="INFO", message="match")
    s.commit()
    s.close()

    result = svc.get_signals()
    assert result["count"] == 2
    # 최신순
    assert result["signals"][0]["indicator_name"] == "hbm_contracts"


def test_get_indicator_history(svc_session):
    Session = svc_session
    _seed_indicator(Session, "memory_inventory", [
        {"observed_at": "2025-06-30", "value": 80.0},
        {"observed_at": "2025-09-30", "value": 92.0},
    ])
    h = svc.get_indicator_history("memory_inventory", days=10)
    assert len(h["points"]) == 2
    assert h["indicator_name"] == "memory_inventory"
