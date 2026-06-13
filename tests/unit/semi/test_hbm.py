"""지표 5 — HBM 공시 수집기 테스트."""

import os
import pytest

from stock.semi_collectors import hbm_contracts


def _fake_fetch_factory(per_corp):
    """{corp_code: [items]} 형태 mock 응답."""
    def _fn(*, api_key, corp_code, bgn_de, end_de):
        return per_corp.get(corp_code, [])
    return _fn


def test_hbm_match_simple(monkeypatch):
    monkeypatch.setenv("OPENDART_API_KEY", "dummy")
    fake = _fake_fetch_factory({
        "00126380": [
            {
                "rcept_no": "20260613000001",
                "report_nm": "단일판매ㆍ공급계약체결 (HBM3E)",
                "rcept_dt": "20260613",
            }
        ],
        "00164779": [],
    })
    results = hbm_contracts.collect(observed_at="2026-06-13", fetch_fn=fake)
    assert len(results) == 1
    r = results[0]
    assert r.indicator_name == "hbm_contracts"
    assert r.observed_at == "2026-06-13"
    assert r.value == 1.0
    assert r.value_meta["unit"] == "count"
    assert "20260613000001" in r.value_meta["rcept_no"]
    assert "HBM" in r.value_meta["matched_keywords"]


def test_hbm_zero_match_still_persists_row(monkeypatch):
    monkeypatch.setenv("OPENDART_API_KEY", "dummy")
    fake = _fake_fetch_factory({
        "00126380": [
            {
                "rcept_no": "20260613000099",
                "report_nm": "유상증자결정",  # 단일판매 아님
                "rcept_dt": "20260613",
            }
        ],
    })
    results = hbm_contracts.collect(observed_at="2026-06-13", fetch_fn=fake)
    assert len(results) == 1
    assert results[0].value == 0.0
    assert results[0].value_meta["rcept_no"] == []


def test_hbm_filter_requires_keyword_after_contract(monkeypatch):
    monkeypatch.setenv("OPENDART_API_KEY", "dummy")
    # 단일판매·공급계약은 매칭되지만 HBM/장기공급/메모리 없음 → 제외
    fake = _fake_fetch_factory({
        "00126380": [
            {
                "rcept_no": "20260613000010",
                "report_nm": "단일판매ㆍ공급계약체결 (자동차 부품)",
                "rcept_dt": "20260613",
            }
        ],
    })
    results = hbm_contracts.collect(observed_at="2026-06-13", fetch_fn=fake)
    assert results[0].value == 0.0


def test_hbm_dedup_across_corps(monkeypatch):
    monkeypatch.setenv("OPENDART_API_KEY", "dummy")
    # 동일 rcept_no가 양쪽에서 모두 등장 (이론상 불가, 가드 검증)
    fake = _fake_fetch_factory({
        "00126380": [
            {
                "rcept_no": "20260613000001",
                "report_nm": "단일판매ㆍ공급계약체결 (HBM)",
                "rcept_dt": "20260613",
            }
        ],
        "00164779": [
            {
                "rcept_no": "20260613000001",
                "report_nm": "단일판매ㆍ공급계약체결 (HBM)",
                "rcept_dt": "20260613",
            }
        ],
    })
    results = hbm_contracts.collect(observed_at="2026-06-13", fetch_fn=fake)
    assert results[0].value == 1.0
    assert len(results[0].value_meta["rcept_no"]) == 1


def test_hbm_multiple_keyword_matches(monkeypatch):
    monkeypatch.setenv("OPENDART_API_KEY", "dummy")
    fake = _fake_fetch_factory({
        "00126380": [
            {
                "rcept_no": "20260613000001",
                "report_nm": "단일판매ㆍ공급계약체결 (HBM 장기공급계약)",
                "rcept_dt": "20260613",
            },
            {
                "rcept_no": "20260613000002",
                "report_nm": "단일판매·공급계약체결 (메모리 장기 공급계약)",
                "rcept_dt": "20260613",
            },
        ],
        "00164779": [],
    })
    results = hbm_contracts.collect(observed_at="2026-06-13", fetch_fn=fake)
    assert results[0].value == 2.0
    assert len(results[0].value_meta["rcept_no"]) == 2


def test_hbm_no_api_key_raises(monkeypatch):
    monkeypatch.delenv("OPENDART_API_KEY", raising=False)
    fake = _fake_fetch_factory({})
    with pytest.raises(RuntimeError, match="OPENDART_API_KEY"):
        hbm_contracts.collect(observed_at="2026-06-13", fetch_fn=fake)
