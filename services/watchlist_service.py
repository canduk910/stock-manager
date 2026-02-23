"""관심종목 서비스 레이어.

stock/ 패키지(pykrx + OpenDart)를 조합해 웹 API용 데이터를 조립한다.
broker(KoreaInvestment)는 선택 인자로, 미설정 시 pykrx로 대체한다.
"""

import time
from typing import Optional

from stock import store, symbol_map
from stock.dart_fin import fetch_financials
from stock.market import fetch_detail, fetch_price


def _awk(won: Optional[int]) -> Optional[int]:
    """원 → 억원 (반올림 int). None이면 None."""
    return round(won / 1_0000_0000) if won is not None else None


def _growth(cur: Optional[int], prev: Optional[int]) -> Optional[float]:
    if cur is None or prev is None or prev == 0:
        return None
    return round((cur - prev) / abs(prev) * 100, 1)


def _period_label(fin: dict) -> str:
    bsns_year = fin.get("bsns_year")
    return f"{bsns_year}/12" if bsns_year else "-"


class WatchlistService:
    def __init__(self, broker=None):
        """broker: KoreaInvestment 인스턴스 (선택). 없으면 pykrx 사용."""
        self.broker = broker

    # ── 종목 resolve ────────────────────────────────────────────────────────

    def resolve_symbol(self, name_or_code: str) -> tuple[str, str]:
        """종목명 또는 코드 → (종목코드, 종목명).

        Raises:
            ValueError: 종목을 찾을 수 없거나 복수 매칭인 경우
        """
        result = symbol_map.resolve(name_or_code)
        if result:
            return result

        import re
        if not re.match(r"^\d{6}$", name_or_code):
            matches = symbol_map.name_to_results(name_or_code)
            if matches:
                names = ", ".join(f"{n}({c})" for c, n, _ in matches[:5])
                raise ValueError(f"'{name_or_code}'에 여러 종목이 매칭됩니다: {names}")

        raise ValueError(f"종목을 찾을 수 없습니다: '{name_or_code}'")

    # ── 대시보드 ─────────────────────────────────────────────────────────────

    def get_dashboard_data(self, items: list[dict]) -> list[dict]:
        """관심종목 목록 → 대시보드 행 데이터 리스트.

        pykrx 배치 호출은 내부 캐싱되므로 종목 수에 관계없이 빠름.
        DART API는 캐싱 후 종목당 1회 호출, 0.1초 간격 rate-limit.
        """
        results = []
        for item in items:
            code = item["code"]
            row: dict = {
                "code": code,
                "name": item["name"],
                "memo": item.get("memo", ""),
                # 시세
                "price": None,
                "change": None,
                "change_pct": None,
                "market_cap": None,
                # 재무
                "revenue": None,
                "operating_profit": None,
                "net_income": None,
                "oi_margin": None,
                "report_date": None,
            }

            try:
                price = fetch_price(code)
                if price:
                    row["price"] = price["close"]
                    row["change"] = price.get("change")
                    row["change_pct"] = price.get("change_pct")
                    row["market_cap"] = _awk(price.get("mktcap"))
            except Exception:
                pass

            try:
                fin = fetch_financials(code)
                if fin and fin.get("bsns_year"):
                    rev = fin.get("revenue")
                    op = fin.get("operating_income")
                    net = fin.get("net_income")
                    row["revenue"] = _awk(rev)
                    row["operating_profit"] = _awk(op)
                    row["net_income"] = _awk(net)
                    row["oi_margin"] = (
                        round(op / rev * 100, 1) if rev and op and rev != 0 else None
                    )
                    row["report_date"] = _period_label(fin)
            except Exception:
                pass

            results.append(row)
            time.sleep(0.05)  # rate-limit 여유

        return results

    # ── 단일 종목 상세 ───────────────────────────────────────────────────────

    def get_stock_detail(self, code: str) -> dict:
        """기본정보 + 3개년 재무 통합."""
        detail = fetch_detail(code)
        fin = fetch_financials(code)
        item = store.get_item(code)

        basic: dict = {"code": code}
        if detail:
            mktcap = detail.get("mktcap")
            basic.update(
                {
                    "price": detail["close"],
                    "change": detail.get("change"),
                    "change_pct": detail.get("change_pct"),
                    "market_cap": _awk(mktcap),
                    "per": detail.get("per"),
                    "pbr": detail.get("pbr"),
                    "high_52": detail.get("high_52"),
                    "low_52": detail.get("low_52"),
                    "market": detail.get("market_type"),
                    "sector": detail.get("sector"),
                    "shares": detail.get("shares"),
                }
            )

        financials_3y = []
        if fin and fin.get("bsns_year"):
            bsns_year = fin["bsns_year"]

            rev_pp = fin.get("revenue_prev2")
            op_pp = fin.get("operating_income_prev2")
            net_pp = fin.get("net_income_prev2")

            rev_p = fin.get("revenue_prev")
            op_p = fin.get("operating_income_prev")
            net_p = fin.get("net_income_prev")

            rev = fin.get("revenue")
            op = fin.get("operating_income")
            net = fin.get("net_income")

            financials_3y = [
                {
                    "year": fin.get("period_prev2") or str(bsns_year - 2),
                    "revenue": _awk(rev_pp),
                    "operating_profit": _awk(op_pp),
                    "net_income": _awk(net_pp),
                    "yoy_revenue": None,
                    "yoy_op": None,
                },
                {
                    "year": fin.get("period_prev") or str(bsns_year - 1),
                    "revenue": _awk(rev_p),
                    "operating_profit": _awk(op_p),
                    "net_income": _awk(net_p),
                    "yoy_revenue": _growth(rev_p, rev_pp),
                    "yoy_op": _growth(op_p, op_pp),
                },
                {
                    "year": fin.get("period_cur") or str(bsns_year),
                    "revenue": _awk(rev),
                    "operating_profit": _awk(op),
                    "net_income": _awk(net),
                    "yoy_revenue": _growth(rev, rev_p),
                    "yoy_op": _growth(op, op_p),
                },
            ]

        return {
            "basic": basic,
            "financials_3y": financials_3y,
            "memo": item.get("memo", "") if item else "",
        }
