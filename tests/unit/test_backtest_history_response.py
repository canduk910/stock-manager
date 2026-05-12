"""GET /api/backtest/history 응답에 symbols_names 변환 필드 검증 (R_1).

라우터(routers/backtest.py)는 `symbol_name`만 변환했으나, 다종목 백테스트의 경우
`symbols` 배열도 코드→이름 매핑이 필요하다. `symbols_names: [{code, name}]` 신규 필드.

- 단일 종목(기존): symbols None 또는 빈 → symbols_names 빈 배열 또는 None
- 다종목: symbols=["005930","000660","035720"] → symbols_names=[{code,name}, ...]
- 해외/알파벳 코드: code_to_name 호출하지 않고 code 그대로(name=code)
"""

from __future__ import annotations

from unittest.mock import patch


# 라우터에서 사용하는 code_to_name 경로 패치 — `from stock.symbol_map import code_to_name`은
# 함수 내부 import이므로 `stock.symbol_map.code_to_name` 자체를 패치.
def _fake_code_to_name(code: str) -> str:
    mapping = {
        "005930": "삼성전자",
        "000660": "SK하이닉스",
        "035720": "카카오",
    }
    return mapping.get(code, code)


def _build_history_rows(symbols_list=None, symbol="005930", market="KR"):
    """`strategy_store.get_job_history` 가짜 응답."""
    job = {
        "job_id": "job-test",
        "user_id": 1,
        "strategy_name": "momentum",
        "symbol": symbol,
        "market": market,
        "strategy_type": "local",
        "status": "completed",
    }
    if symbols_list is not None:
        job["symbols"] = symbols_list
    return [job]


class TestSymbolsNamesField:
    def test_single_symbol_returns_symbols_names_none_or_empty(self, client):
        """단일 종목 백테스트(symbols 키 없음) — symbols_names 없거나 None 또는 빈 배열."""
        with patch("stock.strategy_store.get_job_history", return_value=_build_history_rows(symbols_list=None)), \
             patch("stock.symbol_map.code_to_name", side_effect=_fake_code_to_name):
            resp = client.get("/api/backtest/history")
            assert resp.status_code == 200, resp.text
            jobs = resp.json()
            assert len(jobs) == 1
            j = jobs[0]
            assert j.get("symbol_name") == "삼성전자"  # 기존 단일 변환 보존
            # symbols_names는 없거나 None / 빈 리스트 중 하나 허용 (단일 종목 흐름)
            assert j.get("symbols_names") in (None, [], )

    def test_multi_symbols_kr_codes_translated(self, client):
        """다종목 KR 백테스트 — symbols_names 각 entry가 {code, name}."""
        symbols = ["005930", "000660", "035720"]
        with patch("stock.strategy_store.get_job_history", return_value=_build_history_rows(symbols_list=symbols)), \
             patch("stock.symbol_map.code_to_name", side_effect=_fake_code_to_name):
            resp = client.get("/api/backtest/history")
            assert resp.status_code == 200, resp.text
            jobs = resp.json()
            assert len(jobs) == 1
            j = jobs[0]
            # symbols 원본 유지
            assert j.get("symbols") == symbols
            # 신규 필드 — 길이 일치 + code/name 매핑
            names = j.get("symbols_names")
            assert isinstance(names, list)
            assert len(names) == 3
            assert names[0] == {"code": "005930", "name": "삼성전자"}
            assert names[1] == {"code": "000660", "name": "SK하이닉스"}
            assert names[2] == {"code": "035720", "name": "카카오"}

    def test_multi_symbols_non_domestic_pass_through(self, client):
        """비국내(해외/알파벳) 코드는 변환 없이 name=code 그대로."""
        symbols = ["AAPL", "MSFT", "005930"]  # 마지막 1개만 국내
        with patch("stock.strategy_store.get_job_history",
                   return_value=_build_history_rows(symbols_list=symbols, market="KR")), \
             patch("stock.symbol_map.code_to_name", side_effect=_fake_code_to_name):
            resp = client.get("/api/backtest/history")
            assert resp.status_code == 200, resp.text
            j = resp.json()[0]
            names = j.get("symbols_names")
            assert isinstance(names, list)
            assert len(names) == 3
            # AAPL/MSFT는 6자리 숫자가 아니므로 is_domestic False → name=code
            assert names[0] == {"code": "AAPL", "name": "AAPL"}
            assert names[1] == {"code": "MSFT", "name": "MSFT"}
            # 005930은 국내 → 한글 변환
            assert names[2] == {"code": "005930", "name": "삼성전자"}

    def test_empty_symbols_list(self, client):
        """symbols=[] 빈 배열 — symbols_names 빈 배열 (None과 동등 취급 허용)."""
        with patch("stock.strategy_store.get_job_history",
                   return_value=_build_history_rows(symbols_list=[])), \
             patch("stock.symbol_map.code_to_name", side_effect=_fake_code_to_name):
            resp = client.get("/api/backtest/history")
            assert resp.status_code == 200, resp.text
            j = resp.json()[0]
            # 빈 배열은 [] 또는 None 둘 다 허용
            assert j.get("symbols_names") in (None, [])
