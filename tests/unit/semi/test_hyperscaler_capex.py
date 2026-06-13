"""지표 2 — 하이퍼스케일러 capex 수집기 테스트.

SEC companyfacts 응답 fixture mock + FY→Q4 도출 검증.
"""

import pytest

from stock.semi_collectors import hyperscaler_capex


def _fixture_facts(ticker_quarters: dict) -> dict:
    """{(fy, fp, end): val} → companyfacts 형태로 변환."""
    rows = []
    for (fy, fp, end), val in ticker_quarters.items():
        rows.append({"fy": fy, "fp": fp, "end": end, "val": val, "filed": "2026-05-01"})
    return {
        "facts": {
            "us-gaap": {
                "PaymentsToAcquirePropertyPlantAndEquipment": {
                    "units": {"USD": rows}
                }
            }
        }
    }


def test_fy_to_q4_derivation():
    """Q1+Q2+Q3 + FY 가 있으면 Q4 = FY - 합."""
    facts = _fixture_facts({
        (2024, "Q1", "2024-03-31"): 10_000_000_000,
        (2024, "Q2", "2024-06-30"): 12_000_000_000,
        (2024, "Q3", "2024-09-30"): 14_000_000_000,
        (2024, "FY", "2024-12-31"): 50_000_000_000,
    })
    out = hyperscaler_capex._quarterly_capex_from_facts(facts)
    # Q1/Q2/Q3 + Q4 도출
    assert out["2024-03-31"]["fp"] == "Q1"
    assert out["2024-06-30"]["fp"] == "Q2"
    assert out["2024-09-30"]["fp"] == "Q3"
    assert out["2024-12-31"]["fp"] == "Q4"
    assert out["2024-12-31"]["val"] == 50_000_000_000 - (10_000_000_000 + 12_000_000_000 + 14_000_000_000)


def test_collect_aggregates_4_companies_and_yoy():
    # 4사 분기별 동일 데이터 fixture
    def make(scale: float):
        return _fixture_facts({
            (2023, "Q1", "2023-03-31"): int(10e9 * scale),
            (2023, "Q2", "2023-06-30"): int(10e9 * scale),
            (2023, "Q3", "2023-09-30"): int(10e9 * scale),
            (2023, "FY", "2023-12-31"): int(40e9 * scale),
            (2024, "Q1", "2024-03-31"): int(12e9 * scale),
        })

    fixtures = {
        "0000789019": make(1.0),  # MSFT
        "0001652044": make(1.2),  # GOOGL
        "0001018724": make(1.5),  # AMZN
        "0001326801": make(0.8),  # META
    }

    def fake_fetch(cik):
        return fixtures[cik]

    results = hyperscaler_capex.collect(fetch_fn=fake_fetch)
    # 5분기 중 Q1(2023) ~ Q1(2024) — Q1 2024는 YoY 계산 가능 (vs Q1 2023)
    by_obs = {r.observed_at: r for r in results}
    assert "2024-03-31" in by_obs
    r = by_obs["2024-03-31"]
    # 4사 합 = 12e9 × 4.5(=1+1.2+1.5+0.8)
    expected = 12_000_000_000 * (1.0 + 1.2 + 1.5 + 0.8)
    assert r.value == pytest.approx(expected)
    # YoY = (12 - 10) / 10 = 20%
    assert r.value_meta["yoy_pct"] == pytest.approx(20.0, rel=1e-3)
    assert r.value_meta["unit"] == "USD"
    assert "by_company" in r.value_meta


def test_collect_skips_outlier_quarter():
    # 직전 분기 대비 +200% 발생 시 격리
    def make_spike():
        return _fixture_facts({
            (2024, "Q1", "2024-03-31"): 10_000_000_000,
            (2024, "Q2", "2024-06-30"): 10_000_000_000,
            (2024, "Q3", "2024-09-30"): 50_000_000_000,  # +400% spike (outlier)
        })

    fixtures = {cik: make_spike() for cik in [
        "0000789019", "0001652044", "0001018724", "0001326801"
    ]}

    def fake_fetch(cik):
        return fixtures[cik]

    results = hyperscaler_capex.collect(fetch_fn=fake_fetch)
    obs_dates = [r.observed_at for r in results]
    assert "2024-03-31" in obs_dates
    assert "2024-06-30" in obs_dates
    # Q3 spike 는 격리
    assert "2024-09-30" not in obs_dates


def test_no_data_returns_empty_list():
    def fake_fetch(cik):
        return {"facts": {"us-gaap": {}}}
    results = hyperscaler_capex.collect(fetch_fn=fake_fetch)
    assert results == []


def test_user_agent_invalid_contact_raises(monkeypatch):
    monkeypatch.setattr(hyperscaler_capex, "SEC_EDGAR_USER_AGENT_CONTACT", "")
    from services.exceptions import ConfigError
    with pytest.raises(ConfigError):
        hyperscaler_capex._user_agent()
