"""AI자문 서비스 레이어.

종목별 AI 투자 리포트를 생성하는 핵심 서비스. 데이터 수집부터 GPT 호출, 결과 저장까지의
전체 파이프라인을 관리한다.

데이터 흐름:
  refresh_stock_data()               generate_ai_report()
  ┌──────────────────┐               ┌──────────────────────────────────┐
  │ _collect_fundamental (7~8 task)│   │ advisory_cache → 프롬프트 조립    │
  │ _collect_technical (15분봉)    │──→│ _build_system_prompt (4전략+7점) │
  │ _collect_strategy_signals(MCP) │   │ _build_prompt (재무+기술+매크로)  │
  │         ↓                      │   │         ↓                        │
  │ advisory_cache에 JSON 저장     │   │ OpenAI GPT 호출 (재시도 3단계)   │
  └──────────────────┘               │         ↓                        │
                                      │ _parse_report → Pydantic v2 검증│
                                      │         ↓                        │
                                      │ advisory_reports DB 저장          │
                                      └──────────────────────────────────┘

재시도 전략 3단계:
1) 토큰 잘림(finish_reason=="length"): 10000→12000 토큰으로 재시도, 2차 실패 시 저장 거부
2) Pydantic v2 검증 실패: 추가 지침과 함께 1회 재시도
3) 일반 에러(네트워크/rate limit 등): 2초 backoff 후 1회 재시도

의존 관계:
- stock/advisory_fetcher.py → 15분봉 OHLCV + 기술지표 + 사업 개요
- stock/dart_fin.py → 국내 DART 재무제표
- stock/yf_client.py → 해외 yfinance 재무데이터
- stock/advisory_store.py → 캐시/리포트 DB CRUD
- services/macro_regime.py → 공용 체제 판단
- services/safety_grade.py → 7점 등급 사전 계산
- services/backtest_service.py → MCP 전략 신호 (선택)
"""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import logging

from config import OPENAI_API_KEY, OPENAI_MODEL

from stock import advisory_store, advisory_fetcher
from stock.utils import is_domestic
from services import financial_ratios
from services.exceptions import (
    ConfigError, ExternalAPIError, NotFoundError, PaymentRequiredError,
)
from services.macro_regime import (
    determine_regime as _shared_determine_regime,
    REGIME_DESC,
    get_regime_params as _get_regime_params_cycle,
    get_margin_requirement as _get_margin_requirement_cycle,
)

logger = logging.getLogger(__name__)


# ── 공유 캐시 stampede 방지 (2026-05-12) ─────────────────────────────────────
# 동시 N명이 동일 (code, market) refresh 호출 시 첫 호출만 외부 API 수집,
# 나머지는 Lock 대기 후 캐시 hit 반환. threading.Lock 사용 (FastAPI는 동기 핸들러 threadpool).
# perf_counter() 기반 메모리 플래그로 timezone 무관 — DB updated_at은 KST tz-aware ISO이고
# 호스트 시각이 UTC(CI 등)인 경우 naive 비교 시 ±9h 오차로 윈도우 우회가 무효화될 수 있어 분리.
_REFRESH_LOCKS: dict[tuple[str, str], threading.Lock] = {}
_REFRESH_LOCKS_GUARD = threading.Lock()
_REFRESH_LAST_DONE: dict[tuple[str, str], float] = {}
_REFRESH_RECENT_SECONDS = 5.0


def _get_refresh_lock(code: str, market: str) -> threading.Lock:
    """(code, market) 키별 Lock을 lazy 생성 + 메모이즈."""
    key = (code.upper(), market.upper())
    with _REFRESH_LOCKS_GUARD:
        lock = _REFRESH_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _REFRESH_LOCKS[key] = lock
        return lock


# ── 공개 API ──────────────────────────────────────────────────────────────────

def refresh_stock_data(code: str, market: str, name: str, user_id: int = 1) -> dict:
    """전체 데이터 수집 → advisory_cache 저장 → 저장된 캐시 반환.

    2026-05-12 변경:
      - 공유 캐시 stampede 방지: (code, market) 키별 Lock으로 동시 호출 1회만 fetch
      - 4단계 ThreadPoolExecutor 병렬 실행: max(단계)≈3s, 직렬 대비 단축
      - 부분 실패 허용: 한 단계 예외 발생 시 다른 단계 결과 보존, 실패 필드는 빈 dict
    """
    from services import _telemetry as _tel
    import time as _time

    key = (code.upper(), market.upper())
    lock = _get_refresh_lock(code, market)
    acquired = lock.acquire(timeout=120)
    if not acquired:
        _tel.record_event("advisory.refresh.lock_timeout")
        raise ExternalAPIError("동일 종목 새로고침이 진행 중입니다. 잠시 후 다시 시도해주세요.")
    try:
        # Lock 획득 직후 stampede 우회 — 직전 호출이 방금 채웠으면 fetcher 생략
        # perf_counter() 단조 증가, timezone 무관
        last_done = _REFRESH_LAST_DONE.get(key)
        if last_done is not None and (_time.perf_counter() - last_done) < _REFRESH_RECENT_SECONDS:
            existing = advisory_store.get_cache(user_id, code, market)
            if existing:
                _tel.record_event("advisory.refresh.stampede_skip")
                return existing

        _t0 = _time.perf_counter()
        # 4단계 병렬 실행
        results = {"fundamental": {}, "technical": {}, "strategy_signals": None, "research_data": {}}
        phase_times = {}

        def _run_fundamental():
            t = _time.perf_counter()
            try:
                return "fundamental", _collect_fundamental(code, market, name, user_id), _time.perf_counter() - t, None
            except Exception as e:
                return "fundamental", {}, _time.perf_counter() - t, e

        def _run_technical():
            t = _time.perf_counter()
            try:
                return "technical", _collect_technical(code, market), _time.perf_counter() - t, None
            except Exception as e:
                return "technical", {}, _time.perf_counter() - t, e

        def _run_strategy():
            t = _time.perf_counter()
            try:
                return "strategy_signals", _collect_strategy_signals(code, market), _time.perf_counter() - t, None
            except Exception as e:
                return "strategy_signals", None, _time.perf_counter() - t, e

        def _run_research():
            t = _time.perf_counter()
            try:
                return "research_data", _collect_research(code, market, name), _time.perf_counter() - t, None
            except Exception as e:
                return "research_data", {}, _time.perf_counter() - t, e

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [
                pool.submit(_run_fundamental),
                pool.submit(_run_technical),
                pool.submit(_run_strategy),
                pool.submit(_run_research),
            ]
            for fut in as_completed(futures):
                phase, val, dur, err = fut.result()
                results[phase] = val
                phase_times[phase] = dur
                if err is not None:
                    logger.warning("refresh phase %s failed for %s: %s", phase, code, err)

        # 텔레메트리 (병렬이어도 각 phase wall-time 기록)
        _tel.observe("advisory.phase.fundamental.duration_ms", phase_times.get("fundamental", 0) * 1000.0)
        _tel.observe("advisory.phase.technical.duration_ms", phase_times.get("technical", 0) * 1000.0)
        _tel.observe("advisory.phase.strategy_signals.duration_ms", phase_times.get("strategy_signals", 0) * 1000.0)
        _tel.observe("advisory.phase.research.duration_ms", phase_times.get("research_data", 0) * 1000.0)
        _tel.observe("advisory.refresh.total_duration_ms", (_time.perf_counter() - _t0) * 1000.0)
        _tel.record_event("advisory.refresh.calls")

        advisory_store.save_cache(
            user_id, code, market,
            results["fundamental"], results["technical"],
            strategy_signals=results["strategy_signals"],
            research_data=results["research_data"],
        )
        _REFRESH_LAST_DONE[key] = _time.perf_counter()
        return advisory_store.get_cache(user_id, code, market) or {}
    finally:
        lock.release()


def _collect_research(code: str, market: str, name: str) -> dict:
    """리서치 데이터 수집 (실패 시 빈 dict)."""
    try:
        from stock.research_collector import collect_all_research
        return collect_all_research(code, market, name)
    except Exception as e:
        logger.warning("리서치 데이터 수집 실패 %s: %s", code, e)
        return {}


def generate_ai_report(
    code: str,
    market: str,
    name: str,
    user_id: int = 1,
    user_comment: Optional[str] = None,
) -> dict:
    """저장된 캐시 데이터를 기반으로 OpenAI GPT-5.4 리포트 생성.

    Phase 3: max_completion_tokens 10000 기본, 재시도 시 12000.
    finish_reason=="length" 1차 재시도, 2차 실패 시 ExternalAPIError → 저장 거부.
    Pydantic v2 검증 실패 시 1회 재시도.

    user_comment: 사용자 가설/의견. 시스템 프롬프트 후미 가이드 블록 + user 메시지에 echo.
    GPT 응답 JSON에 user_commentary_evaluation 섹션이 추가됨(코멘트 있을 때만).
    """
    if not OPENAI_API_KEY:
        raise ConfigError("OPENAI_API_KEY가 설정되지 않았습니다.")

    cache = advisory_store.get_cache(user_id, code, market)
    if not cache:
        raise NotFoundError("분석 데이터가 없습니다. 먼저 새로고침을 해주세요.")

    fundamental = cache.get("fundamental") or {}
    technical = cache.get("technical") or {}
    strategy_signals = cache.get("strategy_signals")  # MCP 전략 신호 (없으면 None)
    research_data = cache.get("research_data") or {}

    model = OPENAI_MODEL
    graham_data = _calc_graham_number(fundamental, market)

    # 매크로 컨텍스트 수집 (캐시 활용, 실패 시 빈 dict)
    macro_ctx = _get_macro_context()
    regime, regime_desc = _determine_regime(macro_ctx)

    # 경기 사이클 컨텍스트 수집 (신규: 보수성 완화 위해 cycle×regime 조합 판단)
    cycle_ctx = _get_cycle_context()

    # 항상 통합 프롬프트 (v2/v3 분기 없음)
    system_prompt = _build_system_prompt(regime, regime_desc, cycle_ctx, user_comment=user_comment)
    prompt = _build_prompt(code, market, name, fundamental, technical,
                           graham_data, macro_ctx, regime, regime_desc,
                           strategy_signals, research_data, cycle_ctx,
                           user_comment=user_comment)

    def _call_openai(max_tokens: int, extra_user_msg: str = "", check_quota: bool = True) -> tuple[str, str]:
        """AI Gateway를 통한 OpenAI 호출. (content, finish_reason) 반환."""
        from services.ai_gateway import call_openai_chat
        user_content = prompt + extra_user_msg
        resp = call_openai_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            user_id=user_id,
            service_name="advisory_report",
            check_quota=check_quota,
            model=model,
            max_completion_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        finish = resp.choices[0].finish_reason or "stop"
        return content, finish

    try:
        import time as _time
        from services.ai_gateway import AiQuotaExceededError

        # 통합 v3: 16000 기본, 20000 재시도
        base_tokens = 16000
        retry_tokens = 20000

        content, finish_reason = _call_openai(base_tokens)

        # 토큰 잘림 1차 재시도
        if finish_reason == "length":
            logger.warning("종목 자문 응답 토큰 잘림 1차 (%s), %d로 재시도", code, retry_tokens)
            _time.sleep(1)
            content, finish_reason = _call_openai(retry_tokens, check_quota=False)
            if finish_reason == "length":
                logger.error("종목 자문 응답 토큰 잘림 2차 (%s), 저장 거부", code)
                raise ExternalAPIError("응답이 토큰 제한으로 잘렸습니다. 다시 시도해주세요.")

        report = _parse_report(content)

        # Pydantic v3 검증
        from services.schemas.advisory_report_v3 import validate_v3_report
        ok, _, err = validate_v3_report(report)

        if not ok:
            logger.warning("v3 검증 실패 (%s): %s — 1회 재시도", code, err[:200] if err else "")
            _time.sleep(1)
            retry_msg = "\n\n응답을 반드시 유효한 JSON으로 작성하세요. schema_version='v3' 필수 필드를 누락하지 마세요."
            content2, finish2 = _call_openai(base_tokens, retry_msg, check_quota=False)
            if finish2 == "length":
                logger.warning("v3 재시도도 토큰 잘림 (%s)", code)
            report = _parse_report(content2)

    except (ConfigError, NotFoundError, PaymentRequiredError, ExternalAPIError, AiQuotaExceededError):
        raise
    except Exception as e:
        err_str = str(e)
        if "insufficient_quota" in err_str or "429" in err_str:
            raise PaymentRequiredError(
                "OpenAI API 크레딧이 부족합니다. platform.openai.com에서 결제 정보를 확인해주세요.",
            )
        # 일반 에러 1회 재시도 (backoff 2초)
        import time as _time
        logger.warning("OpenAI 1차 호출 실패 (%s): %s — 2초 후 재시도", code, err_str[:200])
        _time.sleep(2)
        try:
            content, finish_reason = _call_openai(14000, check_quota=False)
            report = _parse_report(content)
        except Exception as e2:
            raise ExternalAPIError(f"OpenAI 호출 실패: {str(e2)}")

    # 정량 필드 추출 → DB 저장 (항상 v3)
    from services.schemas.advisory_report_v3 import extract_v3_fields
    v2_fields = extract_v3_fields(report)

    report_id = advisory_store.save_report(
        user_id, code, market, model, report,
        grade=v2_fields.get("grade"),
        grade_score=v2_fields.get("grade_score"),
        composite_score=v2_fields.get("composite_score"),
        regime_alignment=v2_fields.get("regime_alignment"),
        schema_version=v2_fields.get("schema_version", "v1"),
        value_trap_warning=v2_fields.get("value_trap_warning", False),
    )

    # 사전 계산 vs GPT 등급 gap 로깅
    gpt_grade = v2_fields.get("grade")
    if gpt_grade:
        logger.info("리포트 저장 [%s %s]: GPT등급=%s, schema=%s, VT=%s",
                     code, gpt_grade, v2_fields.get("schema_version"),
                     v2_fields.get("value_trap_warning"))

    return advisory_store.get_latest_report(user_id, code, market) or {}


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _extract_sector_tier_from_fundamental(
    income_stmt: list, bs_cf: dict
) -> str:
    """기본적분석 결과에서 sector_tier 추출 (REQ-SECTOR-02/03, 2026-05-16).

    fetch_income_detail_annual / fetch_bs_cf_annual 응답에 dart_fin이 부착한
    sector_tier를 통합. 두 응답 모두 부재 시 "general" 보수적 기본값.
    """
    # income_stmt 첫 row의 sector_tier (REQ-SECTOR-02 dart_fin 추가)
    if income_stmt and isinstance(income_stmt, list):
        for row in income_stmt:
            tier = (row or {}).get("sector_tier") if isinstance(row, dict) else None
            if tier:
                return tier
    # bs_cf dict 최상위 sector_tier (REQ-SECTOR-02 dart_fin 추가)
    if isinstance(bs_cf, dict):
        tier = bs_cf.get("sector_tier")
        if tier:
            return tier
    return "general"


def _attach_ratio_analysis(collected: dict) -> dict:
    """fundamental 수집 결과에 4축 재무비율 평가(ratio_analysis) 추가 (REQ-SCREEN-02).

    추가 외부 호출 0건 — 이미 수집한 income_stmt/balance_sheet/cashflow/metrics/
    sector_tier를 순수 함수 compute_ratio_analysis에 전달. 산출 실패(예외) 시
    None 할당 + 로깅, fundamental 응답 전체는 정상 반환(부분 실패 격리).
    """
    try:
        collected["ratio_analysis"] = financial_ratios.compute_ratio_analysis(
            collected.get("income_stmt") or [],
            collected.get("balance_sheet") or [],
            collected.get("cashflow") or [],
            collected.get("metrics") or {},
            sector_tier=collected.get("sector_tier", "general"),
        )
    except Exception as exc:  # noqa: BLE001 — 부분 실패 격리(advisory_service 기존 패턴)
        logger.error("ratio_analysis 산출 실패 (격리됨): %s", exc, exc_info=True)
        collected["ratio_analysis"] = None
    return collected


def _collect_fundamental(code: str, market: str, name: str, user_id: int = 1) -> dict:
    """기본적 분석 데이터 수집 + 4축 재무비율 평가 부착 (REQ-SCREEN-02)."""
    if market == "KR":
        collected = _collect_fundamental_kr(code, name, user_id)
    else:
        collected = _collect_fundamental_us(code, name, user_id)
    return _attach_ratio_analysis(collected)


def _collect_fundamental_kr(code: str, name: str, user_id: int = 1) -> dict:
    """국내 종목 기본적 분석 데이터 수집.

    ThreadPoolExecutor 7개 task 매핑표:
    | Task         | 함수                                | 데이터               | 소스      |
    |--------------|-------------------------------------|---------------------|-----------|
    | f_income     | dart_fin.fetch_income_detail_annual  | 손익계산서 (10년)     | DART      |
    | f_bs_cf      | dart_fin.fetch_bs_cf_annual          | 대차대조표+현금흐름(10년)| DART    |
    | f_metrics    | fetch_market_metrics                 | PER/PBR/ROE/시총    | yfinance  |
    | f_segments   | advisory_fetcher.fetch_segments_kr   | 사업 개요+키워드      | DART+GPT  |
    | f_forward    | fetch_forward_estimates_yf           | Forward PE/EPS      | yfinance  |
    | f_val_stats  | advisory_fetcher.fetch_valuation_stats| PER/PBR 5년 통계   | yfinance  |
    | f_quarterly  | dart_fin.fetch_quarterly_financials  | 분기 실적 (8분기)    | DART      |
    """
    from concurrent.futures import ThreadPoolExecutor
    from stock import dart_fin
    from stock.market import fetch_market_metrics
    from stock.yf_client import fetch_forward_estimates_yf

    with ThreadPoolExecutor(max_workers=7) as pool:
        f_income = pool.submit(dart_fin.fetch_income_detail_annual, code, 10)
        f_bs_cf = pool.submit(dart_fin.fetch_bs_cf_annual, code, 10)
        f_metrics = pool.submit(fetch_market_metrics, code)
        f_forward = pool.submit(fetch_forward_estimates_yf, code, True)
        f_val_stats = pool.submit(advisory_fetcher.fetch_valuation_stats, code, "KR")
        f_quarterly = pool.submit(dart_fin.fetch_quarterly_financials, code, 8)
        # REQ-SECTOR-03: segments_history는 income_stmt 완료 후 sector_tier 전파하여 호출
        # (병렬화 손실 < GPT 비용/품질 효과 — bank_holding 부문 사전 hint)
        income_stmt = f_income.result()
        bs_cf = f_bs_cf.result()
        balance_sheet = bs_cf.get("balance_sheet", [])
        cashflow = bs_cf.get("cashflow", [])

        # sector_tier 추출 (income_stmt 첫 행 또는 bs_cf 응답에서 — 모두 동일값)
        sector_tier = _extract_sector_tier_from_fundamental(income_stmt, bs_cf)

        # segments_history는 sector_tier 전파를 위해 income 완료 후 호출
        f_segments_history = pool.submit(
            advisory_fetcher.fetch_segments_history_kr, code, name,
            user_id=user_id, sector_tier=sector_tier,
        )

        metrics_raw = f_metrics.result()
        metrics = _build_metrics_kr(metrics_raw, balance_sheet, income_stmt)
        forward_estimates = f_forward.result()
        valuation_stats = f_val_stats.result()
        quarterly = f_quarterly.result()
        segments_history_data = f_segments_history.result()

    # 파이차트용 segments + description/keywords — DART 통합 호출 1회 결과 재사용 (GPT 호출 0건 추가)
    # 2026-05-10: 사업 개요는 DART 부문별 매출표를 컨텍스트로 GPT가 생성 (신빙성↑).
    history_years = segments_history_data.get("years_data", []) if isinstance(segments_history_data, dict) else []
    if history_years:
        segments_data = {
            "segments": history_years[-1].get("segments", []),
            "description": segments_history_data.get("description", "") if isinstance(segments_history_data, dict) else "",
            "keywords": segments_history_data.get("keywords", []) if isinstance(segments_history_data, dict) else [],
        }
    else:
        segments_data = {"segments": [], "description": "", "keywords": []}

    # 하위호환: 구 캐시가 list일 수 있음
    if isinstance(segments_data, dict):
        segments = segments_data.get("segments", [])
        biz_desc = segments_data.get("description", "")
        biz_keywords = segments_data.get("keywords", [])
    else:
        segments = segments_data if isinstance(segments_data, list) else []
        biz_desc = ""
        biz_keywords = []

    business_model = advisory_fetcher.fetch_business_model(
        code, name, "KR",
        segments_dict={"segments": segments, "description": biz_desc, "keywords": biz_keywords},
        financial_dict={"income_stmt": income_stmt, "cashflow": cashflow},
        user_id=user_id,
    )

    # REQ-SEGMENT-03: metric 필드 추출 (revenue_share / operating_income_share)
    segments_metric = (
        segments_history_data.get("metric", "revenue_share")
        if isinstance(segments_history_data, dict)
        else "revenue_share"
    )
    return {
        "income_stmt": income_stmt,
        "balance_sheet": balance_sheet,
        "cashflow": cashflow,
        "metrics": metrics,
        "segments": segments,
        "business_description": biz_desc,
        "business_keywords": biz_keywords,
        "business_model": business_model,
        "forward_estimates": forward_estimates,
        "valuation_stats": valuation_stats,  # Phase 2-2
        "quarterly": quarterly,              # Phase 2-3
        # REQ-SECTOR-03: 업종 분류 (bank_holding/insurance/securities/general)
        "sector_tier": sector_tier,
        # REQ-SEGMENT-03: 매출비중 분모 표기 (revenue_share / operating_income_share)
        "segments_metric": segments_metric,
        # Phase 1A (2026-05-10): 5년치 매출비중 추이 — 표시 전용. composite_score 미반영.
        "segments_history": segments_history_data.get("years_data", []) if isinstance(segments_history_data, dict) else [],
        "segments_highlights": segments_history_data.get("highlights") if isinstance(segments_history_data, dict) else None,
        "segments_history_source": segments_history_data.get("source") if isinstance(segments_history_data, dict) else None,
    }


def _collect_fundamental_us(code: str, name: str = "", user_id: int = 1) -> dict:
    """해외 종목 기본적 분석 데이터 수집.

    ThreadPoolExecutor 8개 task — 모두 yfinance 기반 (DART 미사용).
    국내 _collect_fundamental_kr과 동일한 반환 구조를 유지하여 하위 호출자가
    시장 구분 없이 동일하게 처리할 수 있다.
    """
    from concurrent.futures import ThreadPoolExecutor
    from stock.yf_client import (
        fetch_income_detail_yf,
        fetch_balance_sheet_yf,
        fetch_cashflow_yf,
        fetch_metrics_yf,
        fetch_segments_yf,
        fetch_forward_estimates_yf,
        fetch_quarterly_financials_yf,
    )

    with ThreadPoolExecutor(max_workers=8) as pool:
        f_income = pool.submit(fetch_income_detail_yf, code, 10)
        f_bs = pool.submit(fetch_balance_sheet_yf, code, 10)
        f_cf = pool.submit(fetch_cashflow_yf, code, 10)
        f_metrics = pool.submit(fetch_metrics_yf, code)
        f_segments = pool.submit(fetch_segments_yf, code)
        f_forward = pool.submit(fetch_forward_estimates_yf, code, False)
        f_val_stats = pool.submit(advisory_fetcher.fetch_valuation_stats, code, "US")
        f_quarterly = pool.submit(fetch_quarterly_financials_yf, code, 8)

        income_stmt = f_income.result()
        balance_sheet = f_bs.result()
        cashflow = f_cf.result()
        metrics = f_metrics.result()
        segments_data = f_segments.result()
        forward_estimates = f_forward.result()
        valuation_stats = f_val_stats.result()
        quarterly = f_quarterly.result()

    # 하위호환: 구 캐시가 list일 수 있음
    if isinstance(segments_data, dict):
        segments = segments_data.get("segments", [])
        biz_desc = segments_data.get("description", "")
        biz_keywords = segments_data.get("keywords", [])
    else:
        segments = segments_data if isinstance(segments_data, list) else []
        biz_desc = ""
        biz_keywords = []

    business_model = advisory_fetcher.fetch_business_model(
        code, name or code, "US",
        segments_dict={"segments": segments, "description": biz_desc, "keywords": biz_keywords},
        financial_dict={"income_stmt": income_stmt, "cashflow": cashflow},
        user_id=user_id,
    )

    return {
        "income_stmt": income_stmt,
        "balance_sheet": balance_sheet,
        "cashflow": cashflow,
        "metrics": metrics,
        "segments": segments,
        "business_description": biz_desc,
        "business_keywords": biz_keywords,
        "business_model": business_model,
        "forward_estimates": forward_estimates,
        "valuation_stats": valuation_stats,  # Phase 2-2
        "quarterly": quarterly,              # Phase 2-3
        # REQ-SECTOR-03: US 종목은 항상 general (한국 금융지주 분류 미적용)
        "sector_tier": "general",
        "segments_metric": "revenue_share",
        # Phase 1A: US는 yfinance 한계로 segments_history 미지원. 빈 배열 반환(프론트 분기 단순화).
        "segments_history": [],
        "segments_highlights": None,
        "segments_history_source": None,
    }


def _build_metrics_kr(
    raw: Optional[dict],
    balance_sheet: list | None = None,
    income_stmt: list | None = None,
) -> dict:
    """stock/market.py fetch_market_metrics + 재무데이터 → advisory 표준 형식.

    balance_sheet/income_stmt에서 ROA, 부채비율, 유동비율, PSR, PBR(대안) 계산.
    """
    base = raw or {}
    per = base.get("per")
    pbr = base.get("pbr")
    roe = base.get("roe")
    mktcap = base.get("mktcap")
    market_type = base.get("market_type")

    # 대차대조표 최신 연도 값
    bs_latest = (balance_sheet or [])[-1] if balance_sheet else None
    debt_to_equity = None
    current_ratio = None
    total_assets = None
    total_equity = None
    if bs_latest:
        debt_to_equity = bs_latest.get("debt_ratio")
        current_ratio = bs_latest.get("current_ratio")
        total_assets = bs_latest.get("total_assets")
        total_equity = bs_latest.get("total_equity")

    # 손익계산서 최신 연도 값
    is_latest = (income_stmt or [])[-1] if income_stmt else None
    revenue = None
    net_income = None
    if is_latest:
        revenue = is_latest.get("revenue")
        net_income = is_latest.get("net_income")

    # ROA = 순이익 / 총자산 × 100
    roa = None
    if net_income is not None and total_assets and total_assets > 0:
        roa = round(net_income / total_assets * 100, 2)

    # PSR = 시가총액 / 매출액
    psr = None
    if mktcap and revenue and revenue > 0:
        psr = round(mktcap / revenue, 2)

    # PBR: yfinance에서 None이면 시가총액/자본총계로 대체 계산
    if pbr is None and mktcap and total_equity and total_equity > 0:
        pbr = round(mktcap / total_equity, 2)

    # EPS (주당순이익) — DART 우선, 없으면 net_income/shares fallback
    eps = None
    if is_latest:
        eps = is_latest.get("eps")
    if not eps and net_income and net_income > 0:
        shares = base.get("shares")
        if shares and shares > 0:
            eps = round(net_income / shares)

    # Graham Number = sqrt(22.5 × EPS × BPS)
    graham_number = None
    if eps and eps > 0 and pbr and pbr > 0:
        shares = base.get("shares")
        if mktcap and shares and shares > 0:
            price = mktcap / shares
            bps = price / pbr
            import math
            graham_number = round(math.sqrt(22.5 * eps * bps))

    return {
        "per": per,
        "pbr": pbr,
        "roe": roe,
        "market_cap": mktcap,
        "market_type": market_type,
        "psr": psr,
        "ev_ebitda": None,  # 순부채 데이터 필요, 추후 지원
        "roa": roa,
        "debt_to_equity": debt_to_equity,
        "current_ratio": current_ratio,
        "eps": eps,
        "graham_number": graham_number,
        "dividend_yield": base.get("dividend_yield"),
        "dividend_per_share": base.get("dividend_per_share"),
    }


def _collect_technical(code: str, market: str) -> dict:
    """기술적 분석 데이터 수집 (15분봉 + 지표)."""
    if market == "KR":
        ohlcv = advisory_fetcher.fetch_15min_ohlcv_kr(code)
    else:
        ohlcv = advisory_fetcher.fetch_15min_ohlcv_us(code)

    indicators = advisory_fetcher.calc_technical_indicators(ohlcv)

    return {
        "ohlcv": ohlcv,
        "indicators": indicators,
    }


def _collect_strategy_signals(code: str, market: str) -> Optional[dict]:
    """KIS AI Extensions 전략 신호 수집 (MCP 비활성화 시 None).

    MCP 서버가 비활성화(KIS_MCP_ENABLED=false)이거나 연결 실패 시 None을 반환하여
    전략 신호 없이도 AI 리포트가 정상 생성되도록 graceful degrade를 보장한다.
    """
    try:
        from services.backtest_service import get_strategy_signals
        return get_strategy_signals(code, market)
    except Exception as e:
        logger.debug("전략 신호 수집 실패 [%s]: %s", code, e)
        return None


def _calc_graham_number(fundamental: dict, market: str) -> dict:
    """Graham Number = sqrt(22.5 × EPS × BPS) 계산.
    BPS 직접 데이터 없으면 price/PBR 역산 (KR/US 공통).
    EPS <= 0 이면 Graham Number = None.
    """
    import math as _math
    metrics = fundamental.get("metrics") or {}
    income  = fundamental.get("income_stmt") or []
    per = metrics.get("per")
    pbr = metrics.get("pbr")

    eps: Optional[float] = None
    if income:
        raw_eps = income[-1].get("eps")
        if raw_eps is not None:
            try:
                eps = float(raw_eps)
            except (TypeError, ValueError):
                eps = None

    bps: Optional[float] = None
    method = "N/A"
    if per and pbr and per > 0 and pbr > 0 and eps and eps > 0:
        estimated_price = eps * per
        bps = round(estimated_price / pbr, 2)
        method = "PBR역산"

    graham_number: Optional[float] = None
    if eps and bps and eps > 0 and bps > 0:
        graham_number = round(_math.sqrt(22.5 * eps * bps), 2)

    current_price: Optional[float] = None
    if eps and per and per > 0:
        current_price = round(eps * per, 0)
    else:
        mc = metrics.get("market_cap")
        sh = metrics.get("shares")
        if mc and sh and sh > 0:
            current_price = round(mc / sh, 2)

    discount_rate: Optional[float] = None
    if graham_number and current_price and current_price > 0:
        discount_rate = round((graham_number - current_price) / current_price * 100, 1)

    return {
        "graham_number": graham_number,
        "eps": round(eps, 2) if eps else None,
        "bps": bps,
        "discount_rate": discount_rate,
        "method": method,
    }


def _get_macro_context() -> dict:
    """매크로 심리 데이터 수집 (캐시 활용, 실패 시 빈 dict)."""
    try:
        from services import macro_service
        return macro_service.get_sentiment()
    except Exception as e:
        logger.debug("매크로 컨텍스트 수집 실패: %s", e)
        return {}


def _determine_regime(sentiment: dict) -> tuple[str, str]:
    """sentiment → (regime, regime_desc) 반환 — 공용 모듈 위임.

    2차원 버핏×공포탐욕 매트릭스 + VIX>35 오버라이드 적용.
    """
    result = _shared_determine_regime(sentiment)
    return result["regime"], result["regime_desc"]


def _get_cycle_context() -> dict:
    """경기 사이클 국면 데이터 수집. 실패 시 빈 dict.

    portfolio_advisor와 동일 함수 — 향후 macro_service.get_macro_cycle()로 통합 가능.
    """
    try:
        from stock import macro_fetcher
        from services.macro_cycle import determine_cycle_phase
        inputs = macro_fetcher.fetch_cycle_inputs()
        return determine_cycle_phase(inputs)
    except Exception as e:
        logger.debug("경기 사이클 수집 실패: %s", e)
        return {}


# ── 프롬프트 빌더 (services/advisory_prompt.py로 분리, 2026-06-20) ──────────────
# 순수 문자열 조립 함수 + 체제 안전마진 상수. 기존 import 경로/네임스페이스 호환을 위해
# re-export. generate_ai_report() 및 routers/pipeline은 변경 없음.
# 도메인 주의: 7점 등급/손절/Value Trap 문자열은 safety_grade.py와 의도적 3중 일관성 → 무수정 이동.
from services.advisory_prompt import (  # noqa: E402,F401
    _REGIME_MARGIN,
    _build_macro_section,
    _build_strategy_signal_section,
    _CYCLE_REGIME_RULES,
    _format_cycle_regime_rule,
    _build_system_prompt,
    _format_money,
    _build_consensus_section,
    _build_prompt,
    _fmt,
    _parse_report,
)


# ── 보고서 챗봇 (services/advisory_chat.py로 분리, 2026-06-20) ──────────────────
# 기존 import 경로 호환을 위해 re-export. routers/advisory.py 등은 변경 없음.
from services.advisory_chat import (  # noqa: E402,F401
    chat_with_report,
    _trim_chat_history,
    _validate_chat_messages,
    _CHAT_HISTORY_MAX_TURNS,
    _CHAT_MESSAGE_MAX_CHARS,
    _CHAT_SYSTEM_TEMPLATE,
)

