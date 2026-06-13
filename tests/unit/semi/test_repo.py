"""SemiconductorRepository 단위 테스트.

검증:
- IndicatorValue upsert 멱등성 + 시계열 순서
- Signal insert + 마지막 신호 조회
- SemiconductorThreshold upsert + 평탄 dict 변환
"""

from db.repositories.semiconductor_repo import SemiconductorRepository


def test_indicator_value_upsert_idempotent(semi_db):
    repo = SemiconductorRepository(semi_db)
    id1 = repo.upsert_indicator_value(
        indicator_name="hbm_contracts",
        observed_at="2026-06-12",
        value=0.0,
        value_meta={"unit": "count", "rcept_no": []},
        source="dart",
    )
    id2 = repo.upsert_indicator_value(
        indicator_name="hbm_contracts",
        observed_at="2026-06-12",
        value=2.0,
        value_meta={"unit": "count", "rcept_no": ["A", "B"]},
        source="dart",
    )
    assert id1 == id2  # 같은 row 갱신

    latest = repo.get_latest_value("hbm_contracts")
    assert latest is not None
    assert latest["value"] == 2.0
    assert latest["value_meta"]["rcept_no"] == ["A", "B"]


def test_list_values_ordering_asc_and_recent_n(semi_db):
    repo = SemiconductorRepository(semi_db)
    for i, day in enumerate(["2026-03-31", "2026-06-30", "2025-12-31", "2025-09-30"]):
        repo.upsert_indicator_value(
            indicator_name="memory_inventory",
            observed_at=day,
            value=float(80 + i * 5),
            value_meta={"unit": "days"},
            source="dart_fin",
        )

    asc = repo.list_values("memory_inventory", limit=10, order="asc")
    assert [r["observed_at"] for r in asc] == [
        "2025-09-30",
        "2025-12-31",
        "2026-03-31",
        "2026-06-30",
    ]

    recent4 = repo.list_recent_n("memory_inventory", n=4)
    assert len(recent4) == 4
    # ASC 정렬 (시간순)
    assert recent4[-1]["observed_at"] == "2026-06-30"
    assert recent4[0]["observed_at"] == "2025-09-30"


def test_signal_insert_and_last_lookup(semi_db):
    repo = SemiconductorRepository(semi_db)
    repo.insert_signal(
        indicator_name="composite",
        level="GREEN",
        message="초기 상태",
        value_snapshot={},
    )
    repo.insert_signal(
        indicator_name="composite",
        level="YELLOW",
        message="capex 둔화 감지",
        value_snapshot={"capex_yoy": -6.1},
    )
    last = repo.get_last_signal("composite")
    assert last["level"] == "YELLOW"
    assert "capex" in last["message"]


def test_signal_listing_with_since_filter(semi_db):
    import time
    repo = SemiconductorRepository(semi_db)
    repo.insert_signal(indicator_name="hbm_contracts", level="INFO", message="A")
    cutoff = repo.list_signals(limit=1)[0]["fired_at"]
    # ISO 시각이 초 단위라 동일 timestamp 회피
    time.sleep(1.1)
    repo.insert_signal(indicator_name="hbm_contracts", level="INFO", message="B")
    after = repo.list_signals(since=cutoff)
    assert len(after) >= 1
    assert any(s["message"] == "B" for s in after)


def test_threshold_upsert_and_map(semi_db):
    repo = SemiconductorRepository(semi_db)
    repo.upsert_threshold(
        indicator_name="hyperscaler_capex",
        threshold_key="yoy_warning_pct",
        value=-5.0,
        comment="seed",
    )
    repo.upsert_threshold(
        indicator_name="hyperscaler_capex",
        threshold_key="yoy_warning_pct",
        value=-6.0,
        updated_by=1,
    )
    # upsert: 같은 row 갱신
    rows = repo.list_thresholds("hyperscaler_capex")
    assert len(rows) == 1
    assert rows[0]["value"] == -6.0
    assert rows[0]["updated_by"] == 1

    repo.upsert_threshold(
        indicator_name="hyperscaler_capex",
        threshold_key="yoy_alert_pct",
        value=-15.0,
    )
    m = repo.thresholds_as_map("hyperscaler_capex")
    assert m == {"yoy_warning_pct": -6.0, "yoy_alert_pct": -15.0}


def test_threshold_get_value_default(semi_db):
    repo = SemiconductorRepository(semi_db)
    assert repo.get_threshold_value("xxx", "yyy", default=42) == 42
    repo.upsert_threshold(
        indicator_name="market_breadth",
        threshold_key="adr20_warning",
        value=0.8,
    )
    assert repo.get_threshold_value("market_breadth", "adr20_warning") == 0.8


def test_ack_signal(semi_db):
    repo = SemiconductorRepository(semi_db)
    sid = repo.insert_signal(
        indicator_name="market_breadth",
        level="WARNING",
        message="ADR 0.72",
    )
    assert repo.ack_signal(sid) is True
    rows = repo.list_signals(indicator_name="market_breadth")
    assert rows[0]["ack"] is True
    assert repo.ack_signal(99999) is False
