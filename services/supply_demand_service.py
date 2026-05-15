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
from wrapper import (
    get_market_investor_daily,
    get_stock_investor_daily,
    get_foreign_holding_snapshot as wrapper_get_foreign_holding_snapshot,
    get_foreign_holding_daily as wrapper_get_foreign_holding_daily,
)

# ── 상수 ──────────────────────────────────────────────────────────────────────

_COLOR_MAP: dict[str, str] = {
    "personal": "#EF4444",
    "foreign": "#3B82F6",
    "institution": "#10B981",
}

_VALID_MARKETS = {"kospi", "kosdaq"}

_DAYS_MIN, _DAYS_MAX = 10, 60

_ADVISORY_NOTE = (
    "참고용 데이터입니다. 한도소진율과 개인 투자자 매수 적합성은 무관합니다(외국인 합산 한도). "
    "매매 신호로 단독 사용 금지(Graham 원칙)."
)

# ── REQ-FH 외국인 보유 ────────────────────────────────────────────────────────

_FH_COLOR_MAP: dict[str, str] = {
    "foreign": "#3B82F6",   # V1 컨벤션 계승
    "limit": "#9CA3AF",     # 한도 라인 회색 점선
}

# V1.5: KIS TR 자체 30일 한도. V1.6: 라우터/서비스 범위 180일로 확장(누적 캐시 머지).
_FH_DAYS_MIN, _FH_DAYS_MAX = 5, 180

# KIS API 자체 한도(누적 머지용 fetch 일수). 변경 시 wrapper TR_ID 한도 재검토 필요.
_FH_KIS_FETCH_DAYS = 30

# REQ-FH-EXT-STORE-01: 누적 보존 상한(거래일). 도메인팀장 권장값 (A).
_FH_HISTORY_MAX_KEEP = 250

# REQ-FH-EXT-SERVICE-01: change_alert 임계값(%p). 부서장 결정 권장 (A).
_FH_CHANGE_ALERT_THRESHOLD = 3.0

_FH_EHRT_UNLIMITED_THRESHOLD = 0.01  # 한도 미설정 종목 컷오프 (%)

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


# ── REQ-FH-SERVICE-01: 외국인 보유 추이 + 매수여력 ───────────────────────────

def _classify_limit_status(ehrt: float | None) -> str:
    """soin율(%) → 4단계 + unlimited.

    safe(<50) / caution(50~80) / warning(80~95) / saturated(≥95) / unlimited.
    exceeded는 별도(보유 > 한도)에서 결정.
    """
    if ehrt is None or ehrt < _FH_EHRT_UNLIMITED_THRESHOLD:
        return "unlimited"
    if ehrt < 50.0:
        return "safe"
    if ehrt < 80.0:
        return "caution"
    if ehrt < 95.0:
        return "warning"
    return "saturated"


def _is_defective_fh_snapshot(snap: dict) -> bool:
    """frgn_hldn_qty AND hts_frgn_ehrt 둘 다 None → 결함 응답."""
    return snap.get("frgn_hldn_qty") is None and snap.get("hts_frgn_ehrt") is None


def _is_defective_fh_daily(rows: list[dict]) -> bool:
    """전 row의 hts_frgn_ehrt가 None → 결함 응답."""
    if not rows:
        return False
    return all(r.get("hts_frgn_ehrt") is None for r in rows)


def _fetch_or_cache_fh(category: str, fetch_fn, defective_check) -> object:
    """외국인 보유 데이터 캐시-우선 fetch + 결함 가드 (V1 _fetch_or_cache 차용).

    1) 캐시 hit + 정상 → 그대로 반환
    2) 캐시 hit + 결함 → 폐기 + wrapper 재호출
    3) 캐시 miss → wrapper 호출
    4) 결과 결함 → 캐시 저장 거부 + ExternalAPIError
    """
    cached = _cache_get(category)
    if cached is not None:
        if not defective_check(cached):
            return cached
        _cache_invalidate(category)

    fresh = fetch_fn()
    if defective_check(fresh):
        raise ExternalAPIError(
            "KIS 외국인 보유 응답이 비정상입니다(필수 필드 누락). 잠시 후 다시 시도하세요."
        )
    _cache_save(category, fresh)
    return fresh


def _build_fh_snapshot(snap: dict) -> dict:
    """wrapper 스냅샷(주 단위) → 응답 snapshot(만주 단위) + limit_status 계산."""
    lstn = snap.get("lstn_stcn") or 0
    frgn_qty = snap.get("frgn_hldn_qty")
    ehrt = snap.get("hts_frgn_ehrt")

    lstn_man = int(round(lstn / 10000.0)) if lstn else 0
    frgn_man = int(round(frgn_qty / 10000.0)) if frgn_qty else 0

    is_unlimited = (ehrt is None or ehrt < _FH_EHRT_UNLIMITED_THRESHOLD)

    if is_unlimited or not frgn_qty:
        frgn_limit_man = None
        is_limit_unset = True
    else:
        # 한도수량 = frgn_hldn_qty / (ehrt/100) ÷ 10000 (반올림)
        try:
            frgn_limit_qty = frgn_qty / (ehrt / 100.0)
            frgn_limit_man = int(round(frgn_limit_qty / 10000.0))
            is_limit_unset = False
        except (ZeroDivisionError, TypeError):
            frgn_limit_man = None
            is_limit_unset = True

    # 보유율(상장 대비)
    if lstn > 0 and frgn_qty:
        frgn_holding_pct = round((frgn_qty / lstn) * 100.0, 2)
    else:
        frgn_holding_pct = None

    frgn_ehrt_pct = round(ehrt, 2) if ehrt is not None else None

    # 잔여 매수여력 + exceeded 판정
    is_exceeded = False
    if frgn_limit_man is None:
        frgn_remaining_man = None
        frgn_remaining_pct_of_limit = None
    else:
        diff = frgn_limit_man - frgn_man
        if diff < 0:
            is_exceeded = True
            frgn_remaining_man = 0
            frgn_remaining_pct_of_limit = 0.0
        else:
            frgn_remaining_man = diff
            if frgn_limit_man > 0:
                frgn_remaining_pct_of_limit = round(
                    (diff / frgn_limit_man) * 100.0, 2
                )
            else:
                frgn_remaining_pct_of_limit = None

    # 상태 결정 (exceeded 우선)
    if is_exceeded:
        limit_status = "exceeded"
    else:
        limit_status = _classify_limit_status(ehrt)

    return {
        "lstn_stcn_man": lstn_man,
        "frgn_hldn_man": frgn_man,
        "frgn_holding_pct": frgn_holding_pct,
        "frgn_ehrt_pct": frgn_ehrt_pct,
        "frgn_limit_man": frgn_limit_man,
        "frgn_remaining_man": frgn_remaining_man,
        "frgn_remaining_pct_of_limit": frgn_remaining_pct_of_limit,
        "limit_status": limit_status,
        "is_limit_unset": is_limit_unset,
        "is_exceeded": is_exceeded,
    }


def _build_fh_daily(raw_rows: list[dict], frgn_limit_man: int | None) -> list[dict]:
    """wrapper 일별 시계열 → 응답 daily.

    frgn_hldn_man_estimated = frgn_limit_man × (ehrt/100). 한도 미설정 시 None.
    """
    out: list[dict] = []
    for r in raw_rows:
        ehrt = r.get("hts_frgn_ehrt")
        if frgn_limit_man is None or ehrt is None:
            est = None
        else:
            try:
                est = int(round(frgn_limit_man * (ehrt / 100.0)))
            except (TypeError, ValueError):
                est = None
        out.append({
            "date": r.get("date"),
            "close": r.get("close"),
            "frgn_ehrt_pct": round(ehrt, 2) if ehrt is not None else None,
            "frgn_ntby_qty": r.get("frgn_ntby_qty", 0),
            "frgn_hldn_man_estimated": est,
        })
    return out


def _merge_fh_daily(
    existing: list[dict],
    new_rows: list[dict],
    max_keep: int = _FH_HISTORY_MAX_KEEP,
) -> list[dict]:
    """REQ-FH-EXT-STORE-01: 외국인 보유 누적 일별 시계열 머지 헬퍼.

    - existing + new_rows → date 기준 dict-merge (last-write-wins)
    - ascending sort by date
    - max_keep(기본 250) 초과 시 FIFO 가장 오래된 row 제거
    - new_rows 중 hts_frgn_ehrt is None row는 결합에서 제외 (영속 결함 데이터 차단)
    - existing의 None row는 보존 (retroactive 제외 X — UI/service 단에서 필터)

    Args:
        existing: 누적 저장된 row 리스트. None ehrt row 보존.
        new_rows: 신규 KIS row 리스트. hts_frgn_ehrt None인 row는 결합 거부.
        max_keep: 누적 보존 상한(거래일).

    Returns:
        date ascending sorted, cap 적용된 list[dict].
    """
    merged: dict[str, dict] = {}
    # existing 우선 적재
    for r in existing or []:
        d = r.get("date")
        if not d:
            continue
        merged[d] = r
    # new_rows로 덮어쓰기 (단, None ehrt는 거부)
    for r in new_rows or []:
        if r.get("hts_frgn_ehrt") is None:
            continue
        d = r.get("date")
        if not d:
            continue
        merged[d] = r

    sorted_rows = sorted(merged.values(), key=lambda x: x["date"])
    if max_keep > 0 and len(sorted_rows) > max_keep:
        sorted_rows = sorted_rows[-max_keep:]
    return sorted_rows


def _build_change_alert(daily_slice: list[dict]) -> dict | None:
    """REQ-FH-EXT-SERVICE-01: daily 슬라이스 양 끝 ehrt 차이로 change_alert 객체 생성.

    Args:
        daily_slice: 요청 days만큼 슬라이스된 서비스 응답용 daily (frgn_ehrt_pct 키).

    Returns:
        dict 또는 None.
        None인 경우: row<2 또는 첫/끝 ehrt 중 None 존재.
    """
    if not daily_slice or len(daily_slice) < 2:
        return None
    first = daily_slice[0]
    last = daily_slice[-1]
    first_e = first.get("frgn_ehrt_pct")
    last_e = last.get("frgn_ehrt_pct")
    if first_e is None or last_e is None:
        return None
    signed = round(last_e - first_e, 2)
    absolute = round(abs(signed), 2)
    breached = absolute >= _FH_CHANGE_ALERT_THRESHOLD
    return {
        "first_date": first.get("date"),
        "first_ehrt_pct": round(first_e, 2),
        "last_date": last.get("date"),
        "last_ehrt_pct": round(last_e, 2),
        "abs_change_pct_point": absolute,
        "signed_change_pct_point": signed,
        "threshold_pct_point": _FH_CHANGE_ALERT_THRESHOLD,
        "breached": breached,
        "color": "warning" if breached else "neutral",
    }


def fetch_foreign_holding(code: str, days: int = 120) -> dict:
    """외국인 보유 추이 + 매수여력 (snapshot + daily 시계열).

    REQ-FH-SERVICE-01 + REQ-FH-EXT-SERVICE-01.

    V1.6 확장:
        - days 기본값 30 → 120, 범위 5~180
        - 누적 캐시 `foreign_holding:daily_history:{code}` 머지 (FIFO 250)
        - 응답에 daily_history_total_days + change_alert (±3%p) 추가

    Args:
        code: 6자리 숫자 (국내 종목만).
        days: 5~180. 기본 120.

    Returns:
        REQ-FH-EXT-SERVICE-01 응답 dict.

    Raises:
        ServiceError: 해외 종목 또는 days 범위 외.
        ConfigError: KIS 키 미설정.
        NotFoundError: 종목 미존재.
        ExternalAPIError: KIS 오류 또는 결함 응답.
    """
    if not is_domestic(code):
        raise ServiceError("국내 종목만 지원합니다.")
    if not isinstance(days, int) or days < _FH_DAYS_MIN or days > _FH_DAYS_MAX:
        raise ServiceError(
            f"days는 {_FH_DAYS_MIN}~{_FH_DAYS_MAX} 범위여야 합니다: {days!r}"
        )
    _ensure_kis_keys()

    snap_category = f"foreign_holding:snapshot:{code}"
    daily_category = f"foreign_holding:daily:{code}"
    history_category = f"foreign_holding:daily_history:{code}"

    def _fetch_snap() -> dict:
        try:
            return wrapper_get_foreign_holding_snapshot(code)
        except ValueError as exc:
            raise ServiceError(str(exc))

    def _fetch_daily() -> list[dict]:
        try:
            return wrapper_get_foreign_holding_daily(code, days=_FH_KIS_FETCH_DAYS)
        except ValueError as exc:
            raise ServiceError(str(exc))

    # snapshot은 V1.5와 동일 (단일 일자 캐시)
    snap_raw = _fetch_or_cache_fh(snap_category, _fetch_snap, _is_defective_fh_snapshot)
    # KIS 30일 fetch (V1.5 daily 캐시 호환 유지)
    daily_raw = _fetch_or_cache_fh(daily_category, _fetch_daily, _is_defective_fh_daily)

    # 누적 캐시 조회 + 머지 + 영속 (Lazy 백필)
    existing_history = _cache_get(history_category) or []
    merged_history = _merge_fh_daily(existing_history, daily_raw,
                                     max_keep=_FH_HISTORY_MAX_KEEP)
    if merged_history:
        _cache_save(history_category, merged_history)

    daily_history_total_days = len(merged_history)

    snapshot = _build_fh_snapshot(snap_raw)

    # 요청 days 만큼 슬라이싱 (누적 데이터 끝에서 N일)
    sliced_history = merged_history[-days:] if len(merged_history) > days else merged_history
    # 누적 row에 None ehrt가 포함되어 있다면 UI 차트 단절 방지 위해 daily 응답에서 제외
    sliced_clean = [r for r in sliced_history if r.get("hts_frgn_ehrt") is not None]
    daily = _build_fh_daily(sliced_clean, snapshot["frgn_limit_man"])

    # change_alert 생성 (응답 daily 양 끝 기준)
    change_alert = _build_change_alert(daily)

    # 종목명 lazy
    name = code
    try:
        from stock.symbol_map import code_to_name
        name = code_to_name(code) or code
    except Exception:
        name = code

    as_of_date = snap_raw.get("as_of_date") or (
        daily[-1]["date"] if daily else _dt.datetime.now().strftime("%Y-%m-%d")
    )

    result: dict = {
        "code": code,
        "name": name,
        "days": days,
        "as_of": as_of_date,
        "color_map": dict(_FH_COLOR_MAP),
        "advisory_note": _ADVISORY_NOTE,
        "snapshot": snapshot,
        "daily": daily,
        "daily_history_total_days": daily_history_total_days,
    }
    if change_alert is not None:
        result["change_alert"] = change_alert
    return result
