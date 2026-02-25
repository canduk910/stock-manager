"""종목 상세 분석 서비스 레이어.

10년 재무, 월별 밸류에이션 히스토리, 종합 리포트를 제공한다.
해외주식(yfinance)도 지원한다.
"""

from typing import Optional

from stock import symbol_map
from stock.dart_fin import fetch_financials_multi_year
from stock.market import fetch_detail, fetch_valuation_history
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


def _cagr(start_val, end_val, n_years: int) -> Optional[float]:
    """CAGR 계산. 음수 or 0이면 None."""
    if start_val is None or end_val is None or n_years <= 0:
        return None
    try:
        sv = float(start_val)
        ev = float(end_val)
        if sv <= 0:
            return None
        return round(((ev / sv) ** (1 / n_years) - 1) * 100, 1)
    except Exception:
        return None


class DetailService:
    def get_financials(self, code: str, years: int = 10) -> dict:
        """최대 years개 사업연도 재무 데이터 반환.

        반환:
            {
                "code": str,
                "currency": "KRW" | "USD",
                "rows": [
                    {
                        "year": 2024,
                        "revenue": 억원 또는 M USD,
                        "operating_profit": 억원 또는 M USD,
                        "net_income": 억원 또는 M USD,
                        "oi_margin": %, (None 가능)
                        "yoy_revenue": %,
                        "yoy_op": %,
                        "dart_url": str,
                    }, ...
                ]  # 과거 → 최신 순
            }
        """
        if is_domestic(code):
            return self._get_financials_kr(code, years)
        else:
            return self._get_financials_us(code, min(years, 4))

    def _get_financials_kr(self, code: str, years: int) -> dict:
        multi_rows = fetch_financials_multi_year(code, years)
        result_rows = []
        for i, row in enumerate(multi_rows):
            prev = multi_rows[i - 1] if i > 0 else None
            rev = row["revenue"]
            op = row["operating_income"]
            net = row["net_income"]
            prev_rev = prev["revenue"] if prev else None
            prev_op = prev["operating_income"] if prev else None
            oi_margin = round(op / rev * 100, 1) if rev and op and rev != 0 else None
            result_rows.append({
                "year": row["year"],
                "revenue": _awk(rev),
                "operating_profit": _awk(op),
                "net_income": _awk(net),
                "oi_margin": oi_margin,
                "yoy_revenue": _growth(rev, prev_rev),
                "yoy_op": _growth(op, prev_op),
                "dart_url": row.get("dart_url", ""),
            })
        return {"code": code, "currency": "KRW", "rows": result_rows}

    def _get_financials_us(self, code: str, years: int) -> dict:
        multi_rows = yf_client.fetch_financials_multi_year_yf(code, years)
        result_rows = []
        for i, row in enumerate(multi_rows):
            prev = multi_rows[i - 1] if i > 0 else None
            rev = row["revenue"]
            op = row["operating_income"]
            net = row["net_income"]
            prev_rev = prev["revenue"] if prev else None
            prev_op = prev["operating_income"] if prev else None
            rev_m = _usd_m(rev)
            op_m = _usd_m(op)
            oi_margin = round(op / rev * 100, 1) if rev and op and rev != 0 else None
            result_rows.append({
                "year": row["year"],
                "revenue": rev_m,
                "operating_profit": op_m,
                "net_income": _usd_m(net),
                "oi_margin": oi_margin,
                "yoy_revenue": _growth(rev, prev_rev),
                "yoy_op": _growth(op, prev_op),
                "dart_url": "",
            })
        return {"code": code, "currency": "USD", "rows": result_rows}

    def get_valuation_chart(self, code: str, years: int = 10) -> dict:
        """월별 PER/PBR 히스토리 + 기간 평균 반환.

        해외주식은 히스토리 미지원 → 빈 데이터 반환.
        """
        if not is_domestic(code):
            return {
                "history": [],
                "avg_per": None,
                "avg_pbr": None,
                "note": "해외주식 PER/PBR 히스토리 미지원",
            }

        history = fetch_valuation_history(code, years)

        # 이상치(PER > 500) 제외 후 평균
        pers = [h["per"] for h in history if h.get("per") and h["per"] < 500]
        pbrs = [h["pbr"] for h in history if h.get("pbr")]

        avg_per = round(sum(pers) / len(pers), 1) if pers else None
        avg_pbr = round(sum(pbrs) / len(pbrs), 2) if pbrs else None

        return {
            "history": history,
            "avg_per": avg_per,
            "avg_pbr": avg_pbr,
        }

    def get_report(self, code: str, years: int = 10) -> dict:
        """재무 + 밸류에이션 + 종합 요약 + 기본 시세 통합 반환."""
        if is_domestic(code):
            return self._get_report_kr(code, years)
        else:
            return self._get_report_us(code, min(years, 4))

    def _get_report_kr(self, code: str, years: int) -> dict:
        financials = self.get_financials(code, years)
        valuation = self.get_valuation_chart(code, years)
        detail = fetch_detail(code)

        resolved = symbol_map.resolve(code)
        name = resolved[1] if resolved else code

        basic: dict = {
            "code": code,
            "name": name,
            "currency": "KRW",
            "price": None,
            "change": None,
            "change_pct": None,
            "market_cap": None,
            "per": None,
            "pbr": None,
            "high_52": None,
            "low_52": None,
            "market": None,
            "sector": None,
        }
        if detail:
            mktcap = detail.get("mktcap")
            basic.update({
                "price": detail.get("close"),
                "change": detail.get("change"),
                "change_pct": detail.get("change_pct"),
                "market_cap": _awk(mktcap),
                "per": detail.get("per"),
                "pbr": detail.get("pbr"),
                "high_52": detail.get("high_52"),
                "low_52": detail.get("low_52"),
                "market": detail.get("market_type"),
                "sector": detail.get("sector"),
            })

        return self._build_report(basic, financials, valuation)

    def _get_report_us(self, code: str, years: int) -> dict:
        financials = self.get_financials(code, years)
        valuation = self.get_valuation_chart(code, years)  # 빈 데이터
        detail = yf_client.fetch_detail_yf(code)

        basic: dict = {
            "code": code,
            "name": code,
            "currency": "USD",
            "price": None,
            "change": None,
            "change_pct": None,
            "market_cap": None,
            "per": None,
            "pbr": None,
            "high_52": None,
            "low_52": None,
            "market": None,
            "sector": None,
        }
        if detail:
            mktcap = detail.get("mktcap")
            basic.update({
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
            })

        return self._build_report(basic, financials, valuation)

    def _build_report(self, basic: dict, financials: dict, valuation: dict) -> dict:
        current_per = basic.get("per")
        current_pbr = basic.get("pbr")
        rows = financials["rows"]

        rev_cagr = op_cagr = net_cagr = None
        if len(rows) >= 2:
            n = len(rows) - 1
            first, last = rows[0], rows[-1]
            rev_cagr = _cagr(first["revenue"], last["revenue"], n)
            op_cagr = _cagr(first["operating_profit"], last["operating_profit"], n)
            net_cagr = _cagr(first["net_income"], last["net_income"], n)

        avg_per = valuation.get("avg_per")
        avg_pbr = valuation.get("avg_pbr")

        per_vs_avg = (
            round((current_per - avg_per) / avg_per * 100, 1)
            if current_per and avg_per
            else None
        )
        pbr_vs_avg = (
            round((current_pbr - avg_pbr) / avg_pbr * 100, 1)
            if current_pbr and avg_pbr
            else None
        )

        return {
            "basic": basic,
            "financials": financials,
            "valuation": valuation,
            "summary": {
                "rev_cagr": rev_cagr,
                "op_cagr": op_cagr,
                "net_cagr": net_cagr,
                "current_per": current_per,
                "current_pbr": current_pbr,
                "avg_per": avg_per,
                "avg_pbr": avg_pbr,
                "per_vs_avg": per_vs_avg,
                "pbr_vs_avg": pbr_vs_avg,
                "years": len(rows),
                "year_start": rows[0]["year"] if rows else None,
                "year_end": rows[-1]["year"] if rows else None,
            },
        }
