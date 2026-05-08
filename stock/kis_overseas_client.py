"""KIS 해외 시세 게이트웨이.

REQ-CLIENT-04. 미국 주식 시세(현재가/일봉/15분봉)를 KIS OpenAPI로 가져오는 단일 진입점.
wrapper.py 직접 호출은 본 모듈에서만 일어난다(상위 레이어는 표준 dict shape만 봄).

설계 원칙:
- **거래소 자동 resolve**: stock_info.exchange 캐시 우선 → 미스 시 NAS→NYS→AMS 순회 → 영속.
- **인증 자동 분기**: routers._kis_auth.get_kis_credentials(user_id) 재사용.
  사용자 키 우선, 미등록은 운영자 키.
- **실패 시 None 반환**: 호출처(yf_client/quote_overseas/advisory_fetcher)가 yfinance fallback을
  결정할 수 있도록 함. ServiceError/ExternalAPIError를 raise하지 않음.
- **ConfigError(503)는 raise**: KIS 키 부재는 운영자가 인지해야 함 (fallback과 별개).

계측:
- record_event("kis_overseas.<func>.success" | "fail" | "fallback_to_yf")
- @timed 로 p50/p95 측정

거래소 코드 매핑:
- NAS ↔ "나스닥", NYS ↔ "뉴욕", AMS ↔ "아멕스"
  wrapper.fetch_oversea_price / fetch_ohlcv_overesea 는 self.exchange(한국어) 기준으로
  EXCHANGE_CODE/EXCHANGE_CODE4 변환을 수행한다. fetch_minute_bar_overesea(REQ-WRAPPER-01)는
  EXCD를 인자로 직접 받으므로 변환 불필요.
"""
from __future__ import annotations

import datetime as _dt
import logging
from typing import Optional

from db.session import get_session
from db.repositories.stock_info_repo import StockInfoRepository
from services.exceptions import ConfigError
from services import _telemetry

logger = logging.getLogger(__name__)


# 거래소 코드 ↔ wrapper 한국어 매핑
_EXCD_TO_KR = {"NAS": "나스닥", "NYS": "뉴욕", "AMS": "아멕스"}
# resolve 순회 순서 (시장 규모 기준)
_EXCHANGE_CANDIDATES = ("NAS", "NYS", "AMS")


# ── 내부: KIS 클라이언트 빌더 ────────────────────────────────────────────────


def _get_kis_client(user_id: Optional[int] = None):
    """KoreaInvestment 인스턴스를 반환. 인증 실패 시 None.

    ConfigError(KIS 키 부재)는 그대로 raise — 운영자 인지 필요.
    토큰 발급 실패(ExternalAPIError) 등 일시적 장애는 None.
    """
    try:
        from routers._kis_auth import get_kis_credentials, get_access_token, _get_user_base_url
    except Exception as e:
        logger.warning("kis_overseas_client: _kis_auth import 실패: %s", e)
        return None

    # ConfigError 는 propagate
    app_key, app_secret, acnt_no, acnt_prdt_cd_stk, _ = get_kis_credentials(user_id)
    base_url = _get_user_base_url(user_id)

    try:
        token = get_access_token(user_id)
    except Exception as e:
        logger.warning("kis_overseas_client: 토큰 발급 실패: %s", e)
        return None

    # KoreaInvestment 인스턴스 — 토큰은 위에서 발급, __init__의 자동 발급 로직을 우회
    try:
        from wrapper import KoreaInvestment
    except Exception as e:
        logger.warning("kis_overseas_client: wrapper import 실패: %s", e)
        return None

    inst = KoreaInvestment.__new__(KoreaInvestment)
    inst.base_url = base_url
    inst.api_key = app_key
    inst.api_secret = app_secret
    # KIS는 토큰 헤더에 "Bearer "를 직접 포함하는 형식 사용
    inst.access_token = f"Bearer {token}"
    # 계좌 정보 (시세 조회는 사용 안하지만 인스턴스 일관성 위해 채움)
    inst.acc_no = f"{acnt_no}-{acnt_prdt_cd_stk}"
    inst.acc_no_prefix = acnt_no
    inst.acc_no_postfix = acnt_prdt_cd_stk
    inst.exchange = "나스닥"  # default — 실제 호출 시 _set_client_exchange로 갱신
    inst.mock = False
    return inst


def _set_client_exchange(client, excd: str) -> None:
    """wrapper 인스턴스의 exchange 속성을 한국어로 설정 (EXCHANGE_CODE 변환용)."""
    kr = _EXCD_TO_KR.get(excd)
    if kr:
        client.exchange = kr


# ── 내부: 거래소 resolve ─────────────────────────────────────────────────────


def _try_price_for_exchange(client, symbol: str, excd: str) -> Optional[dict]:
    """단일 거래소에서 가격 조회 시도. 정상 응답이면 dict, 아니면 None."""
    try:
        _set_client_exchange(client, excd)
        resp = client.fetch_oversea_price(symbol)
    except Exception as e:
        logger.debug("kis_overseas: %s/%s price 호출 실패: %s", symbol, excd, e)
        return None

    if not isinstance(resp, dict):
        return None
    if resp.get("rt_cd") != "0":
        return None
    output = resp.get("output") or {}
    last_str = output.get("last") or output.get("ovrs_last") or "0"
    try:
        last = float(last_str)
    except (TypeError, ValueError):
        return None
    if last <= 0:
        return None
    return resp


@_telemetry.timed("kis_overseas.resolve_exchange")
def _resolve_exchange(symbol: str, user_id: Optional[int] = None) -> Optional[str]:
    """거래소 코드 자동 결정.

    1) stock_info.exchange 캐시 hit → 그대로 반환.
    2) 캐시 miss → NAS → NYS → AMS 순회. 첫 성공 거래소 영속 후 반환.
    3) 모두 실패 → None.

    이 함수는 KIS 키 부재(ConfigError)를 그대로 propagate한다.
    """
    # 1) 캐시 hit
    with get_session() as db:
        repo = StockInfoRepository(db)
        cached = repo.get_exchange(symbol, "US")
    if cached in _EXCHANGE_CANDIDATES:
        return cached

    # 2) 미스 → 순회
    client = _get_kis_client(user_id)
    if client is None:
        return None

    for excd in _EXCHANGE_CANDIDATES:
        resp = _try_price_for_exchange(client, symbol, excd)
        if resp is None:
            continue
        # 성공 → 영속 (best effort)
        try:
            with get_session() as db:
                repo = StockInfoRepository(db)
                repo.set_exchange(symbol, "US", excd)
        except Exception as e:
            logger.warning("kis_overseas: exchange 영속 실패 (%s/%s): %s", symbol, excd, e)
        return excd

    return None


# ── public: 가격 ──────────────────────────────────────────────────────────────


def _normalize_price_response(resp: dict, exchange: str) -> Optional[dict]:
    """KIS price 응답 → 표준 dict."""
    output = resp.get("output") or {}
    try:
        last = float(output.get("last") or output.get("ovrs_last") or 0) or None
    except (TypeError, ValueError):
        last = None
    if not last or last <= 0:
        return None

    def _f(*keys) -> Optional[float]:
        for k in keys:
            v = output.get(k)
            if v in (None, ""):
                continue
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
        return None

    def _i(*keys) -> Optional[int]:
        v = _f(*keys)
        return int(v) if v is not None else None

    return {
        "last": last,
        "change": _f("diff", "ovrs_diff"),
        "change_rate": _f("rate", "ovrs_rate"),
        "volume": _i("tvol", "ovrs_tvol") or 0,
        "currency": "USD",
        "exchange": exchange,
    }


@_telemetry.timed("kis_overseas.get_kis_price")
def get_kis_price(symbol: str, user_id: Optional[int] = None) -> Optional[dict]:
    """미국 주식 현재가 (KIS HHDFS00000300).

    Returns: {last, change, change_rate, volume, currency:"USD", exchange:"NAS"|"NYS"|"AMS"} 또는 None.
    실패 시 호출처가 yfinance fallback을 결정.
    """
    excd = _resolve_exchange(symbol, user_id=user_id)
    if not excd:
        _telemetry.record_event("kis_overseas.get_kis_price.fail")
        return None

    client = _get_kis_client(user_id)
    if client is None:
        _telemetry.record_event("kis_overseas.get_kis_price.fail")
        return None

    try:
        _set_client_exchange(client, excd)
        resp = client.fetch_oversea_price(symbol)
    except Exception as e:
        logger.debug("kis_overseas: get_kis_price 호출 실패 (%s/%s): %s", symbol, excd, e)
        _telemetry.record_event("kis_overseas.get_kis_price.fail")
        return None

    if not isinstance(resp, dict) or resp.get("rt_cd") != "0":
        _telemetry.record_event("kis_overseas.get_kis_price.fail")
        return None

    out = _normalize_price_response(resp, excd)
    if out is None:
        _telemetry.record_event("kis_overseas.get_kis_price.fail")
        return None

    _telemetry.record_event("kis_overseas.get_kis_price.success")
    return out


# ── public: 일봉 ──────────────────────────────────────────────────────────────


def _normalize_daily_row(row: dict) -> Optional[dict]:
    try:
        date = str(row.get("xymd") or row.get("date") or "")
        if not date:
            return None
        return {
            "date": date,
            "open": float(row.get("open", 0) or 0),
            "high": float(row.get("high", 0) or 0),
            "low": float(row.get("low", 0) or 0),
            "close": float(row.get("clos") or row.get("close") or 0),
            "volume": int(float(row.get("tvol") or row.get("evol") or 0)),
        }
    except (TypeError, ValueError):
        return None


@_telemetry.timed("kis_overseas.get_kis_ohlcv_daily")
def get_kis_ohlcv_daily(
    symbol: str,
    end_day: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Optional[list[dict]]:
    """미국 주식 일봉 (KIS HHDFS76240000).

    Returns: [{date:"YYYYMMDD", open, high, low, close, volume}, ...] (KIS 응답 순: 최신→과거).
    실패 시 None.
    """
    excd = _resolve_exchange(symbol, user_id=user_id)
    if not excd:
        _telemetry.record_event("kis_overseas.get_kis_ohlcv_daily.fail")
        return None

    client = _get_kis_client(user_id)
    if client is None:
        _telemetry.record_event("kis_overseas.get_kis_ohlcv_daily.fail")
        return None

    eday = end_day or _dt.datetime.now().strftime("%Y%m%d")

    try:
        _set_client_exchange(client, excd)
        resp = client.fetch_ohlcv_overesea(symbol, timeframe="D", end_day=eday, adj_price=True)
    except Exception as e:
        logger.debug("kis_overseas: get_kis_ohlcv_daily 실패 (%s/%s): %s", symbol, excd, e)
        _telemetry.record_event("kis_overseas.get_kis_ohlcv_daily.fail")
        return None

    if not isinstance(resp, dict) or resp.get("rt_cd") != "0":
        _telemetry.record_event("kis_overseas.get_kis_ohlcv_daily.fail")
        return None

    rows_raw = resp.get("output2") or []
    rows = [_normalize_daily_row(r) for r in rows_raw if r]
    rows = [r for r in rows if r is not None]
    if not rows:
        _telemetry.record_event("kis_overseas.get_kis_ohlcv_daily.fail")
        return None

    _telemetry.record_event("kis_overseas.get_kis_ohlcv_daily.success")
    return rows


# ── public: 15분봉 ────────────────────────────────────────────────────────────


def _normalize_minute_row(row: dict) -> Optional[dict]:
    """KIS 분봉 row → 표준 dict."""
    try:
        xymd = str(row.get("xymd") or row.get("kymd") or "")
        xhms = str(row.get("xhms") or row.get("khms") or "000000").zfill(6)
        if not xymd:
            return None
        # ISO8601 (timezone naive — 미국 동부 기준 시각, 호출처가 처리)
        iso = (
            f"{xymd[:4]}-{xymd[4:6]}-{xymd[6:8]}T"
            f"{xhms[:2]}:{xhms[2:4]}:{xhms[4:6]}"
        )
        close = float(row.get("last") or row.get("close") or row.get("clos") or 0)
        if close <= 0:
            return None
        return {
            "datetime": iso,
            "time": iso,  # advisory_fetcher 호환 (기존 yfinance 분봉도 "time" 키 사용)
            "open": float(row.get("open", close) or close),
            "high": float(row.get("high", close) or close),
            "low": float(row.get("low", close) or close),
            "close": close,
            "volume": int(float(row.get("evol") or row.get("tvol") or row.get("volume") or 0)),
        }
    except (TypeError, ValueError):
        return None


@_telemetry.timed("kis_overseas.get_kis_ohlcv_15min")
def get_kis_ohlcv_15min(
    symbol: str,
    days: int = 60,
    user_id: Optional[int] = None,
) -> Optional[list[dict]]:
    """미국 주식 15분봉 (KIS HHDFS76950200).

    days=60 일치 확보 위해 페이지네이션 KEYB 사용. KIS 분봉 응답 1회 최대 ~120봉.
    Returns: [{datetime/time, open, high, low, close, volume}, ...] 과거 → 최신 정렬.
    실패 시 None.
    """
    excd = _resolve_exchange(symbol, user_id=user_id)
    if not excd:
        _telemetry.record_event("kis_overseas.get_kis_ohlcv_15min.fail")
        return None

    client = _get_kis_client(user_id)
    if client is None:
        _telemetry.record_event("kis_overseas.get_kis_ohlcv_15min.fail")
        return None

    # 60일 × 약 26봉(거래일 6.5h × 4) ≈ 1500봉. 안전마진 포함 최대 20페이지 순회.
    target = max(100, days * 30)
    max_pages = 20
    aggregated: list[dict] = []
    keyb = ""
    next_flag = ""

    for _ in range(max_pages):
        try:
            resp = client.fetch_minute_bar_overesea(
                symbol, excd, time_period="15", keyb=keyb, next_flag=next_flag,
            )
        except Exception as e:
            logger.debug("kis_overseas: get_kis_ohlcv_15min 실패 (%s/%s): %s", symbol, excd, e)
            _telemetry.record_event("kis_overseas.get_kis_ohlcv_15min.fail")
            return None

        if not isinstance(resp, dict):
            break
        rows_raw = resp.get("output2") or []
        if not rows_raw:
            break
        for r in rows_raw:
            norm = _normalize_minute_row(r)
            if norm:
                aggregated.append(norm)
        if len(aggregated) >= target:
            break
        # 페이지네이션 — KIS 응답 output1.keyb 사용
        out1 = resp.get("output1") or {}
        new_keyb = str(out1.get("keyb") or out1.get("KEYB") or "")
        if not new_keyb or new_keyb == keyb:
            break
        keyb = new_keyb
        next_flag = "N"

    if not aggregated:
        _telemetry.record_event("kis_overseas.get_kis_ohlcv_15min.fail")
        return None

    # KIS 응답은 최신→과거 — 호출처(advisory) 호환을 위해 과거→최신 정렬
    aggregated.sort(key=lambda x: x["datetime"])
    _telemetry.record_event("kis_overseas.get_kis_ohlcv_15min.success")
    return aggregated


# ── public: 10단계 호가 (REQ-CLIENT-04) ──────────────────────────────────────


def _normalize_orderbook_response(resp: dict, exchange: str) -> Optional[dict]:
    """KIS HHDFS76200100 응답 → 표준 dict.

    응답 단계가 부족하면(빈/0 가격) 받은 단계만 반환.
    """
    out2 = resp.get("output2") or {}

    def _f(key: str) -> float:
        v = out2.get(key)
        if v in (None, ""):
            return 0.0
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    def _i(key: str) -> int:
        v = _f(key)
        return int(v) if v >= 0 else 0

    asks: list[dict] = []
    bids: list[dict] = []
    for i in range(1, 11):
        p_ask = _f(f"pask{i}")
        v_ask = _i(f"vask{i}")
        if p_ask > 0:
            asks.append({"price": p_ask, "volume": v_ask})
        p_bid = _f(f"pbid{i}")
        v_bid = _i(f"vbid{i}")
        if p_bid > 0:
            bids.append({"price": p_bid, "volume": v_bid})

    if not asks and not bids:
        return None

    return {
        "asks": asks,
        "bids": bids,
        "total_ask_volume": _i("tvol_a"),
        "total_bid_volume": _i("tvol_b"),
        "exchange": exchange,
    }


@_telemetry.timed("kis_overseas.get_kis_orderbook")
def get_kis_orderbook(symbol: str, user_id: Optional[int] = None) -> Optional[dict]:
    """미국 주식 10단계 호가 (KIS HHDFS76200100).

    Returns:
        ``{"asks": [{price, volume}, ...up to 10], "bids": [...], "total_ask_volume",
        "total_bid_volume", "exchange": "NAS"|"NYS"|"AMS"}`` 또는 None.
    실패 시 호출처가 fallback(WS 재시도 등)을 결정.
    """
    excd = _resolve_exchange(symbol, user_id=user_id)
    if not excd:
        _telemetry.record_event("kis_overseas.get_kis_orderbook.fail")
        return None

    client = _get_kis_client(user_id)
    if client is None:
        _telemetry.record_event("kis_overseas.get_kis_orderbook.fail")
        return None

    try:
        resp = client.fetch_oversea_asking_price(symbol, excd)
    except Exception as e:
        logger.debug("kis_overseas: get_kis_orderbook 실패 (%s/%s): %s", symbol, excd, e)
        _telemetry.record_event("kis_overseas.get_kis_orderbook.fail")
        return None

    if not isinstance(resp, dict) or resp.get("rt_cd") != "0":
        _telemetry.record_event("kis_overseas.get_kis_orderbook.fail")
        return None

    out = _normalize_orderbook_response(resp, excd)
    if out is None:
        _telemetry.record_event("kis_overseas.get_kis_orderbook.fail")
        return None

    _telemetry.record_event("kis_overseas.get_kis_orderbook.success")
    return out


# ── public: 현재가 상세 (REQ-CLIENT-04) ───────────────────────────────────────


def _normalize_price_detail_response(resp: dict, exchange: str) -> Optional[dict]:
    output = resp.get("output") or {}

    def _f(*keys) -> Optional[float]:
        for k in keys:
            v = output.get(k)
            if v in (None, ""):
                continue
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
        return None

    def _i(*keys) -> Optional[int]:
        v = _f(*keys)
        return int(v) if v is not None else None

    last = _f("last")
    if last is None or last <= 0:
        return None

    return {
        "open": _f("open"),
        "high": _f("high"),
        "low": _f("low"),
        "last": last,
        "prev_close": _f("base"),
        "volume": _i("tvol") or 0,
        "high_52w": _f("h52p"),
        "low_52w": _f("l52p"),
        "high_52w_date": output.get("h52d") or None,
        "low_52w_date": output.get("l52d") or None,
        "currency": "USD",
        "exchange": exchange,
    }


@_telemetry.timed("kis_overseas.get_kis_price_detail")
def get_kis_price_detail(symbol: str, user_id: Optional[int] = None) -> Optional[dict]:
    """미국 주식 현재가 상세 (KIS HHDFS76200200).

    Returns:
        ``{"open", "high", "low", "last", "prev_close", "volume", "high_52w",
        "low_52w", "currency": "USD", "exchange": ...}`` 또는 None.
    """
    excd = _resolve_exchange(symbol, user_id=user_id)
    if not excd:
        _telemetry.record_event("kis_overseas.get_kis_price_detail.fail")
        return None

    client = _get_kis_client(user_id)
    if client is None:
        _telemetry.record_event("kis_overseas.get_kis_price_detail.fail")
        return None

    try:
        resp = client.fetch_oversea_price_detail(symbol, excd)
    except Exception as e:
        logger.debug("kis_overseas: get_kis_price_detail 실패 (%s/%s): %s", symbol, excd, e)
        _telemetry.record_event("kis_overseas.get_kis_price_detail.fail")
        return None

    if not isinstance(resp, dict) or resp.get("rt_cd") != "0":
        _telemetry.record_event("kis_overseas.get_kis_price_detail.fail")
        return None

    out = _normalize_price_detail_response(resp, excd)
    if out is None:
        _telemetry.record_event("kis_overseas.get_kis_price_detail.fail")
        return None

    _telemetry.record_event("kis_overseas.get_kis_price_detail.success")
    return out
