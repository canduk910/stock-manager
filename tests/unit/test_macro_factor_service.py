"""거시 팩터 모델 서비스/라우터/배치 통합 단위 테스트.

- get_factor_model: 캐시 miss → status=pending, hit → 그대로 반환
- _annotate_user_portfolio: in_portfolio/source 사용자별 재주입
- build_and_cache_factor_model: fetcher/store monkeypatch로 end-to-end (외부 호출 0)
- 라우터/스케줄러 import 가드
"""
import numpy as np
import pytest

from services import macro_service
from services import macro_factor_model as mfm


# ── get_factor_model: pending / hit ──────────────────────────────────────────

def test_get_factor_model_pending_on_miss(monkeypatch):
    monkeypatch.setattr(macro_service, "get_macro_today", lambda cat: None)
    out = macro_service.get_factor_model(user_id=None)
    assert out["status"] == "pending"
    assert "updated_at" in out


def test_get_factor_model_returns_cached(monkeypatch):
    cached = {"status": "ok", "as_of": "2026-06-19", "stock_betas": [], "signal_lights": []}
    monkeypatch.setattr(macro_service, "get_macro_today", lambda cat: cached)
    out = macro_service.get_factor_model(user_id=None)
    assert out["status"] == "ok"
    assert out["as_of"] == "2026-06-19"


def test_get_factor_model_no_calc_on_request_path(monkeypatch):
    """요청 경로에서 build(무거운 PCA)를 절대 호출하지 않음(t3.small 보호)."""
    called = {"build": False}
    monkeypatch.setattr(macro_service, "get_macro_today", lambda cat: None)
    monkeypatch.setattr(
        mfm, "build_and_cache_factor_model",
        lambda: called.__setitem__("build", True) or {},
    )
    macro_service.get_factor_model(user_id=None)
    assert called["build"] is False


# ── _annotate_user_portfolio ─────────────────────────────────────────────────

def test_annotate_user_portfolio_does_not_mutate(monkeypatch):
    model = {
        "stock_betas": [
            {"code": "005930", "market": "KR", "in_portfolio": False, "source": "representative"},
        ]
    }
    # user 조회 실패 시 원본 그대로 반환(graceful)
    out = macro_service._annotate_user_portfolio(model, user_id=999)
    # 원본 betas 객체는 변하지 않음
    assert model["stock_betas"][0]["in_portfolio"] is False
    assert isinstance(out["stock_betas"], list)


# ── build_and_cache_factor_model (end-to-end, monkeypatch) ────────────────────

def test_build_and_cache_end_to_end(monkeypatch):
    """모든 외부 호출 monkeypatch — 행렬/PCA/베타/저장 전체 흐름 검증."""
    import pandas as pd

    biz = pd.bdate_range("2018-01-01", periods=560)

    def fake_fetch_one(meta):
        # 구조 있는 합성 시계열 (지표별 위상차)
        i = [m["key"] for m in mfm.FACTOR_SERIES].index(meta["key"])
        t = np.arange(len(biz))
        if meta["transform"] == "diff":
            base = 2.0 + 0.001 * t + 0.3 * np.sin(t / 20 + i)
        else:
            base = 100.0 * np.exp(0.0003 * t + 0.05 * np.sin(t / 15 + i))
        return pd.Series(base, index=biz)

    def fake_stock_logret(code, market):
        # 윈도우 날짜와 충분히 겹치는 일별 logret
        rng = np.random.default_rng(hash(code) % 1000)
        vals = rng.normal(scale=0.01, size=len(biz))
        return {d.strftime("%Y-%m-%d"): float(v) for d, v in zip(biz, vals)}

    saved = {}
    monkeypatch.setattr(mfm, "_fetch_one_series", fake_fetch_one)
    monkeypatch.setattr(mfm, "_fetch_stock_logret_series", fake_stock_logret)
    monkeypatch.setattr(mfm, "_collect_portfolio_stocks",
                        lambda: ([("005930", "삼성전자", "KR"), ("AAPL", "Apple", "US")], False))
    # save_today는 mfm 네임스페이스에서 import되므로 거기에 패치
    import stock.macro_store as ms
    monkeypatch.setattr(ms, "save_today", lambda cat, res: saved.__setitem__(cat, res))

    result = mfm.build_and_cache_factor_model()

    # 4종 산출물 키 존재
    assert result["status"] == "ok"
    assert "signal_lights" in result and len(result["signal_lights"]) == 5
    assert "explained_history" in result and len(result["explained_history"]) >= 1
    assert "loadings" in result and len(result["loadings"]) == 5
    assert "stock_betas" in result
    assert result["meta"]["n_factors"] == 10
    # 저장 호출됨
    assert "factor_model" in saved
    # 신호등 레벨 유효
    for s in result["signal_lights"]:
        assert s["level"] in ("neutral", "mild", "stressed")
        assert "pc" in s and "label" in s and "z" in s
    # loadings weights 절대값 정렬 + 10개 지표
    for l in result["loadings"]:
        assert len(l["weights"]) == 10
        ws = [abs(w["weight"]) for w in l["weights"]]
        assert ws == sorted(ws, reverse=True)


def test_build_raises_without_anchor(monkeypatch):
    """anchor(S&P500) 수집 실패 → build에서 ValueError 전파."""
    def fake_fetch_one(meta):
        if meta.get("anchor"):
            return None
        import pandas as pd
        biz = pd.bdate_range("2018-01-01", periods=560)
        return pd.Series(100.0 + np.arange(len(biz)) * 0.1, index=biz)

    monkeypatch.setattr(mfm, "_fetch_one_series", fake_fetch_one)
    with pytest.raises(ValueError):
        mfm.build_and_cache_factor_model()


# ── 폴백 대표 리스트 ──────────────────────────────────────────────────────────

def test_collect_portfolio_fallback(monkeypatch):
    """watchlist∪advisory 0건이면 대표 리스트 폴백 + used_fallback=True."""
    monkeypatch.setattr(
        "services.scheduler_service._all_advisory_users_codes", lambda: []
    )
    monkeypatch.setattr(
        "services.scheduler_service._all_watchlist_codes", lambda: []
    )
    stocks, used_fallback = mfm._collect_portfolio_stocks()
    assert used_fallback is True
    assert len(stocks) == len(mfm._REPRESENTATIVE_STOCKS)


# ── import 가드 ───────────────────────────────────────────────────────────────

def test_router_endpoint_registered():
    from routers import macro as macro_router
    paths = {r.path for r in macro_router.router.routes}
    assert "/api/macro/factor-model" in paths


def test_scheduler_job_function_importable():
    from services.scheduler_service import _run_macro_factor_model_job
    assert callable(_run_macro_factor_model_job)
