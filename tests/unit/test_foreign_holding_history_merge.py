"""REQ-FH-EXT-STORE-01: 외국인 보유율 누적 시계열 머지 헬퍼 단위 테스트.

서비스 내부 헬퍼 `_merge_fh_daily(existing, new_rows, max_keep)` 검증:
- existing + new_rows → date 기준 dict-merge
- ascending sort by date
- max_keep(기본 250) 초과 시 FIFO 가장 오래된 row 제거
- new_rows 중 hts_frgn_ehrt is None row는 결합에서 제외
- 동일 date 중복 시 마지막 row 유지(dedup)
- 빈 입력 처리
"""
from __future__ import annotations

import pytest


def _row(date: str, ehrt: float | None = 50.0, close: int = 71000,
         ntby: int = 1000) -> dict:
    return {
        "date": date,
        "close": close,
        "hts_frgn_ehrt": ehrt,
        "frgn_ntby_qty": ntby,
    }


class TestMergeFhDaily:

    def test_empty_existing_returns_new_sorted(self):
        from services.supply_demand_service import _merge_fh_daily
        new_rows = [_row("2026-05-03"), _row("2026-05-01"), _row("2026-05-02")]
        result = _merge_fh_daily([], new_rows)
        assert [r["date"] for r in result] == ["2026-05-01", "2026-05-02", "2026-05-03"]

    def test_existing_plus_new_no_overlap(self):
        from services.supply_demand_service import _merge_fh_daily
        existing = [_row("2026-05-01", ehrt=50.0), _row("2026-05-02", ehrt=51.0)]
        new_rows = [_row("2026-05-03", ehrt=52.0)]
        result = _merge_fh_daily(existing, new_rows)
        assert [r["date"] for r in result] == ["2026-05-01", "2026-05-02", "2026-05-03"]
        assert [r["hts_frgn_ehrt"] for r in result] == [50.0, 51.0, 52.0]

    def test_overlap_dedupes_by_date_last_wins(self):
        from services.supply_demand_service import _merge_fh_daily
        existing = [_row("2026-05-01", ehrt=50.0), _row("2026-05-02", ehrt=51.0)]
        new_rows = [_row("2026-05-02", ehrt=51.5), _row("2026-05-03", ehrt=52.0)]
        result = _merge_fh_daily(existing, new_rows)
        assert len(result) == 3
        m = {r["date"]: r["hts_frgn_ehrt"] for r in result}
        # 동일 date 충돌 — 새 row 우선
        assert m["2026-05-02"] == 51.5

    def test_max_keep_cap_fifo(self):
        from services.supply_demand_service import _merge_fh_daily
        existing = [_row(f"2026-01-{i:02d}", ehrt=50.0 + i * 0.01) for i in range(1, 11)]
        # 11 existing
        existing.append(_row("2026-01-11", ehrt=50.5))
        new_rows = [_row("2026-01-12", ehrt=51.0)]
        result = _merge_fh_daily(existing, new_rows, max_keep=5)
        # 12 total → keep last 5
        assert len(result) == 5
        assert result[0]["date"] == "2026-01-08"
        assert result[-1]["date"] == "2026-01-12"

    def test_default_max_keep_250(self):
        from services.supply_demand_service import _merge_fh_daily
        # 251 unique dates
        existing = [_row(f"2025-{(i // 31) + 1:02d}-{(i % 31) + 1:02d}",
                         ehrt=50.0 + i * 0.001) for i in range(255)]
        # 일자 중복 가능성 — set으로 dedup 보장
        seen = {}
        for r in existing:
            seen[r["date"]] = r
        unique = list(seen.values())
        result = _merge_fh_daily([], unique)
        assert len(result) <= 250

    def test_filters_out_new_rows_with_none_ehrt(self):
        from services.supply_demand_service import _merge_fh_daily
        existing = [_row("2026-05-01", ehrt=50.0)]
        new_rows = [
            _row("2026-05-02", ehrt=None),  # 결함 — 제외
            _row("2026-05-03", ehrt=52.0),
        ]
        result = _merge_fh_daily(existing, new_rows)
        dates = [r["date"] for r in result]
        assert "2026-05-02" not in dates
        assert dates == ["2026-05-01", "2026-05-03"]

    def test_keeps_existing_row_with_none_ehrt(self):
        """existing은 그대로 유지(이미 영속화된 row까지 retroactive 제외하지 않음).

        도메인 자문: 'new_rows의 결함 row를 append 거부'에 한정.
        (UI 단에서는 service의 daily 응답에서 None ehrt row를 제외)
        """
        from services.supply_demand_service import _merge_fh_daily
        existing = [_row("2026-05-01", ehrt=None)]
        new_rows = [_row("2026-05-02", ehrt=52.0)]
        result = _merge_fh_daily(existing, new_rows)
        # existing은 보존되지만 new에서 None 가드는 적용
        dates = [r["date"] for r in result]
        assert "2026-05-01" in dates
        assert "2026-05-02" in dates

    def test_duplicate_dates_in_new_rows_last_wins(self):
        from services.supply_demand_service import _merge_fh_daily
        new_rows = [
            _row("2026-05-01", ehrt=50.0),
            _row("2026-05-01", ehrt=51.0),  # 동일 date — 후자 우선
            _row("2026-05-01", ehrt=52.0),
        ]
        result = _merge_fh_daily([], new_rows)
        assert len(result) == 1
        assert result[0]["hts_frgn_ehrt"] == 52.0

    def test_empty_inputs_returns_empty(self):
        from services.supply_demand_service import _merge_fh_daily
        assert _merge_fh_daily([], []) == []
