"""REQ-ANALYST-08, 09, 10: advisory_service 프롬프트 12번 섹션 + 시스템 프롬프트 6규칙.

체제별 차등 (defensive 미표시 / cautious 50% 감산 / accumulation·selective 정상).
"""

import re

import pytest


# ────────────────────────────────────────────────────────────────────────────
# 헬퍼: 최소한의 fundamental/technical 더미
# ────────────────────────────────────────────────────────────────────────────


def _minimal_fundamental(market="KR"):
    """advisory_service._build_prompt가 요구하는 키 세트로 구성."""
    return {
        "current_price": 80000,
        "currency": "KRW" if market == "KR" else "USD",
        "metrics": {
            "per": 12, "pbr": 1.0, "roe": 10.0, "psr": 1.5,
            "ev_ebitda": 8.0, "mktcap": 500_000_000_000,
        },
        "income_stmt": [],
        "balance_sheet": [],
        "cashflow": [],
        "shares_outstanding": 5_000_000,
        "eps": 5000,
        "bps": 80000,
        "interest_coverage": [],
        "valuation_stats": {},
        "quarterly": [],
        "forward_estimates": {},
        "business_description": "",
        "business_keywords": [],
    }


def _minimal_technical():
    return {
        "indicators": {
            "current_signals": {
                "macd_cross": "none", "rsi_signal": "neutral", "rsi_value": 55,
                "stoch_signal": "neutral", "stoch_k": 50, "above_ma20": True,
                "ma5": 80000, "ma20": 80000, "ma60": 80000,
                "ma_alignment": "정배열",
                "atr": 1000, "current_price": 80000,
                "bb_position": 50, "volume_signal": 1.0,
                "volume_5d_avg": 100, "volume_20d_avg": 100,
            },
        },
        "indicators_15m": {}, "indicators_1d": {},
    }


def _consensus_kr_normal():
    """KR 정상 컨센서스 데이터 (target_price 있음, overheated=False)."""
    return {
        "reports": [
            {"broker": "미래에셋", "title": "t1", "target_price": 100000,
             "opinion": "Buy", "date": "2026-04-28",
             "pdf_url": "https://e.com/1.pdf",
             "summary": "메모리 가격 반등으로 영업이익 개선 전망."},
            {"broker": "키움", "title": "t2", "target_price": 95000,
             "opinion": "Buy", "date": "2026-04-26",
             "pdf_url": "https://e.com/2.pdf",
             "summary": "HBM 점유율 확대로 2분기 호실적."},
            {"broker": "한국투자", "title": "t3", "target_price": 88000,
             "opinion": "Hold", "date": "2026-04-22",
             "pdf_url": "https://e.com/3.pdf",
             "summary": "단기 모멘텀 둔화 우려."},
        ],
        "consensus": {
            "target_median": 95000,
            "target_mean": 94333,
            "target_stdev": 5000,
            "target_dispersion": 0.05,
            "upside_pct_median": 18.75,
            "opinion_dist_3": {"buy": 2, "hold": 1, "sell": 0},
            "opinion_dist_raw": {"strong_buy": 0, "buy": 2,
                                 "hold": 1, "sell": 0, "strong_sell": 0},
            "count": 3,
        },
        "history_line": "8.5만(11/15) → 9만(2/2) → 9.5만(4/28)",
        "momentum_signal": "up",
        "consensus_overheated": False,
        "data_source": "naver_research",
    }


def _consensus_kr_overheated():
    c = _consensus_kr_normal()
    c["consensus_overheated"] = True
    c["momentum_signal"] = "strong_up"
    return c


def _consensus_us():
    """US 컨센서스 (target_price=None, 등급 변경 이력 위주)."""
    return {
        "reports": [
            {"broker": "Goldman Sachs", "title": "Upgrade",
             "target_price": None, "opinion": "Overweight",
             "date": "2026-04-15", "pdf_url": "", "summary": ""},
            {"broker": "JPMorgan", "title": "Downgrade",
             "target_price": None, "opinion": "Hold",
             "date": "2026-04-10", "pdf_url": "", "summary": ""},
        ],
        "consensus": {
            "target_median": None,
            "target_mean": None,
            "target_stdev": None,
            "target_dispersion": None,
            "upside_pct_median": None,
            "opinion_dist_3": {"buy": 1, "hold": 1, "sell": 0},
            "opinion_dist_raw": {"strong_buy": 0, "buy": 1,
                                 "hold": 1, "sell": 0, "strong_sell": 0},
            "count": 2,
        },
        "history_line": "",
        "momentum_signal": "flat",
        "consensus_overheated": False,
        "data_source": "yfinance_upgrades",
    }


def _consensus_empty():
    return {
        "reports": [], "consensus": None, "history_line": "",
        "momentum_signal": "flat", "consensus_overheated": False,
        "data_source": "empty",
    }


def _build_research_with_consensus(consensus_data):
    """5카테고리 빈 + analyst_consensus만 포함한 research_data."""
    return {
        "basic_macro": {}, "valuation_band": {}, "management": {},
        "capital_actions": {}, "industry_peers": {},
        "analyst_consensus": consensus_data,
        "categories_ok": 1,
    }


def _build_prompt(research, regime="selective"):
    """advisory_service._build_prompt() 호출 헬퍼."""
    from services.advisory_service import _build_prompt as _bp
    return _bp(
        code="005930", market="KR", name="삼성전자",
        fundamental=_minimal_fundamental(),
        technical=_minimal_technical(),
        graham_data={"graham_number": 100000, "discount_rate": 0.2,
                     "eps": 5000, "bps": 80000, "current_price": 80000,
                     "method": "Graham"},
        macro_ctx={
            "fear_greed": {"value": 50},
            "vix": {"value": 18},
            "buffett": {"ratio": 1.5},
        },
        regime=regime, regime_desc="중립",
        strategy_signals=None,
        research_data=research,
    )


# ────────────────────────────────────────────────────────────────────────────
# REQ-ANALYST-08: 체제별 차등
# ────────────────────────────────────────────────────────────────────────────


class TestPromptSection12:
    def test_section_12_appears_in_selective(self):
        prompt = _build_prompt(_build_research_with_consensus(_consensus_kr_normal()),
                               regime="selective")
        assert "## 12" in prompt
        assert "증권사 컨센서스" in prompt
        assert "중앙 목표가" in prompt
        # 95,000 (천원 단위 콤마) 또는 95000
        assert "95,000" in prompt or "95000" in prompt

    def test_section_12_appears_in_accumulation(self):
        prompt = _build_prompt(_build_research_with_consensus(_consensus_kr_normal()),
                               regime="accumulation")
        assert "## 12" in prompt

    def test_section_12_defensive_shows_with_warning(self):
        """defensive 체제 → 12번 섹션 노출 + 50% 감산 경고 (2026-05-02 변경: 보수성 완화).

        과거 동작: defensive에서 섹션 자체 숨김 → GPT가 매수 신호를 전혀 못 봄.
        새 동작: 섹션은 노출하되 cautious와 동일한 신뢰도 경고로 톤 다운.
        """
        prompt = _build_prompt(_build_research_with_consensus(_consensus_kr_normal()),
                               regime="defensive")
        assert "## 12" in prompt
        assert "증권사 컨센서스" in prompt
        # 50% 감산 또는 신뢰도 경고가 함께 노출되어야 함
        assert ("50%" in prompt) and ("감산" in prompt or "신뢰도" in prompt or "가중" in prompt)

    def test_section_12_cautious_warning(self):
        """cautious 체제 → 50% 감산 경고 라인 포함."""
        prompt = _build_prompt(_build_research_with_consensus(_consensus_kr_normal()),
                               regime="cautious")
        assert "## 12" in prompt
        # 신뢰도 경고: "하락 추세장" or "50%" or "감산"
        assert ("50%" in prompt) and ("감산" in prompt or "신뢰도" in prompt or "가중" in prompt)

    def test_section_12_overheated_warning(self):
        """consensus_overheated=True → 과열 시그널 경고."""
        prompt = _build_prompt(_build_research_with_consensus(_consensus_kr_overheated()),
                               regime="selective")
        assert "## 12" in prompt
        assert "과열" in prompt
        assert "Value Trap" in prompt or "가중" in prompt

    def test_section_12_us_grade_changes(self):
        """US 종목: target_price 없음 → 등급 변경 이력 형식."""
        prompt = _build_prompt(_build_research_with_consensus(_consensus_us()),
                               regime="selective")
        assert "## 12" in prompt
        assert "등급 변경" in prompt
        # 중앙 목표가 라인은 없어야 함 (target_price 부재 시)
        assert "중앙 목표가" not in prompt

    def test_section_12_empty_data_skipped(self):
        """data_source='empty' → 섹션 미포함."""
        prompt = _build_prompt(_build_research_with_consensus(_consensus_empty()),
                               regime="selective")
        assert not re.search(r"##\s*12\.", prompt)

    def test_section_12_history_line_included(self):
        prompt = _build_prompt(_build_research_with_consensus(_consensus_kr_normal()),
                               regime="selective")
        assert "8.5만" in prompt or "추이" in prompt

    def test_section_12_recent_3_reports(self):
        prompt = _build_prompt(_build_research_with_consensus(_consensus_kr_normal()),
                               regime="selective")
        # 최근 3건의 broker 명이 모두 등장
        assert "미래에셋" in prompt
        assert "키움" in prompt
        assert "한국투자" in prompt


# ────────────────────────────────────────────────────────────────────────────
# REQ-ANALYST-11: 호환성 — 5카테고리만 있는 research도 정상
# ────────────────────────────────────────────────────────────────────────────


class TestLegacyCompatibility:
    def test_legacy_5_categories_no_section_12(self):
        """analyst_consensus 키 부재 → 12번 섹션 없음, 정상 동작."""
        legacy = {
            "basic_macro": {}, "valuation_band": {}, "management": {},
            "capital_actions": {}, "industry_peers": {},
        }
        prompt = _build_prompt(legacy, regime="selective")
        assert not re.search(r"##\s*12\.", prompt)


# ────────────────────────────────────────────────────────────────────────────
# REQ-ANALYST-09: 시스템 프롬프트 — Value Trap 6규칙
# ────────────────────────────────────────────────────────────────────────────


class TestSystemPromptValueTrap6:
    def test_value_trap_six_rules_in_system_prompt(self):
        from services.advisory_service import _build_system_prompt
        sp = _build_system_prompt("selective", "중립")
        assert "Value Trap" in sp
        assert "6" in sp  # 6규칙 / 6번째
        assert "consensus_overheated" in sp or "컨센서스 과열" in sp

    def test_critical_consensus_warning_in_system_prompt(self):
        """'증권사 컨센서스를 무비판적으로 수용하지 말 것' 한 줄 추가."""
        from services.advisory_service import _build_system_prompt
        sp = _build_system_prompt("selective", "중립")
        assert ("무비판" in sp) or ("비판적" in sp and "컨센서스" in sp)


# ────────────────────────────────────────────────────────────────────────────
# REQ-ANALYST-10: 사전 계산값 불변
# ────────────────────────────────────────────────────────────────────────────


class TestPrecomputedValuesUnchanged:
    def test_compute_grade_signature_unchanged(self):
        """compute_grade_7point에 analyst_consensus 파라미터 없음."""
        import inspect
        from services.safety_grade import compute_grade_7point
        sig = inspect.signature(compute_grade_7point)
        params = set(sig.parameters.keys())
        # 컨센서스 관련 파라미터 추가 금지
        assert "analyst_consensus" not in params
        assert "consensus" not in params
        assert "consensus_overheated" not in params

    def test_compute_position_size_signature_unchanged(self):
        import inspect
        from services.safety_grade import compute_position_size
        sig = inspect.signature(compute_position_size)
        params = set(sig.parameters.keys())
        assert "analyst_consensus" not in params
        assert "consensus" not in params

    def test_section_14_unaffected_by_consensus(self):
        """7점 등급 사전 계산값 블록은 컨센서스 유무에 동일."""
        without = _build_prompt({}, regime="selective")
        with_data = _build_prompt(_build_research_with_consensus(_consensus_kr_normal()),
                                  regime="selective")

        # "7점 등급 사전 계산값" 블록 추출
        def _extract_grade_block(p):
            # "7점 등급 사전 계산값" ~ "복합 점수" 사이 텍스트
            m = re.search(r"7점 등급 사전 계산값.*?복합 점수.*?\n", p, re.DOTALL)
            return m.group(0) if m else ""

        b1 = _extract_grade_block(without)
        b2 = _extract_grade_block(with_data)
        assert b1 != ""
        assert b2 != ""
        # 두 블록은 동일해야 함 (컨센서스 무관)
        assert b1 == b2
