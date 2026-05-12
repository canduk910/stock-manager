"""수급정보 서비스 — 시장 + 종목 일별 투자자 매매동향.

REQ-SUPPLY-MACRO-01 / REQ-SUPPLY-STOCK-01 / REQ-SUPPLY-CACHE-01 구현.

설계:
- wrapper.py 의 get_market_investor_daily / get_stock_investor_daily 위임
- 단위 변환: 백만원(KIS 원본) → 억원(÷100, 반올림)
- 누적합(cumulative): 기간 시작일 0 기준
- 색상 표준: 개인 #EF4444 / 외국인 #3B82F6 / 기관 #10B981
- 영속 캐시: macro_store.get_today / save_today (KST 일자 기반)
  카테고리 키: supply_demand:market:{kospi|kosdaq} / supply_demand:stock:{code}
- 예외 매핑: ServiceError(400) / NotFoundError(404) / ConfigError(503) / ExternalAPIError(502)
- 매매 액션 키 금지(OrderAdvisor 자문): recommendation/action/buy_signal 등 포함 안 함

도메인 자문 결과 (요건서 명시):
- MacroSentinel: 억원/20일/Graham 보조지표
- OrderAdvisor: V1 표시만, advisory_note 고지, 단독 시그널 금지
"""
from __future__ import annotations

import datetime as _dt
from typing import Any

from config import KIS_APP_KEY, KIS_APP_SECRET
from services.exceptions import (
    ConfigError, ExternalAPIError, NotFoundError, ServiceError,
)
from stock import macro_store
from stock.utils import is_domestic
from wrapper import get_market_investor_daily, get_stock_investor_daily

# ── 상수 ──────────────────────────────────────────────────────────────────────

_COLOR_MAP: dict[str, str] = {
    "personal": "#EF4444",
    "foreign": "#3B82F6",
    "institution": "#10B981",
}

_VALID_MARKETS = {"kospi", "kosdaq"}

_DAYS_MIN, _DAYS_MAX = 10, 60

_ADVISORY_NOTE = (
    "참고용 데이터입니다. 매매 신호로 단독 사용 금지(Graham 원칙)."
)

# 기관 11종 detail 키 매핑(서비스 응답용 키 → wrapper 응답 키)
_INSTITUTION_DETAIL_MAP: list[tuple[str, str]] = [
    ("securities", "securities_net_amt"),
    ("inv_trust", "inv_trust_net_amt"),
    ("private_fund", "private_fund_net_amt"),
    ("bank", "bank_net_amt"),
    ("insurance", "insurance_net_amt"),
    ("mrbn", "mrbn_net_amt"),
    ("pension", "pension_net_amt"),
    ("etc_finance", "etc_finance_net_amt"),
    ("etc_corp", "etc_corp_net_amt"),
    ("etc_org", "etc_org_net_amt"),
]


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _to_eok(amount_million: Any) -> int:
    """백만원 → 억원 (÷100, 반올림). None/빈문자 → 0."""
    if amount_million is None:
        return 0
    try:
        return int(round(float(amount_million) / 100.0))
    except (TypeError, ValueError):
        return 0


def _ensure_kis_keys() -> None:
    """KIS 키 미설정 시 ConfigError(503) — 라우터에서 503 안내 카드."""
    if not KIS_APP_KEY or not KIS_APP_SECRET:
        raise ConfigError("KIS API 키 설정이 필요합니다.")


def _as_of(rows: list[dict]) -> str:
    """daily 마지막 일자 또는 오늘 KST."""
    if rows:
        return rows[-1].get("date", "")
    return _dt.datetime.now().strftime("%Y-%m-%d")


def _build_daily_market(raw_row: dict) -> dict:
    """wrapper 시장 row(백만원) → 서비스 응답 daily 한 행(억원)."""
    return {
        "date": raw_row["date"],
        "index_close": raw_row.get("index_close", 0.0),
        "personal_net": _to_eok(raw_row.get("personal_net_amt")),
        "foreign_net": _to_eok(raw_row.get("foreign_net_amt")),
        "institution_net": _to_eok(raw_row.get("institution_net_amt")),
        "institution_detail": {
            out_key: _to_eok(raw_row.get(src_key))
            for out_key, src_key in _INSTITUTION_DETAIL_MAP
        },
    }


def _build_daily_stock(raw_row: dict) -> dict:
    """wrapper 종목 row(백만원) → 서비스 응답 daily 한 행(억원)."""
    return {
        "date": raw_row["date"],
        "close": raw_row.get("close_price", 0),
        "personal_net": _to_eok(raw_row.get("personal_net_amt")),
        "personal_buy": _to_eok(raw_row.get("personal_buy_amt")),
        "personal_sell": _to_eok(raw_row.get("personal_sell_amt")),
        "foreign_net": _to_eok(raw_row.get("foreign_net_amt")),
        "foreign_buy": _to_eok(raw_row.get("foreign_buy_amt")),
        "foreign_sell": _to_eok(raw_row.get("foreign_sell_amt")),
        "institution_net": _to_eok(raw_row.get("institution_net_amt")),
        "institution_buy": _to_eok(raw_row.get("institution_buy_amt")),
        "institution_sell": _to_eok(raw_row.get("institution_sell_amt")),
        "institution_detail": {
            out_key: _to_eok(raw_row.get(src_key))
            for out_key, src_key in _INSTITUTION_DETAIL_MAP
        },
    }


def _build_cumulative(daily: list[dict]) -> list[dict]:
    """daily 배열 → 누적합 배열(1:1 매칭)."""
    cum_p, cum_f, cum_i = 0, 0, 0
    out: list[dict] = []
    for d in daily:
        cum_p += d["personal_net"]
        cum_f += d["foreign_net"]
        cum_i += d["institution_net"]
        out.append({
            "date": d["date"],
            "personal_cum": cum_p,
            "foreign_cum": cum_f,
            "institution_cum": cum_i,
        })
    return out


def _build_summary(daily: list[dict], cumulative: list[dict]) -> dict:
    """오늘(가장 최근 일자) 기준 요약."""
    if not daily:
        return {
            "personal_today": 0, "foreign_today": 0, "institution_today": 0,
            "personal_cum_total": 0, "foreign_cum_total": 0, "institution_cum_total": 0,
        }
    last_d = daily[-1]
    last_c = cumulative[-1]
    return {
        "personal_today": last_d["personal_net"],
        "foreign_today": last_d["foreign_net"],
        "institution_today": last_d["institution_net"],
        "personal_cum_total": last_c["personal_cum"],
        "foreign_cum_total": last_c["foreign_cum"],
        "institution_cum_total": last_c["institution_cum"],
    }


# ── 캐시 ──────────────────────────────────────────────────────────────────────

def _cache_get(category: str) -> list[dict] | None:
    """macro_store에서 영속 캐시 조회. 표준화된 wrapper 결과(list[dict])를 그대로 저장/반환.

    영속 캐시 적중: 같은 KST 일자라면 hit. 일자 경계는 macro_store가 처리(today=KST).
    장중 in-memory 10분 TTL은 V2(현 V1은 macro_store만으로도 부분 실패 정책 만족).
    """
    try:
        return macro_store.get_today(category)
    except Exception:
        return None


def _cache_save(category: str, rows: list[dict]) -> None:
    try:
        macro_store.save_today(category, rows)
    except Exception:
        # 캐시 저장 실패는 응답에 영향 없음
        pass


def _cache_invalidate(category: str) -> None:
    """영속된 결함 데이터를 즉시 폐기. 실패는 무시."""
    try:
        macro_store.delete_today(category)
    except Exception:
        pass


# ── 결함 응답 가드 ────────────────────────────────────────────────────────────

def _is_all_zero_net(rows: list[dict]) -> bool:
    """전 행 personal/foreign/institution net_amt가 모두 0이면 True.

    회귀 가드(2026-05-12 결함 재발 방지):
    wrapper의 KIS 파라미터 결함 등으로 KIS가 zero-row를 반환할 때, 그 결과가
    영속 캐시에 저장되어 일자 경계까지 굳어버린 사례가 있었음. 이 헬퍼는
    캐시 저장 거부 + 영속된 결함 자동 폐기의 기준으로 사용된다.

    빈 응답(`rows=[]`)은 False (신규 상장 등 별도 분기에서 처리).
    일부 행만 0인 경우(휴장일 등)는 False — 정상 데이터로 간주.
    """
    if not rows:
        return False
    for r in rows:
        if (_to_eok(r.get("personal_net_amt")) != 0 or
            _to_eok(r.get("foreign_net_amt")) != 0 or
            _to_eok(r.get("institution_net_amt")) != 0):
            return False
    return True


def _fetch_or_cache(category: str, fetch_fn) -> list[dict]:
    """캐시-우선 fetch + zero-row 가드.

    1) 캐시 hit + 정상 → 그대로 반환
    2) 캐시 hit + 전 행 zero-row → 결함 영속 → 폐기 후 wrapper 재호출
    3) 캐시 miss → wrapper 호출
    4) wrapper 결과 전 행 zero-row → 캐시 저장 거부 + ExternalAPIError로 표면화
       (다음 호출 시 자동 복구 시도; UI는 부분 실패 안내 카드 노출)
    """
    cached = _cache_get(category)
    if cached is not None:
        if not _is_all_zero_net(cached):
            return cached
        _cache_invalidate(category)

    raw_rows = fetch_fn()
    if _is_all_zero_net(raw_rows):
        raise ExternalAPIError(
            "KIS 수급 응답이 비정상입니다(모든 net_amt=0). 잠시 후 다시 시도하세요."
        )
    _cache_save(category, raw_rows)
    return raw_rows


# ── 공개 API ─────────────────────────────────────────────────────────────────

def fetch_market_supply_demand(market: str, days: int = 20) -> dict:
    """시장(코스피/코스닥) 일별 수급 + 누적.

    Args:
        market: "kospi" | "kosdaq" (소문자).
        days: 10~60. 외 범위 → ServiceError(400).

    Returns:
        REQ-SUPPLY-MACRO-01 응답 dict.
    """
    if market not in _VALID_MARKETS:
        raise ServiceError(
            f"market은 'kospi' 또는 'kosdaq'이어야 합니다: {market!r}"
        )
    if not isinstance(days, int) or days < _DAYS_MIN or days > _DAYS_MAX:
        raise ServiceError(
            f"days는 {_DAYS_MIN}~{_DAYS_MAX} 범위여야 합니다: {days!r}"
        )
    _ensure_kis_keys()

    category = f"supply_demand:market:{market}"
    market_code = "U001" if market == "kospi" else "U201"

    def _fetch() -> list[dict]:
        try:
            return get_market_investor_daily(market_code, days=_DAYS_MAX)
        except ValueError as exc:
            raise ServiceError(str(exc))

    raw_rows = _fetch_or_cache(category, _fetch)

    # 요청 days 만큼 슬라이싱 (최근 days개)
    rows = raw_rows[-days:] if len(raw_rows) > days else raw_rows
    daily = [_build_daily_market(r) for r in rows]
    cumulative = _build_cumulative(daily)
    summary = _build_summary(daily, cumulative)

    return {
        "market": market,
        "days": days,
        "as_of": _as_of(daily),
        "color_map": dict(_COLOR_MAP),
        "daily": daily,
        "cumulative": cumulative,
        "summary": summary,
    }


def fetch_stock_supply_demand(code: str, days: int = 30) -> dict:
    """종목 일별 수급 + 누적 + 매수/매도 분리.

    Args:
        code: 6자리 숫자(국내 종목만 지원).
        days: 10~60.

    Returns:
        REQ-SUPPLY-STOCK-01 응답 dict (advisory_note 포함).
    """
    if not is_domestic(code):
        raise ServiceError("국내 종목만 지원합니다.")
    if not isinstance(days, int) or days < _DAYS_MIN or days > _DAYS_MAX:
        raise ServiceError(
            f"days는 {_DAYS_MIN}~{_DAYS_MAX} 범위여야 합니다: {days!r}"
        )
    _ensure_kis_keys()

    category = f"supply_demand:stock:{code}"

    def _fetch() -> list[dict]:
        try:
            return get_stock_investor_daily(code, days=_DAYS_MAX)
        except ValueError as exc:
            raise ServiceError(str(exc))

    raw_rows = _fetch_or_cache(category, _fetch)

    if not raw_rows:
        # 미존재 종목: KIS는 빈 output2로 응답할 수 있음
        raise NotFoundError(f"종목 {code} 수급 데이터를 찾을 수 없습니다.")

    rows = raw_rows[-days:] if len(raw_rows) > days else raw_rows
    daily = [_build_daily_stock(r) for r in rows]
    cumulative = _build_cumulative(daily)
    summary = _build_summary(daily, cumulative)

    # 종목명은 advisory_store/symbol_map에서 lazy 조회 (실패해도 code 폴백)
    name = code
    try:
        from stock.symbol_map import code_to_name
        name = code_to_name(code) or code
    except Exception:
        name = code

    return {
        "code": code,
        "name": name,
        "days": days,
        "as_of": _as_of(daily),
        "color_map": dict(_COLOR_MAP),
        "advisory_note": _ADVISORY_NOTE,
        "daily": daily,
        "cumulative": cumulative,
        "summary": summary,
    }
