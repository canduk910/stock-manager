"""종목 상세 분석 서비스 레이어.

10년 재무, 월별 밸류에이션 히스토리, 종합 리포트를 제공한다.
해외주식(yfinance)도 지원한다.

2026-05-12: get_bundle() 신규 — DetailPage 마운트 시 N+1 호출 패턴을 단일 호출로 축약.
ThreadPoolExecutor 병렬 수집 + 부분 실패 보존(partial_failure 리스트).
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import logging

from services.exceptions import ExternalAPIError
from stock import symbol_map
from stock.dart_fin import fetch_financials_multi_year
from stock.market import fetch_detail, fetch_valuation_history, fetch_market_metrics
from stock.utils import is_domestic
import stock.yf_client as yf_client

logger = logging.getLogger(__name__)


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
        try:
            if is_domestic(code):
                return self._get_financials_kr(code, years)
            else:
                return self._get_financials_us(code, min(years, 4))
        except RuntimeError as e:
            raise ExternalAPIError(str(e))

    def _get_financials_kr(self, code: str, years: int) -> dict:
        multi_rows = fetch_financials_multi_year(code, years)
        result_rows = []
        # REQ-SECTOR-03 (2026-05-16): sector_tier 응답 노출 (dart_fin 결과 통과)
        sector_tier = "general"
        for i, row in enumerate(multi_rows):
            prev = multi_rows[i - 1] if i > 0 else None
            rev = row["revenue"]
            op = row["operating_income"]
            net = row["net_income"]
            prev_rev = prev["revenue"] if prev else None
            prev_op = prev["operating_income"] if prev else None
            oi_margin = round(op / rev * 100, 1) if rev and op and rev != 0 else None
            # 최초 row에서 sector_tier 추출 (모든 row 동일값)
            row_tier = row.get("sector_tier")
            if row_tier and sector_tier == "general":
                sector_tier = row_tier
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
        return {"code": code, "currency": "KRW", "rows": result_rows, "sector_tier": sector_tier}

    def _get_financials_us(self, code: str, years: int) -> dict:
        # REQ-SECTOR-03: US는 항상 general (한국 금융지주 분류 미적용)
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
        return {"code": code, "currency": "USD", "rows": result_rows, "sector_tier": "general"}

    def get_valuation_chart(self, code: str, years: int = 10) -> dict:
        """월별 PER/PBR 히스토리 + 기간 평균 반환.

        해외주식: 분기 EPS/BPS + 일별 주가 조합으로 추정 히스토리 산출.
        """
        try:
            return self._get_valuation_chart_inner(code, years)
        except RuntimeError as e:
            raise ExternalAPIError(str(e))

    def _get_valuation_chart_inner(self, code: str, years: int = 10) -> dict:
        if not is_domestic(code):
            history = yf_client.fetch_valuation_history_yf(code, min(years, 5))
            pers = [h["per"] for h in history if h.get("per") and 0 < h["per"] < 500]
            pbrs = [h["pbr"] for h in history if h.get("pbr") and h["pbr"] > 0]
            avg_per = round(sum(pers) / len(pers), 1) if pers else None
            avg_pbr = round(sum(pbrs) / len(pbrs), 2) if pbrs else None
            return {
                "history": history,
                "avg_per": avg_per,
                "avg_pbr": avg_pbr,
                "note": "분기 EPS/BPS + 일별 주가 추정" if history else None,
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
        try:
            if is_domestic(code):
                return self._get_report_kr(code, years)
            else:
                return self._get_report_us(code, min(years, 4))
        except RuntimeError as e:
            raise ExternalAPIError(str(e))

    def _get_report_kr(self, code: str, years: int) -> dict:
        financials = self.get_financials(code, years)
        valuation = self.get_valuation_chart(code, years)
        detail = fetch_detail(code)
        forward = yf_client.fetch_forward_estimates_yf(code, is_kr=True)

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
            "roe": None,
            "dividend_yield": None,
            "dividend_per_share": None,
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
        try:
            metrics = fetch_market_metrics(code)
            basic["roe"] = metrics.get("roe")
            basic["dividend_yield"] = metrics.get("dividend_yield")
            basic["dividend_per_share"] = metrics.get("dividend_per_share")
            # PBR/PER fallback: fetch_detail()에서 None이면 metrics에서 보충
            if basic["pbr"] is None and metrics.get("pbr"):
                basic["pbr"] = metrics["pbr"]
            if basic["per"] is None and metrics.get("per"):
                basic["per"] = metrics["per"]
        except Exception:
            pass

        return self._build_report(basic, financials, valuation, forward)

    def _get_report_us(self, code: str, years: int) -> dict:
        financials = self.get_financials(code, years)
        valuation = self.get_valuation_chart(code, years)  # 빈 데이터
        detail = yf_client.fetch_detail_yf(code)
        forward = yf_client.fetch_forward_estimates_yf(code, is_kr=False)

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
            "roe": None,
            "dividend_yield": None,
            "dividend_per_share": None,
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
                "roe": detail.get("roe"),
                "dividend_yield": detail.get("dividend_yield"),
                "dividend_per_share": detail.get("dividend_per_share"),
                "high_52": detail.get("high_52"),
                "low_52": detail.get("low_52"),
                "market": detail.get("market_type"),
                "sector": detail.get("sector"),
            })

        return self._build_report(basic, financials, valuation, forward)

    def get_bundle(self, code: str, market: str = "auto", years: int = 10) -> dict:
        """DetailPage 마운트용 통합 응답. ThreadPoolExecutor 병렬 수집 + 부분 실패 보존.

        2026-05-12: 프론트 N+1 호출 패턴 제거 — 재무/밸류에이션/기본시세/예상실적/심볼맵을 동시 수집.
        각 섹션 실패 시 해당 키는 None + partial_failure 리스트에 섹션명 기록 (200 응답 보존).

        market='auto' (기본): is_domestic(code) 자동 판별. 'KR'/'US' 명시도 허용.
        """
        # 시장 판별
        is_kr = is_domestic(code) if market == "auto" else (market.upper() == "KR")
        eff_years = years if is_kr else min(years, 4)

        partial_failure: list[str] = []
        results: dict = {
            "financials": None,
            "valuation": None,
            "detail": None,
            "metrics": None,
            "forward": None,
            "name": code,
        }

        def _safe_fin():
            try:
                return self.get_financials(code, eff_years)
            except Exception as e:
                logger.warning("[bundle] financials 실패 %s: %s", code, e)
                partial_failure.append("financials")
                return None

        def _safe_val():
            try:
                return self.get_valuation_chart(code, eff_years)
            except Exception as e:
                logger.warning("[bundle] valuation 실패 %s: %s", code, e)
                partial_failure.append("valuation")
                return None

        def _safe_detail():
            try:
                if is_kr:
                    return fetch_detail(code)
                return yf_client.fetch_detail_yf(code)
            except Exception as e:
                logger.warning("[bundle] detail 실패 %s: %s", code, e)
                partial_failure.append("detail")
                return None

        def _safe_metrics():
            if not is_kr:
                return None  # US는 detail에 다 포함 (별도 호출 없음)
            try:
                return fetch_market_metrics(code)
            except Exception as e:
                logger.warning("[bundle] metrics 실패 %s: %s", code, e)
                partial_failure.append("metrics")
                return None

        def _safe_forward():
            try:
                return yf_client.fetch_forward_estimates_yf(code, is_kr=is_kr)
            except Exception as e:
                logger.warning("[bundle] forward 실패 %s: %s", code, e)
                partial_failure.append("forward_estimates")
                return None

        def _safe_name():
            if not is_kr:
                return code  # US는 detail에서 가져옴
            try:
                resolved = symbol_map.resolve(code)
                return resolved[1] if resolved else code
            except Exception:
                return code

        # ThreadPoolExecutor 병렬 — t3.small 보호 max_workers=4
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                "financials": executor.submit(_safe_fin),
                "valuation": executor.submit(_safe_val),
                "detail": executor.submit(_safe_detail),
                "metrics": executor.submit(_safe_metrics),
                "forward": executor.submit(_safe_forward),
                "name": executor.submit(_safe_name),
            }
            for key, fut in futures.items():
                try:
                    results[key] = fut.result()
                except Exception as e:
                    logger.warning("[bundle] %s future 실패 %s: %s", key, code, e)
                    if key not in partial_failure:
                        partial_failure.append(key)

        # basic 구성 — 기존 _get_report_kr/_get_report_us와 동일 shape
        basic: dict = {
            "code": code,
            "name": results["name"],
            "currency": "KRW" if is_kr else "USD",
            "price": None,
            "change": None,
            "change_pct": None,
            "market_cap": None,
            "per": None,
            "pbr": None,
            "roe": None,
            "dividend_yield": None,
            "dividend_per_share": None,
            "high_52": None,
            "low_52": None,
            "market": None,
            "sector": None,
        }
        detail = results["detail"]
        if detail:
            mktcap = detail.get("mktcap")
            basic.update({
                "price": detail.get("close"),
                "change": detail.get("change"),
                "change_pct": detail.get("change_pct"),
                "market_cap": _awk(mktcap) if is_kr else _usd_m(mktcap),
                "per": detail.get("per"),
                "pbr": detail.get("pbr"),
                "high_52": detail.get("high_52"),
                "low_52": detail.get("low_52"),
                "market": detail.get("market_type"),
                "sector": detail.get("sector"),
            })
            if not is_kr:
                # US는 detail에 name/roe/dividend 포함
                basic["name"] = detail.get("name", code)
                basic["roe"] = detail.get("roe")
                basic["dividend_yield"] = detail.get("dividend_yield")
                basic["dividend_per_share"] = detail.get("dividend_per_share")

        # KR metrics 보충 (PER/PBR/ROE fallback)
        metrics = results["metrics"]
        if metrics:
            basic["roe"] = metrics.get("roe", basic.get("roe"))
            basic["dividend_yield"] = metrics.get("dividend_yield", basic.get("dividend_yield"))
            basic["dividend_per_share"] = metrics.get(
                "dividend_per_share", basic.get("dividend_per_share"),
            )
            if basic["pbr"] is None and metrics.get("pbr"):
                basic["pbr"] = metrics["pbr"]
            if basic["per"] is None and metrics.get("per"):
                basic["per"] = metrics["per"]

        # _build_report 와 동일 summary 산출
        financials = results["financials"] or {"code": code, "currency": "KRW" if is_kr else "USD", "rows": []}
        valuation = results["valuation"] or {"history": [], "avg_per": None, "avg_pbr": None}
        forward = results["forward"] or {}

        bundle = self._build_report(basic, financials, valuation, forward)
        bundle["partial_failure"] = partial_failure
        return bundle

    def _build_report(self, basic: dict, financials: dict, valuation: dict, forward: dict = None) -> dict:
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
            "forward_estimates": forward or {},
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
