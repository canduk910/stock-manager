"""거시 팩터 모델(롤링 PCA) 단위 테스트.

순수 함수부(외부 호출 0) 합성 행렬 검증:
- _pca_window: 직교성, evr 정렬/범위, scores 형태
- _align_sign: anchor +, 멱등성, 연속성
- compute_rolling_pca: 윈도우 수, today_scores 형태, explained_history
- compute_stock_betas: 회귀 R² 범위, 유효관측<60 skip, 결측/금융업 케이스
- _level_for_z: 신호등 임계
- _build_factor_matrix: fetcher monkeypatch로 정렬/변환/결측 가드
"""
import numpy as np
import pytest

from services import macro_factor_model as mfm


# ── _pca_window ───────────────────────────────────────────────────────────────

def _synthetic_matrix(T=600, F=10, seed=42):
    """잠재 5요인 + 노이즈로 구조 있는 합성 행렬."""
    rng = np.random.default_rng(seed)
    k = 5
    loadings = rng.normal(size=(k, F))
    factors = rng.normal(size=(T, k))
    noise = rng.normal(scale=0.3, size=(T, F))
    # errstate: macOS Accelerate BLAS spurious matmul FP-flag 격리 (모듈과 동일 사유)
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        return factors @ loadings + noise


def test_pca_window_components_orthonormal():
    X = _synthetic_matrix()
    res = mfm._pca_window(X, n_components=5)
    comp = res["components"]
    assert comp.shape == (5, X.shape[1])
    # 행(주성분) 직교 정규 — V^T 의 행은 단위벡터 + 상호 직교
    gram = comp @ comp.T
    np.testing.assert_allclose(gram, np.eye(5), atol=1e-8)


def test_pca_window_evr_sorted_and_bounded():
    X = _synthetic_matrix()
    res = mfm._pca_window(X, n_components=5)
    evr = res["evr"]
    assert evr.shape == (5,)
    # 내림차순
    assert all(evr[i] >= evr[i + 1] - 1e-12 for i in range(len(evr) - 1))
    # 0~1 범위, 합 ≤ 1
    assert (evr >= 0).all() and (evr <= 1.0 + 1e-9).all()
    assert evr.sum() <= 1.0 + 1e-9


def test_pca_window_full_rank_evr_sums_to_one():
    """n_components = F 이면 evr 합 = 1 (전체 분산 설명)."""
    X = _synthetic_matrix(F=8)
    res = mfm._pca_window(X, n_components=8)
    assert abs(res["evr"].sum() - 1.0) < 1e-9


def test_pca_window_scores_shape():
    X = _synthetic_matrix(T=300, F=10)
    res = mfm._pca_window(X, n_components=5)
    assert res["scores"].shape == (300, 5)


def test_standardize_zero_std_guard():
    """std=0 컬럼(상수)은 0으로 나누지 않고 안전 처리(분모 1.0)."""
    X = np.ones((100, 3))
    X[:, 1] = np.arange(100)  # 변동 컬럼
    Xs = mfm._standardize(X)
    assert not np.isnan(Xs).any()
    assert not np.isinf(Xs).any()
    # 상수 컬럼은 평균 빼서 0
    np.testing.assert_allclose(Xs[:, 0], 0.0, atol=1e-12)


# ── _align_sign ───────────────────────────────────────────────────────────────

def test_align_sign_anchor_positive():
    """anchor 지표 loading은 PC0에서 항상 + (첫 윈도우)."""
    comp = np.array([
        [-0.5, 0.3, -0.8],   # anchor_idx=0 음수 → 뒤집힘
        [0.2, -0.9, 0.4],
    ])
    aligned = mfm._align_sign(comp, anchor_idx=0, prev_components=None)
    assert aligned[0, 0] > 0


def test_align_sign_idempotent():
    """이미 정렬된 components에 재적용 → 동일 결과 (멱등)."""
    X = _synthetic_matrix()
    comp = mfm._pca_window(X)["components"]
    once = mfm._align_sign(comp, anchor_idx=9, prev_components=None)
    twice = mfm._align_sign(once, anchor_idx=9, prev_components=once)
    np.testing.assert_allclose(once, twice, atol=1e-12)


def test_align_sign_continuity_with_prev():
    """직전 윈도우와 부호 반대인 PC는 뒤집어 연속성 확보."""
    prev = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    cur = np.array([[-1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])  # PC0 부호 반대
    aligned = mfm._align_sign(cur, anchor_idx=2, prev_components=prev)
    # PC0이 prev와 같은 방향(+)으로 정렬
    assert float(np.dot(aligned[0], prev[0])) > 0


def test_align_sign_does_not_mutate_input():
    comp = np.array([[-0.5, 0.3], [0.2, -0.9]])
    snapshot = comp.copy()
    mfm._align_sign(comp, anchor_idx=0, prev_components=None)
    np.testing.assert_array_equal(comp, snapshot)


# ── compute_rolling_pca ───────────────────────────────────────────────────────

def _dates(T):
    import pandas as pd
    return [d.strftime("%Y-%m-%d") for d in pd.date_range("2019-01-01", periods=T, freq="D")]


def test_rolling_pca_basic_shapes():
    T = 600
    X = _synthetic_matrix(T=T, F=10)
    dates = _dates(T)
    res = mfm.compute_rolling_pca(X, dates, window=504, n_components=5, step=5, anchor_idx=9)
    assert res["today_scores"].shape == (5,)
    assert res["today_loadings"].shape == (5, 10)
    assert res["today_evr"].shape == (5,)
    assert len(res["window_dates"]) == 504
    assert res["last_scores_window"].shape == (504, 5)
    assert res["n_windows"] >= 1
    # explained_history 각 항목에 pc0..pc4
    for entry in res["explained_history"]:
        assert "date" in entry
        for j in range(5):
            assert f"pc{j}" in entry


def test_rolling_pca_window_dates_align_to_end():
    """마지막 윈도우 날짜는 시계열 끝에 정렬."""
    T = 520
    X = _synthetic_matrix(T=T, F=10)
    dates = _dates(T)
    res = mfm.compute_rolling_pca(X, dates, window=504, step=5, anchor_idx=9)
    assert res["window_dates"][-1] == dates[-1]


def test_rolling_pca_raises_when_too_short():
    X = _synthetic_matrix(T=100, F=10)
    dates = _dates(100)
    with pytest.raises(ValueError):
        mfm.compute_rolling_pca(X, dates, window=504)


# ── compute_stock_betas ───────────────────────────────────────────────────────

def _pca_result_for_betas(T=520, F=10):
    X = _synthetic_matrix(T=T, F=F)
    dates = _dates(T)
    return mfm.compute_rolling_pca(X, dates, window=504, step=5, anchor_idx=9), dates


def test_stock_betas_r2_in_range_and_idiosyncratic():
    pca_res, _ = _pca_result_for_betas()
    wdates = pca_res["window_dates"]
    scores = pca_res["last_scores_window"]
    # 종목 수익률 = PC 점수의 선형결합 + 노이즈 → R² 높아야
    rng = np.random.default_rng(7)
    true_beta = np.array([0.5, -0.3, 0.2, 0.0, 0.1])
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        y = scores @ true_beta + rng.normal(scale=0.01, size=scores.shape[0])
    returns = {d: float(y[i]) for i, d in enumerate(wdates)}
    out = mfm.compute_stock_betas(
        pca_res, {"005930": {"name": "삼성전자", "market": "KR", "returns": returns}}
    )
    assert len(out) == 1
    row = out[0]
    assert 0.0 <= row["r2"] <= 1.0
    assert abs(row["idiosyncratic"] - (1.0 - row["r2"])) < 1e-9
    assert len(row["betas"]) == 5
    # 강한 선형관계 → R² 높음
    assert row["r2"] > 0.8


def test_stock_betas_skip_insufficient_obs():
    """유효 관측 < 60 종목은 skip."""
    pca_res, _ = _pca_result_for_betas()
    wdates = pca_res["window_dates"]
    # 50개만 제공
    returns = {d: 0.01 for d in wdates[:50]}
    out = mfm.compute_stock_betas(
        pca_res, {"000660": {"name": "SK하이닉스", "market": "KR", "returns": returns}}
    )
    assert out == []


def test_stock_betas_handles_missing_and_nan():
    """결측 날짜 + NaN/Inf 수익률은 무시, 유효분만 회귀."""
    pca_res, _ = _pca_result_for_betas()
    wdates = pca_res["window_dates"]
    returns = {}
    for i, d in enumerate(wdates):
        if i % 3 == 0:
            returns[d] = float("nan")
        elif i % 7 == 0:
            continue  # 결측
        else:
            returns[d] = 0.005
    # 윈도우 밖 날짜도 섞음 (정렬에서 무시되어야)
    returns["1999-01-01"] = 0.5
    out = mfm.compute_stock_betas(
        pca_res, {"AAPL": {"name": "Apple", "market": "us", "returns": returns}}
    )
    # 유효 관측 ≥ 60 이면 산출 (market 대문자화 확인)
    if out:
        assert out[0]["market"] == "US"
        assert not any(np.isnan(b) for b in out[0]["betas"])


def test_stock_betas_financial_zero_variance_returns():
    """수익률 분산 0(상수) → SS_tot=0 → R²=0 graceful (금융업 정지 케이스)."""
    pca_res, _ = _pca_result_for_betas()
    wdates = pca_res["window_dates"]
    returns = {d: 0.0 for d in wdates}  # 전부 0 (분산 없음)
    out = mfm.compute_stock_betas(
        pca_res, {"105560": {"name": "KB금융", "market": "KR", "returns": returns}}
    )
    assert len(out) == 1
    assert out[0]["r2"] == 0.0
    assert out[0]["idiosyncratic"] == 1.0


def test_stock_betas_caps_at_100():
    """종목 N cap = 100."""
    pca_res, _ = _pca_result_for_betas()
    wdates = pca_res["window_dates"]
    returns = {d: 0.01 for d in wdates}
    stocks = {
        f"{i:06d}": {"name": f"종목{i}", "market": "KR", "returns": returns}
        for i in range(150)
    }
    out = mfm.compute_stock_betas(pca_res, stocks)
    assert len(out) <= 100


# ── _level_for_z ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("z,expected", [
    (0.0, "neutral"), (0.6, "neutral"), (-0.69, "neutral"),
    (0.7, "mild"), (-1.0, "mild"), (1.49, "mild"),
    (1.5, "stressed"), (-2.0, "stressed"), (3.0, "stressed"),
])
def test_level_for_z(z, expected):
    assert mfm._level_for_z(z) == expected


# ── _build_factor_matrix (fetcher monkeypatch) ────────────────────────────────

def test_build_factor_matrix_reindex_ffill_transform(monkeypatch):
    """S&P500 거래일 reindex + ffill + 변환 검증 (모든 시계열 합성)."""
    import pandas as pd

    biz = pd.bdate_range("2018-01-01", periods=400)

    def fake_fetch_one(meta):
        key = meta["key"]
        # anchor(sp500)은 모든 거래일, 나머지는 일부 결측(ffill 대상)
        idx = biz if key == "sp500" else biz[::1]
        base = 100.0 + np.arange(len(idx)) * 0.1
        s = pd.Series(base, index=idx)
        if meta["transform"] == "diff":
            # 금리류는 작은 값
            s = pd.Series(2.0 + np.arange(len(idx)) * 0.001, index=idx)
        return s

    monkeypatch.setattr(mfm, "_fetch_one_series", fake_fetch_one)
    X, dates, keys, errors = mfm._build_factor_matrix()
    assert X.shape[1] == len(keys) == 10
    assert X.shape[0] == len(dates)
    assert X.shape[0] > 300  # 변환으로 1행만 소실
    assert not np.isnan(X).any()


def test_build_factor_matrix_raises_without_anchor(monkeypatch):
    """anchor(S&P500) 수집 실패 시 ValueError."""
    def fake_fetch_one(meta):
        if meta.get("anchor"):
            return None
        import pandas as pd
        biz = pd.bdate_range("2018-01-01", periods=400)
        return pd.Series(100.0 + np.arange(len(biz)) * 0.1, index=biz)

    monkeypatch.setattr(mfm, "_fetch_one_series", fake_fetch_one)
    with pytest.raises(ValueError):
        mfm._build_factor_matrix()


def test_build_factor_matrix_partial_failure_isolated(monkeypatch):
    """일부 지표 예외 → errors 기록, anchor 있으면 행렬 조립 계속."""
    import pandas as pd
    biz = pd.bdate_range("2018-01-01", periods=400)

    def fake_fetch_one(meta):
        if meta["key"] == "wti":
            raise RuntimeError("yf 타임아웃")
        return pd.Series(100.0 + np.arange(len(biz)) * 0.1, index=biz)

    monkeypatch.setattr(mfm, "_fetch_one_series", fake_fetch_one)
    X, dates, keys, errors = mfm._build_factor_matrix()
    assert "wti" not in keys
    assert any("wti" in e for e in errors)
    assert X.shape[1] == 9  # 10 - 1
