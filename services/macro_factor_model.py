"""거시 팩터 모델 — 롤링 PCA 주성분 분해 + 종목 거시 베타.

거시 10지표 7년 일별 시계열을 롤링 PCA(504일 윈도우, 5 주성분, step=5)로
5개 직교 주성분 축으로 압축하고, 각 종목을 그 축들에 회귀해
거시 민감도(beta) + 고유 스토리(1-R²)를 분해한다.

설계 제약:
- **scikit-learn/scipy 불채택** — PCA는 `np.linalg.svd`, 회귀는 `np.linalg.lstsq`,
  표준화는 수동. numpy(`numpy<2`)는 yfinance 경유 이미 가용.
- 무거운 계산은 일배치(KST 00:20)로 캐시 → 엔드포인트는 read-only.
- 데이터 수집은 `stock/macro_fetcher.py` 헬퍼 + `oas_history_store` 재사용.
- 캐시는 `stock/macro_store.py`의 save_today/get_today.

`financial_ratios.py`/`macro_regime.py`(외부호출 0, 순수 로직)와 동일 레이어 패턴 —
순수 함수부는 외부 의존 0, 데이터 수집부만 fetcher에 위임.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


# ── 거시 10지표 메타 (key, label, source, symbol, transform, anchor) ──────────
# transform: "diff"(1차 차분, 금리/스프레드) | "logret"(로그수익률, 가격/지수)
# anchor: 부호 정렬 기준 (S&P500 — 위험선호 축의 + 방향 고정)

FACTOR_SERIES = [
    {"key": "ust10y", "label": "미국채 10년", "source": "yf", "symbol": "^TNX", "transform": "diff"},
    {"key": "ust2y", "label": "미국채 2년", "source": "fred", "symbol": "DGS2", "transform": "diff"},
    {"key": "hy_oas", "label": "HY 스프레드", "source": "oas_store", "symbol": "BAMLH0A0HYM2", "transform": "diff"},
    {"key": "ig_oas", "label": "IG 스프레드", "source": "oas_store", "symbol": "BAMLC0A0CM", "transform": "diff"},
    {"key": "vix", "label": "VIX", "source": "yf", "symbol": "^VIX", "transform": "logret"},
    {"key": "dxy", "label": "달러인덱스", "source": "yf", "symbol": "DX-Y.NYB", "transform": "logret"},
    {"key": "usdkrw", "label": "원/달러", "source": "yf", "symbol": "USDKRW=X", "transform": "logret"},
    {"key": "infl_exp", "label": "기대인플레", "source": "fred", "symbol": "T10YIE", "transform": "diff"},
    {"key": "wti", "label": "WTI", "source": "yf", "symbol": "CL=F", "transform": "logret"},
    {"key": "sp500", "label": "S&P500", "source": "yf", "symbol": "^GSPC", "transform": "logret", "anchor": True},
]

# 주성분 라벨 — 경험칙(loadings 재검증 필요). 프론트에 항상 loadings 동봉.
PC_LABELS = {
    0: "위험선호/유동성",
    1: "금리레벨",
    2: "곡선기울기",
    3: "달러/환율",
    4: "기대인플레",
}

# 롤링 파라미터
_WINDOW = 504        # ~2년 거래일
_N_COMPONENTS = 5
_STEP = 5            # 주 단위 샘플 (t3.small 부하 절감)

# 종목 베타 회귀 가드
_MIN_STOCK_OBS = 60  # 유효 관측 < 60 종목 skip
_STOCK_CAP = 100     # 종목 N cap

# 신호등 임계 (|z|)
_LEVEL_STRESSED = 1.5
_LEVEL_MILD = 0.7


# ── 순수 PCA 함수부 (외부 의존 0) ─────────────────────────────────────────────

def _standardize(X_win: np.ndarray) -> np.ndarray:
    """윈도우별 수동 표준화 (x-mean)/std. std=0 컬럼 가드(분모 1.0)."""
    mean = X_win.mean(axis=0)
    std = X_win.std(axis=0)
    std_safe = np.where(std == 0, 1.0, std)
    return (X_win - mean) / std_safe


def _pca_window(X_win: np.ndarray, n_components: int = _N_COMPONENTS) -> dict:
    """단일 윈도우 PCA via np.linalg.svd.

    Args:
        X_win: (T, F) 표준화 전 변환 행렬 (T=윈도우 길이, F=지표 수)
        n_components: 주성분 수

    Returns:
        {
            "components": (n_components, F) 단위 고유벡터(행=PC),
            "evr": (n_components,) 설명분산비율 (전체 분산 대비),
            "scores": (T, n_components) 주성분 점수 (표준화된 데이터의 투영),
        }
    """
    Xs = _standardize(X_win)
    # SVD: Xs = U S V^T. V의 행(=Vt)이 주성분 방향. 특이값 제곱이 분산에 비례.
    # np.errstate: macOS Accelerate BLAS가 정상 SVD/matmul에도 spurious FP-flag를
    # 올리는 알려진 버그 — 결과는 유한(단위테스트로 직교성/evr 검증). 경고만 격리.
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        U, S, Vt = np.linalg.svd(Xs, full_matrices=False)
        n = min(n_components, Vt.shape[0])
        components = Vt[:n]                  # (n, F)
        # 설명분산비율: 특이값 제곱 / 전체 특이값 제곱 합
        var = (S ** 2)
        total_var = var.sum()
        if total_var <= 0:
            evr = np.zeros(n)
        else:
            evr = var[:n] / total_var
        # 점수: 표준화 데이터를 주성분 방향에 투영 = U*S (앞 n열)
        scores = (U[:, :n] * S[:n])         # (T, n)
    return {"components": components, "evr": evr, "scores": scores}


def _align_sign(
    components: np.ndarray,
    anchor_idx: int,
    prev_components: Optional[np.ndarray] = None,
) -> np.ndarray:
    """주성분 부호 정렬 (회전 모호성 제거 → 설명력 추이 깜빡임 방지).

    - PC0(anchor PC): anchor 지표(S&P500) loading이 항상 + 가 되도록 부호 고정.
    - PC1~: prev_components가 있으면 직전 윈도우 동일 PC와 내적 부호로 연속성 확보.
      prev 없으면 anchor loading 부호로 결정론적 고정(첫 윈도우 안정).

    멱등: 이미 정렬된 components에 다시 적용해도 동일 결과.

    Args:
        components: (n, F) 주성분 (행=PC)
        anchor_idx: anchor 지표의 컬럼 인덱스
        prev_components: 직전 윈도우 정렬 후 (n, F) 또는 None

    Returns:
        부호 정렬된 (n, F) (원본 unmutated copy).
    """
    comp = components.copy()
    n = comp.shape[0]
    for i in range(n):
        if prev_components is not None and i < prev_components.shape[0]:
            # 직전 윈도우 동일 PC와의 내적 부호로 연속성 확보 (errstate: BLAS FP-flag 격리)
            with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
                dot = float(np.dot(comp[i], prev_components[i]))
            if dot < 0:
                comp[i] = -comp[i]
        else:
            # prev 없음(첫 윈도우): anchor loading 부호로 결정론적 고정
            if comp[i, anchor_idx] < 0:
                comp[i] = -comp[i]
        # PC0(anchor PC)는 prev 정렬 후에도 anchor loading +를 최종 강제(축 의미 고정)
        if i == 0 and comp[i, anchor_idx] < 0:
            comp[i] = -comp[i]
    return comp


def compute_rolling_pca(
    X: np.ndarray,
    dates: list[str],
    window: int = _WINDOW,
    n_components: int = _N_COMPONENTS,
    step: int = _STEP,
    anchor_idx: Optional[int] = None,
) -> dict:
    """롤링 PCA.

    Args:
        X: (T, F) 변환 행렬 (표준화 전 — 윈도우별로 _pca_window가 표준화)
        dates: 길이 T 날짜 문자열 (X 행과 1:1)
        window: 윈도우 길이 (거래일)
        n_components: 주성분 수
        step: 윈도우 이동 간격
        anchor_idx: anchor 지표 컬럼 인덱스 (None이면 FACTOR_SERIES에서 탐색)

    Returns:
        {
            "today_scores": (n,) 마지막 윈도우 주성분 점수의 z-score(신호등용),
            "today_loadings": (n, F) 마지막 윈도우 정렬 주성분,
            "today_evr": (n,) 마지막 윈도우 설명분산비율,
            "explained_history": [{date, pc0..pc(n-1)}] 윈도우별 evr 추이,
            "window_dates": list[str] 마지막 윈도우의 날짜 (종목 베타 정렬용),
            "last_scores_window": (W, n) 마지막 윈도우 주성분 점수 시계열,
            "n_windows": int,
        }
    """
    if anchor_idx is None:
        anchor_idx = next(
            (i for i, m in enumerate(FACTOR_SERIES) if m.get("anchor")), 0
        )

    T, F = X.shape
    if T < window:
        raise ValueError(f"시계열 길이 {T} < 윈도우 {window} — PCA 불가")

    explained_history: list[dict] = []
    prev_components: Optional[np.ndarray] = None
    last = None
    last_start = 0

    # 윈도우 시작 인덱스: 0, step, 2*step, ... (마지막 윈도우는 끝에 정렬)
    starts = list(range(0, T - window + 1, step))
    if starts[-1] != T - window:
        starts.append(T - window)

    for start in starts:
        end = start + window
        X_win = X[start:end]
        res = _pca_window(X_win, n_components=n_components)
        comp = _align_sign(res["components"], anchor_idx, prev_components)
        prev_components = comp
        evr = res["evr"]

        # 설명력 추이: 윈도우 마지막 날짜 기준
        entry = {"date": dates[end - 1]}
        for j in range(len(evr)):
            entry[f"pc{j}"] = round(float(evr[j]), 4)
        explained_history.append(entry)

        last = res
        last_start = start

    # 마지막 윈도우 상세
    last_end = last_start + window
    last_comp = prev_components  # 이미 정렬됨
    last_scores = last["scores"]  # (W, n) — 부호는 components 정렬과 별개이므로 재정렬
    last_evr = last["evr"]

    # scores 부호를 정렬된 components와 일치시키기 위해 재투영
    # (정렬 시 일부 PC 부호가 뒤집혔을 수 있음)
    # np.errstate: macOS Accelerate BLAS가 정상 matmul에도 spurious divide/overflow
    # FP-flag를 올리는 알려진 버그 — 출력은 유한(테스트로 검증). 경고만 격리.
    Xs_last = _standardize(X[last_start:last_end])
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        aligned_scores = Xs_last @ last_comp.T  # (W, n)

    # today 신호등: 마지막 윈도우 점수 시계열의 z-score(마지막 관측치)
    today_scores = _scores_today_zscore(aligned_scores)

    return {
        "today_scores": today_scores,                    # (n,)
        "today_loadings": last_comp,                      # (n, F)
        "today_evr": last_evr,                            # (n,)
        "explained_history": explained_history,
        "window_dates": dates[last_start:last_end],
        "last_scores_window": aligned_scores,             # (W, n)
        "n_windows": len(starts),
    }


def _scores_today_zscore(scores_window: np.ndarray) -> np.ndarray:
    """주성분 점수 시계열(W, n)의 마지막 관측치를 윈도우 내 z-score로.

    표준화된 데이터의 투영이므로 윈도우 평균≈0이지만, 안전하게 윈도우 통계로 z화.
    std=0 가드.
    """
    mean = scores_window.mean(axis=0)
    std = scores_window.std(axis=0)
    std_safe = np.where(std == 0, 1.0, std)
    z = (scores_window[-1] - mean) / std_safe
    return z


def compute_stock_betas(
    pca_result: dict,
    stock_returns: dict[str, dict],
) -> list[dict]:
    """종목 logret을 주성분 점수에 회귀 → 거시 베타 + R² + 고유스토리.

    Args:
        pca_result: compute_rolling_pca 반환 (window_dates, last_scores_window 사용)
        stock_returns: {code: {"name", "market", "returns": {date: logret}}}

    Returns:
        [{code, name, market, betas:[n], r2, idiosyncratic}] (유효관측<60 skip).
        idiosyncratic = 1 - r2 (고유 스토리 비중).
    """
    window_dates: list[str] = pca_result["window_dates"]
    scores: np.ndarray = pca_result["last_scores_window"]  # (W, n)
    n_pc = scores.shape[1]

    # window_dates → 인덱스 맵 (종목 수익률 정렬용)
    date_idx = {d: i for i, d in enumerate(window_dates)}

    out: list[dict] = []
    count = 0
    for code, meta in stock_returns.items():
        if count >= _STOCK_CAP:
            break
        rets: dict = meta.get("returns") or {}
        # 윈도우 날짜에 정렬된 (y, 해당 score 행) 수집
        rows_y: list[float] = []
        rows_idx: list[int] = []
        for d, r in rets.items():
            if d in date_idx and r is not None:
                try:
                    fr = float(r)
                except (TypeError, ValueError):
                    continue
                if np.isnan(fr) or np.isinf(fr):
                    continue
                rows_y.append(fr)
                rows_idx.append(date_idx[d])

        if len(rows_y) < _MIN_STOCK_OBS:
            continue

        y = np.array(rows_y)                     # (m,)
        Xpc = scores[rows_idx]                   # (m, n_pc)
        # 절편 포함 설계행렬
        A = np.hstack([np.ones((Xpc.shape[0], 1)), Xpc])  # (m, n_pc+1)
        # np.errstate: Accelerate BLAS spurious FP-flag 격리 (위 주석 참조).
        with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            coef, _res, _rank, _sv = np.linalg.lstsq(A, y, rcond=None)
            betas = coef[1:]                     # 절편 제외
            # R²: 1 - SS_res/SS_tot
            y_hat = A @ coef
        ss_res = float(np.sum((y - y_hat) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r2 = 0.0 if ss_tot <= 0 else max(0.0, min(1.0, 1.0 - ss_res / ss_tot))

        out.append({
            "code": code,
            "name": meta.get("name") or code,
            "market": (meta.get("market") or "KR").upper(),
            "betas": [round(float(b), 4) for b in betas],
            "r2": round(r2, 4),
            "idiosyncratic": round(1.0 - r2, 4),
        })
        count += 1

    return out


def _level_for_z(z: float) -> str:
    """|z| → 신호등 레벨. stressed/elevated 구분은 부호로 표현하지 않고 강도만."""
    az = abs(z)
    if az >= _LEVEL_STRESSED:
        return "stressed"
    if az >= _LEVEL_MILD:
        return "mild"
    return "neutral"


# ── 데이터 수집부 (fetcher 위임) ──────────────────────────────────────────────

def _build_factor_matrix() -> tuple[np.ndarray, list[str], list[str], list[str]]:
    """거시 10지표 7년 일별 시계열 → 변환 행렬.

    S&P500 거래일 기준 reindex + forward-fill(≤5일) + 잔여 결측 행 drop.
    변환(diff/logret) 후 (T, F) 행렬 반환.

    Returns:
        (X, dates, keys, errors)
        X: (T, F) 변환 행렬 (표준화 전)
        dates: 길이 T 날짜 (변환 후 — 첫 행은 diff/logret로 소실)
        keys: 길이 F 지표 key
        errors: 수집 부분 실패 메시지
    """
    import pandas as pd

    errors: list[str] = []
    raw_series: dict[str, "pd.Series"] = {}

    for meta in FACTOR_SERIES:
        key = meta["key"]
        try:
            s = _fetch_one_series(meta)
            if s is None or s.empty:
                errors.append(f"{key}: 빈 시계열")
                continue
            raw_series[key] = s
        except Exception as e:  # noqa: BLE001 — 부분 실패 격리
            errors.append(f"{key}: {e}")
            logger.warning("팩터 시계열 수집 실패 (%s): %s", key, e)

    # anchor(S&P500) 필수 — 거래일 기준
    anchor_key = next((m["key"] for m in FACTOR_SERIES if m.get("anchor")), "sp500")
    if anchor_key not in raw_series:
        raise ValueError("anchor(S&P500) 시계열 수집 실패 — 행렬 조립 불가")

    anchor_index = raw_series[anchor_key].index

    # S&P500 거래일 기준 reindex + ffill(≤5일)
    aligned: dict[str, "pd.Series"] = {}
    for key, s in raw_series.items():
        s2 = s.reindex(anchor_index).ffill(limit=5)
        aligned[key] = s2

    keys = [m["key"] for m in FACTOR_SERIES if m["key"] in aligned]
    df = pd.DataFrame({k: aligned[k] for k in keys})

    # 잔여 결측 행 drop
    df = df.dropna(how="any")
    if df.empty:
        raise ValueError("정렬 후 유효 행 0 — 행렬 조립 불가")

    # 변환: diff / logret
    transformed = {}
    for m in FACTOR_SERIES:
        k = m["key"]
        if k not in df.columns:
            continue
        col = df[k]
        if m["transform"] == "diff":
            transformed[k] = col.diff()
        else:  # logret
            # 가격 ≤0 가드: log 입력 보호
            safe = col.where(col > 0)
            transformed[k] = np.log(safe).diff()

    tdf = pd.DataFrame(transformed).dropna(how="any")
    if tdf.empty:
        raise ValueError("변환 후 유효 행 0 — 행렬 조립 불가")

    final_keys = list(tdf.columns)
    X = tdf.to_numpy(dtype=float)
    dates = [d.strftime("%Y-%m-%d") for d in tdf.index]
    return X, dates, final_keys, errors


def _fetch_one_series(meta: dict) -> Optional["object"]:
    """단일 지표 7년 일별 시계열을 pandas Series(index=Timestamp)로.

    source:
      - yf: yfinance .history(period="7y", interval="1d") Close
      - fred: macro_fetcher._fetch_fred_via_api(series_id) → oas_store 머지 + slice
      - oas_store: oas_history_store.slice_history(series_id, 7) (HY/IG, FRED 머지 기수행)
    """
    import pandas as pd

    source = meta["source"]
    symbol = meta["symbol"]

    if source == "yf":
        import yfinance as yf
        t = yf.Ticker(symbol)
        hist = t.history(period="7y", interval="1d")
        if hist is None or hist.empty:
            return None
        s = hist["Close"].dropna()
        s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
        s = s[~s.index.duplicated(keep="last")]
        return s

    if source == "fred":
        # DGS2 / T10YIE — FRED API 수집 후 oas_history_store에 머지(7년 누적) + slice
        from stock import macro_fetcher
        from stock import oas_history_store
        api_rows = macro_fetcher._fetch_fred_via_api(symbol)
        if api_rows:
            persist = [{"date": r["date"], "value": r["value"]} for r in api_rows]
            try:
                oas_history_store.merge_and_persist(symbol, persist)
            except Exception as e:  # noqa: BLE001
                logger.warning("FRED %s 누적 머지 실패: %s", symbol, e)
        rows = oas_history_store.slice_history(symbol, 7)
        if not rows:
            # store 비었으면 api_rows 직접 사용
            rows = [{"date": r["date"], "value": r["value"]} for r in (api_rows or [])]
        if not rows:
            return None
        return _rows_to_series(rows)

    if source == "oas_store":
        # HY/IG OAS — fetch_credit_spread가 이미 FRED 머지를 수행(7년 누적).
        # 콜드스타트 보호: store 비면 fetch_credit_spread 1회 트리거.
        from stock import oas_history_store
        rows = oas_history_store.slice_history(symbol, 7)
        if not rows:
            try:
                from stock import macro_fetcher
                macro_fetcher.fetch_credit_spread()  # store 적재 트리거
                rows = oas_history_store.slice_history(symbol, 7)
            except Exception as e:  # noqa: BLE001
                logger.warning("OAS store 콜드스타트 트리거 실패 (%s): %s", symbol, e)
        if not rows:
            return None
        return _rows_to_series(rows)

    return None


def _rows_to_series(rows: list[dict]) -> "object":
    """[{date, value}] → pandas Series(index=Timestamp normalized)."""
    import pandas as pd
    dates = pd.to_datetime([r["date"] for r in rows]).normalize()
    vals = [float(r["value"]) for r in rows]
    s = pd.Series(vals, index=dates).dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s


# ── 종목 수집 + 베타 입력 ─────────────────────────────────────────────────────

# 관심종목 0건 폴백 대표 리스트 (KR 대형주 + US 메가캡 — 거시 베타 데모용)
_REPRESENTATIVE_STOCKS: list[tuple[str, str, str]] = [
    ("005930", "삼성전자", "KR"),
    ("000660", "SK하이닉스", "KR"),
    ("373220", "LG에너지솔루션", "KR"),
    ("207940", "삼성바이오로직스", "KR"),
    ("005380", "현대차", "KR"),
    ("105560", "KB금융", "KR"),
    ("AAPL", "Apple", "US"),
    ("MSFT", "Microsoft", "US"),
    ("NVDA", "NVIDIA", "US"),
    ("JPM", "JPMorgan", "US"),
]


def _collect_portfolio_stocks() -> tuple[list[tuple[str, str, str]], bool]:
    """베타 대상 종목 = 전 사용자 watchlist ∪ advisory_stocks (dedup).

    scheduler의 helper 재사용. 0건이면 대표 리스트 폴백.

    Returns:
        ([(code, name, market)], used_fallback)
    """
    seen: set[tuple[str, str]] = set()
    pairs: list[tuple[str, str]] = []
    try:
        from services.scheduler_service import (
            _all_advisory_users_codes,
            _all_watchlist_codes,
        )
        for code, market in (_all_advisory_users_codes() or []) + (_all_watchlist_codes() or []):
            mk = (market or "KR").upper()
            key = (code, mk)
            if code and key not in seen:
                seen.add(key)
                pairs.append((code, mk))
    except Exception as e:  # noqa: BLE001
        logger.warning("포트폴리오 종목 수집 실패: %s", e)

    if not pairs:
        return list(_REPRESENTATIVE_STOCKS), True

    # 종목명 보강 (symbol_map). 실패해도 code로 폴백.
    out: list[tuple[str, str, str]] = []
    for code, market in pairs[:_STOCK_CAP]:
        name = code
        try:
            if market == "KR":
                from stock.symbol_map import code_to_name
                name = code_to_name(code) or code
        except Exception:  # noqa: BLE001
            pass
        out.append((code, name, market))
    return out, False


def _fetch_stock_logret_series(code: str, market: str) -> dict[str, float]:
    """종목 7년 일별 종가 → logret {date: float}. 실패 시 빈 dict.

    KR=`_resolve_yf_code`로 .KS/.KQ 자동 부착, US=티커 그대로. yfinance 7y 일봉.
    """
    try:
        import numpy as _np
        import pandas as pd
        import yfinance as yf
        from stock.yf_client import _resolve_yf_code

        ticker = _resolve_yf_code(code) if market == "KR" else code
        hist = yf.Ticker(ticker).history(period="7y", interval="1d")
        if hist is None or hist.empty:
            return {}
        close = hist["Close"].dropna()
        close = close[close > 0]
        if len(close) < _MIN_STOCK_OBS + 1:
            return {}
        with _np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            logret = _np.log(close).diff().dropna()
        idx = pd.to_datetime(logret.index).tz_localize(None).normalize()
        return {
            d.strftime("%Y-%m-%d"): float(v)
            for d, v in zip(idx, logret.to_numpy())
            if not (_np.isnan(v) or _np.isinf(v))
        }
    except Exception as e:  # noqa: BLE001
        logger.warning("종목 logret 수집 실패 (%s/%s): %s", code, market, e)
        return {}


def build_and_cache_factor_model() -> dict:
    """배치 오케스트레이터 — 수집 → 롤링 PCA → 종목 베타 → macro_store 캐시.

    KST 00:20 일배치(scheduler)에서 호출. 요청 경로에서 호출 금지(무거움).
    부분 실패는 errors에 격리, 핵심(행렬/PCA) 실패만 raise.

    Returns:
        save_today에 저장되는 응답 dict (서비스가 그대로 반환).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from stock.db_base import now_kst_iso
    from stock.macro_store import save_today

    errors: list[str] = []

    # 1) 거시 행렬 조립 (anchor 실패 시 raise)
    X, dates, keys, mat_errors = _build_factor_matrix()
    errors.extend(mat_errors)

    anchor_idx = next((i for i, k in enumerate(keys) if FACTOR_SERIES_BY_KEY.get(k, {}).get("anchor")), None)
    if anchor_idx is None:
        # keys에 anchor 없으면 sp500 인덱스 탐색
        anchor_idx = keys.index("sp500") if "sp500" in keys else 0

    # 2) 롤링 PCA
    pca = compute_rolling_pca(X, dates, window=_WINDOW, n_components=_N_COMPONENTS,
                              step=_STEP, anchor_idx=anchor_idx)

    # 3) 종목 수집 + 베타
    stocks, used_fallback = _collect_portfolio_stocks()
    portfolio_keys = {(c, m) for c, _n, m in stocks}
    stock_returns: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {
            pool.submit(_fetch_stock_logret_series, c, m): (c, n, m)
            for c, n, m in stocks
        }
        for fut in as_completed(futs):
            c, n, m = futs[fut]
            try:
                rets = fut.result()
            except Exception as e:  # noqa: BLE001
                errors.append(f"종목 {c}: {e}")
                rets = {}
            if rets:
                stock_returns[c] = {"name": n, "market": m, "returns": rets}

    betas = compute_stock_betas(pca, stock_returns)

    # 4) 응답 조립 (4종 산출)
    result = _assemble_response(pca, keys, betas, portfolio_keys, used_fallback, errors)

    # 5) 캐시 저장
    try:
        save_today("factor_model", result)
    except Exception as e:  # noqa: BLE001
        logger.error("factor_model 캐시 저장 실패: %s", e, exc_info=True)
        result.setdefault("errors", []).append(f"캐시 저장: {e}")

    return result


# key → meta 역인덱스 (anchor 탐색용)
FACTOR_SERIES_BY_KEY = {m["key"]: m for m in FACTOR_SERIES}


def _assemble_response(
    pca: dict,
    keys: list[str],
    betas: list[dict],
    portfolio_keys: set[tuple[str, str]],
    used_fallback: bool,
    errors: list[str],
) -> dict:
    """4종 산출물을 API 응답 shape으로 조립.

    ① signal_lights (5축 z-score 신호등)
    ② stock_betas (관심+자문 거시베타 + R²)
    ③ explained_history (설명력 추이)
    ④ loadings (PC별 지표 weight)
    """
    from stock.db_base import now_kst_iso

    n_pc = pca["today_scores"].shape[0]
    today_z = pca["today_scores"]
    today_loadings = pca["today_loadings"]   # (n, F)
    today_evr = pca["today_evr"]
    key_labels = {m["key"]: m["label"] for m in FACTOR_SERIES}

    # ① 신호등
    signal_lights = []
    for pc in range(n_pc):
        z = float(today_z[pc])
        signal_lights.append({
            "pc": pc,
            "label": PC_LABELS.get(pc, f"PC{pc}"),
            "z": round(z, 3),
            "level": _level_for_z(z),
        })

    # ④ loadings (절대값 정렬)
    loadings = []
    for pc in range(n_pc):
        weights = [
            {"key": keys[f], "label": key_labels.get(keys[f], keys[f]),
             "weight": round(float(today_loadings[pc, f]), 4)}
            for f in range(len(keys))
        ]
        weights.sort(key=lambda w: abs(w["weight"]), reverse=True)
        loadings.append({
            "pc": pc,
            "label": PC_LABELS.get(pc, f"PC{pc}"),
            "explained": round(float(today_evr[pc]), 4),
            "weights": weights,
        })

    # ② 종목 베타 — in_portfolio/source 플래그는 서비스 레이어에서 user별 주입.
    #    배치는 합집합 베타만 계산(종목 무관 순수 회귀). source는 KR/US 시장 기반 단순 표기.
    stock_betas = []
    for b in betas:
        stock_betas.append({
            **b,
            "in_portfolio": (b["code"], b["market"]) in portfolio_keys,
            "source": "portfolio" if not used_fallback else "representative",
        })

    return {
        "status": "ok",
        "as_of": pca["window_dates"][-1],
        "updated_at": now_kst_iso(),
        "pc_labels": PC_LABELS,
        "signal_lights": signal_lights,
        "explained_history": pca["explained_history"],
        "loadings": loadings,
        "stock_betas": stock_betas,
        "meta": {
            "n_windows": pca["n_windows"],
            "n_stocks": len(stock_betas),
            "n_factors": len(keys),
            "window": _WINDOW,
            "step": _STEP,
            "used_representative_fallback": used_fallback,
        },
        "errors": errors,
    }
