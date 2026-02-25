"""관심종목 서비스 레이어.

stock/ 패키지(pykrx + OpenDart + yfinance)를 조합해 웹 API용 데이터를 조립한다.
broker(KoreaInvestment)는 선택 인자로, 미설정 시 pykrx로 대체한다.
"""

import time
from typing import Optional

from stock import store, symbol_map
from stock.dart_fin import fetch_financials, fetch_financials_multi_year
from stock.market import fetch_detail, fetch_price
from stock.utils import is_domestic
import stock.yf_client as yf_client


def _awk(won: Optional[int]) -> Optional[int]:
    """원 → 억원 (반올림 int). None이면 None."""
    return round(won / 1_0000_0000) if won is not None else None


def _usd_m(usd: Optional[int]) -> Optional[float]:
    """USD → 백만달러(M). None이면 None."""
    return round(usd / 1_000_000, 1) if usd is not None else None


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

    def resolve_symbol(self, name_or_code: str, market: str = "KR") -> tuple[str, str, str]:
        """종목명 또는 코드 → (종목코드, 종목명, market).

        Raises:
            ValueError: 종목을 찾을 수 없거나 복수 매칭인 경우
        """
        if market != "KR":
            # 해외: ticker 직접 검증
            ticker = name_or_code.upper().strip()
            info = yf_client.validate_ticker(ticker)
            if not info:
                raise ValueError(f"종목을 찾을 수 없습니다: '{ticker}'")
            return ticker, info["name"], market

        # 국내: 기존 pykrx 기반 검색
        result = symbol_map.resolve(name_or_code)
        if result:
            return result[0], result[1], "KR"

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
            market = item.get("market", "KR")
            domestic = is_domestic(code) and market == "KR"

            row: dict = {
                "code": code,
                "market": market,
                "name": item["name"],
                "memo": item.get("memo", ""),
                "currency": "KRW" if domestic else "USD",
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

            if domestic:
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
            else:
                # 해외: yfinance
                try:
                    price = yf_client.fetch_price_yf(code)
                    if price:
                        row["price"] = price["close"]
                        row["change"] = price.get("change")
                        row["change_pct"] = price.get("change_pct")
                        mktcap = price.get("mktcap")
                        row["market_cap"] = _usd_m(mktcap)  # M USD
                except Exception:
                    pass

                try:
                    fin = yf_client.fetch_financials_yf(code)
                    if fin:
                        rev = fin.get("revenue")
                        op = fin.get("operating_income")
                        net = fin.get("net_income")
                        row["revenue"] = _usd_m(rev)
                        row["operating_profit"] = _usd_m(op)
                        row["net_income"] = _usd_m(net)
                        row["oi_margin"] = (
                            round(op / rev * 100, 1) if rev and op and rev != 0 else None
                        )
                        row["report_date"] = str(fin.get("year", "")) if fin.get("year") else None
                except Exception:
                    pass

            results.append(row)
            time.sleep(0.05)  # rate-limit 여유

        return results

    # ── 단일 종목 상세 ───────────────────────────────────────────────────────

    def get_stock_detail(self, code: str, market: str = "KR") -> dict:
        """기본정보 + 최대 10개년 재무 통합."""
        domestic = is_domestic(code) and market == "KR"

        if domestic:
            detail = fetch_detail(code)
            multi_rows = fetch_financials_multi_year(code, years=10)
            item = store.get_item(code, market="KR")

            basic: dict = {"code": code, "currency": "KRW"}
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

            financials_ny = []
            for i, row in enumerate(multi_rows):
                prev = multi_rows[i - 1] if i > 0 else None
                rev = row["revenue"]
                op = row["operating_income"]
                net = row["net_income"]
                prev_rev = prev["revenue"] if prev else None
                prev_op = prev["operating_income"] if prev else None
                financials_ny.append(
                    {
                        "year": row["year"],
                        "revenue": _awk(rev),
                        "operating_profit": _awk(op),
                        "net_income": _awk(net),
                        "yoy_revenue": _growth(rev, prev_rev),
                        "yoy_op": _growth(op, prev_op),
                        "dart_url": row.get("dart_url", ""),
                    }
                )
        else:
            # 해외: yfinance
            detail = yf_client.fetch_detail_yf(code)
            multi_rows_yf = yf_client.fetch_financials_multi_year_yf(code, years=4)
            item = store.get_item(code, market=market)

            basic: dict = {"code": code, "currency": "USD"}
            if detail:
                mktcap = detail.get("mktcap")
                basic.update(
                    {
                        "name": detail.get("name", code),
                        "price": detail.get("close"),
                        "change": detail.get("change"),
                        "change_pct": detail.get("change_pct"),
                        "market_cap": _usd_m(mktcap),
                        "per": detail.get("per"),
                        "pbr": detail.get("pbr"),
                        "high_52": detail.get("high_52"),
                        "low_52": detail.get("low_52"),
                        "market": detail.get("market_type"),
                        "sector": detail.get("sector"),
                    }
                )

            financials_ny = []
            for i, row in enumerate(multi_rows_yf):
                prev = multi_rows_yf[i - 1] if i > 0 else None
                rev = row["revenue"]
                op = row["operating_income"]
                net = row["net_income"]
                prev_rev = prev["revenue"] if prev else None
                prev_op = prev["operating_income"] if prev else None
                financials_ny.append(
                    {
                        "year": row["year"],
                        "revenue": _usd_m(rev),
                        "operating_profit": _usd_m(op),
                        "net_income": _usd_m(net),
                        "yoy_revenue": _growth(rev, prev_rev),
                        "yoy_op": _growth(op, prev_op),
                        "dart_url": "",
                    }
                )

        return {
            "basic": basic,
            "financials_3y": financials_ny,   # 키 이름 유지 (하위 호환)
            "memo": item.get("memo", "") if item else "",
        }
