"""지표 4 — 메모리 재고일수 수집기 테스트."""

import pytest

from stock.semi_collectors import memory_inventory


def _fixture_quarter(year, q, inv, cogs):
    return {
        "year": year,
        "quarter": q,
        "inventory": inv,
        "cogs_quarter": cogs,
        "period_end": memory_inventory._quarter_end_date(year, q),
    }


def test_inventory_days_basic():
    # 삼성: 재고 30조, 매출원가 30조/분기 → 91일
    # 하이닉스: 재고 15조, 매출원가 15조/분기 → 91일
    # 평균 91일
    samsung_rows = [_fixture_quarter(2025, 4, 30_000_000_000_000, 30_000_000_000_000)]
    hynix_rows = [_fixture_quarter(2025, 4, 15_000_000_000_000, 15_000_000_000_000)]

    def fake(code):
        if code == "005930":
            return samsung_rows
        if code == "000660":
            return hynix_rows
        return []

    results = memory_inventory.collect(fetch_fn=fake)
    assert len(results) == 1
    r = results[0]
    assert r.indicator_name == "memory_inventory"
    assert r.observed_at == "2025-12-31"
    assert r.value == pytest.approx(91.0, rel=1e-2)
    assert r.value_meta["unit"] == "days"
    assert "005930" in r.value_meta["by_company"]
    assert r.value_meta["by_company"]["005930"]["days"] == pytest.approx(91.0, rel=1e-2)


def test_inventory_days_avg_when_diverge():
    # 삼성 100일 / 하이닉스 60일 → 평균 80일
    # cogs 25조 / 분기 → 91/25*days_target = inv → days=80 → inv = 80 * 25/91
    samsung_rows = [
        _fixture_quarter(2025, 4, int(100 * 25_000_000_000_000 / 91), 25_000_000_000_000)
    ]
    hynix_rows = [
        _fixture_quarter(2025, 4, int(60 * 25_000_000_000_000 / 91), 25_000_000_000_000)
    ]

    def fake(code):
        return samsung_rows if code == "005930" else hynix_rows

    results = memory_inventory.collect(fetch_fn=fake)
    r = results[0]
    assert r.value == pytest.approx(80.0, rel=2e-2)


def test_cogs_zero_yields_none_days_skips_company():
    # 한 회사 cogs 0 → 그 회사는 days=None, 다른 회사 단독 평균
    samsung_rows = [_fixture_quarter(2025, 4, 30_000_000_000_000, 30_000_000_000_000)]
    hynix_rows = [_fixture_quarter(2025, 4, 15_000_000_000_000, 0)]

    def fake(code):
        return samsung_rows if code == "005930" else hynix_rows

    results = memory_inventory.collect(fetch_fn=fake)
    assert len(results) == 1
    assert results[0].value == pytest.approx(91.0, rel=1e-2)
    # hynix 데이터 보존 (days=None 으로)
    assert results[0].value_meta["by_company"]["000660"]["days"] is None


def test_outlier_quarter_excluded():
    # 정상 90일 → 다음 분기 250일 (+178%) → 격리
    samsung = [
        _fixture_quarter(2025, 3, 27_000_000_000_000, 27_000_000_000_000),  # 91일
        _fixture_quarter(2025, 4, 50_000_000_000_000, 10_000_000_000_000),  # 91*5 = 455일 (spike)
    ]
    hynix = [
        _fixture_quarter(2025, 3, 13_500_000_000_000, 13_500_000_000_000),  # 91일
        _fixture_quarter(2025, 4, 25_000_000_000_000, 5_000_000_000_000),  # 455일
    ]

    def fake(code):
        return samsung if code == "005930" else hynix

    results = memory_inventory.collect(fetch_fn=fake)
    # Q3 통과, Q4 격리
    obs = [r.observed_at for r in results]
    assert "2025-09-30" in obs
    assert "2025-12-31" not in obs


def test_common_period_intersection():
    # 한 회사가 더 적은 분기를 가지면 교집합만 결과
    samsung = [
        _fixture_quarter(2025, 3, 27_000_000_000_000, 27_000_000_000_000),
        _fixture_quarter(2025, 4, 30_000_000_000_000, 30_000_000_000_000),
    ]
    hynix = [
        _fixture_quarter(2025, 4, 15_000_000_000_000, 15_000_000_000_000),
    ]

    def fake(code):
        return samsung if code == "005930" else hynix

    results = memory_inventory.collect(fetch_fn=fake)
    obs = [r.observed_at for r in results]
    assert obs == ["2025-12-31"]


def test_no_data_returns_empty():
    def fake(code):
        return []
    results = memory_inventory.collect(fetch_fn=fake)
    assert results == []
