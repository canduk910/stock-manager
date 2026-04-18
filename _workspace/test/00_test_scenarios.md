# 전체 기능 테스트 시나리오

> 작성일: 2026-04-19
> 작성자: QA Inspector
> 도메인 자문: MarginAnalyst, MacroSentinel, OrderAdvisor

---

## 1. 단위 테스트 (tests/unit/)

### 1.1 stock/utils.py — is_domestic, is_fno

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-001 | test_six_digit_domestic | 6자리 숫자는 국내 | "005930" | True |
| U-002 | test_us_ticker_not_domestic | 영문 티커는 해외 | "AAPL" | False |
| U-003 | test_fno_code_not_domestic | FNO 코드는 국내 아님 | "101S6000" | False |
| U-004 | test_empty_string | 빈 문자열 | "" | False |
| U-005 | test_five_digits | 5자리 숫자 | "12345" | False |
| U-006 | test_seven_digits | 7자리 숫자 | "1234567" | False |
| U-007 | test_fno_index_futures | 지수선물 1xxx | "101S6" | True (is_fno) |
| U-008 | test_fno_index_options | 지수옵션 2xxx | "201S6" | True (is_fno) |
| U-009 | test_fno_stock_futures | 주식선물 3xxx | "301S6" | True (is_fno) |
| U-010 | test_fno_short_code | 4자리 미만 FNO | "1A" | False (is_fno) |
| U-011 | test_fno_six_digit_number | 6자리 숫자는 FNO 아님 | "123456" | False (is_fno) |
| U-012 | test_fno_empty | 빈 문자열 FNO | "" | False (is_fno) |
| U-013 | test_fno_none | None FNO | None | False (is_fno) |

### 1.2 stock/indicators.py — 기술지표 계산

#### 1.2.1 _ema (지수이동평균)

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-020 | test_ema_basic | 기본 EMA 계산 | [1,2,3,4,5], period=3 | 처음 2개 None, 나머지 계산값 |
| U-021 | test_ema_short_data | 데이터 < period | [1,2], period=5 | 전부 None |
| U-022 | test_ema_single_value | period=1 | [10,20,30] | [10, 20, 30] |
| U-023 | test_ema_constant | 동일값 연속 | [5,5,5,5,5], period=3 | 초기 None 이후 전부 5.0 |

#### 1.2.2 _sma (단순이동평균)

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-030 | test_sma_basic | 기본 SMA 계산 | [1,2,3,4,5], period=3 | [None,None,2.0,3.0,4.0] |
| U-031 | test_sma_short_data | 데이터 < period | [1], period=5 | [None] |
| U-032 | test_sma_period_equals_length | period=len | [10,20,30], period=3 | [None,None,20.0] |

#### 1.2.3 _rsi (Wilder RSI)

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-040 | test_rsi_uptrend | 연속 상승 | [i for i in range(20)] | RSI > 70 (overbought) |
| U-041 | test_rsi_downtrend | 연속 하락 | [20-i for i in range(20)] | RSI < 30 (oversold) |
| U-042 | test_rsi_flat | 횡보 | [50]*20 | RSI None (변동 없으면 gains=losses=0) |
| U-043 | test_rsi_short_data | 데이터 <= period | [1]*14 | 전부 None |
| U-044 | test_rsi_all_gains_no_loss | 모두 상승, 하락 없음 | 상승만 16개 | RSI = 100 (avg_loss=0) |

#### 1.2.4 _stoch (Stochastic)

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-050 | test_stoch_overbought | %K >= 80 | 종가 = 최고가 근처 | stoch_signal = "overbought" |
| U-051 | test_stoch_oversold | %K <= 20 | 종가 = 최저가 근처 | stoch_signal = "oversold" |
| U-052 | test_stoch_equal_high_low | 변동 없음 | 고=저 | %K = 50.0 (중립) |

#### 1.2.5 _bollinger (볼린저밴드)

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-060 | test_bb_basic | 기본 BB 계산 | 20개+ 데이터 | upper > mid > lower |
| U-061 | test_bb_constant | 동일값 연속 | [100]*25 | upper=mid=lower=100 (std=0) |
| U-062 | test_bb_short_data | 데이터 < 20 | [1]*10 | 전부 None |

#### 1.2.6 _atr (Average True Range)

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-070 | test_atr_basic | 기본 ATR | OHLCV 20개 | period+1 이후 값 존재 |
| U-071 | test_atr_short_data | 데이터 < period+1 | 10개 | 전부 None |
| U-072 | test_atr_zero_range | 변동 없음 | 고=저=종 | ATR = 0 |

#### 1.2.7 _safe_val

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-080 | test_safe_val_normal | 정상 float | 3.14159 | 3.1416 (4자리) |
| U-081 | test_safe_val_nan | NaN | float('nan') | None |
| U-082 | test_safe_val_inf | Inf | float('inf') | None |
| U-083 | test_safe_val_none | None | None | None |
| U-084 | test_safe_val_neg_inf | -Inf | float('-inf') | None |

#### 1.2.8 calc_technical_indicators (통합)

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-090 | test_empty_ohlcv | 빈 입력 | [] | 기본 구조 반환 (macd_cross="none") |
| U-091 | test_single_bar | 1봉 입력 | [{...}] | 기본 구조 반환 |
| U-092 | test_minimal_ohlcv | 2봉 최소 | [{...},{...}] | volatility_target 계산됨 |
| U-093 | test_full_ohlcv | 60봉+ 입력 | 60개 OHLCV | 모든 지표 계산됨, 구조 검증 |
| U-094 | test_macd_golden_cross | 골든크로스 감지 | MACD > Signal 전환 | macd_cross = "golden" |
| U-095 | test_macd_dead_cross | 데드크로스 감지 | MACD < Signal 전환 | macd_cross = "dead" |
| U-096 | test_ma_alignment_positive | 정배열 | MA5>MA20>MA60 | ma_alignment = "정배열" |
| U-097 | test_ma_alignment_negative | 역배열 | MA5<MA20<MA60 | ma_alignment = "역배열" |
| U-098 | test_ma_alignment_mixed | 혼합 | MA5>MA60>MA20 | ma_alignment = "혼합" |
| U-099 | test_volume_signal | 거래량 신호 | 최신 거래량 / 5일 평균 | volume_signal 계산됨 |
| U-100 | test_bb_position | BB 위치 | 종가 = BB 중심 | bb_position ≈ 50 |
| U-101 | test_volatility_target | 변동성돌파 목표가 | K=0.5 | open + range*0.5 |

### 1.3 services/safety_grade.py — 7점 등급/복합점수/포지션 사이징

#### 1.3.1 개별 점수 함수

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-110 | test_score_discount_4pt | 할인율 > 40% | 45.0 | 4 |
| U-111 | test_score_discount_3pt | 할인율 20-40% | 30.0 | 3 |
| U-112 | test_score_discount_2pt | 할인율 0-20% | 10.0 | 2 |
| U-113 | test_score_discount_1pt | 할인율 <= 0% | -5.0 | 1 |
| U-114 | test_score_discount_none | None | None | 1 |
| U-115 | test_score_discount_boundary_40 | 정확히 40% | 40.0 | 3 (>40이어야 4) |
| U-116 | test_score_discount_boundary_20 | 정확히 20% | 20.0 | 2 (>20이어야 3) |
| U-117 | test_score_discount_boundary_0 | 정확히 0% | 0.0 | 1 (>0이어야 2) |
| U-120 | test_score_per_vs_avg_4pt | PER << 평균 | PER=5, avg=10 (-50%) | 4 |
| U-121 | test_score_per_vs_avg_3pt | PER < 평균 | PER=8, avg=10 (-20%) | 3 |
| U-122 | test_score_per_vs_avg_2pt | PER ≈ 평균 | PER=10, avg=10 (0%) | 2 |
| U-123 | test_score_per_vs_avg_1pt | PER >> 평균 | PER=15, avg=10 (+50%) | 1 |
| U-124 | test_score_per_vs_avg_none | PER None | None, 10 | 2 (중립) |
| U-125 | test_score_per_vs_avg_zero | avg 0 | 10, 0 | 2 (중립) |
| U-130 | test_score_pbr_4pt | PBR < 0.7 | 0.5 | 4 |
| U-131 | test_score_pbr_3pt | PBR 0.7-1.0 | 0.8 | 3 |
| U-132 | test_score_pbr_2pt | PBR 1.0-1.5 | 1.2 | 2 |
| U-133 | test_score_pbr_1pt | PBR > 1.5 | 2.0 | 1 |
| U-134 | test_score_pbr_boundary | 정확히 0.7 | 0.7 | 3 (<0.7이어야 4) |
| U-140 | test_score_debt_4pt | 부채비율 < 50% | 30 | 4 |
| U-141 | test_score_debt_3pt | 부채비율 50-100% | 70 | 3 |
| U-142 | test_score_debt_2pt | 부채비율 100-200% | 150 | 2 |
| U-143 | test_score_debt_1pt | 부채비율 > 200% | 300 | 1 |
| U-150 | test_score_current_ratio_percent | %(150) 입력 | 150 | 3 (1.5배 → 1.5-2.0) |
| U-151 | test_score_current_ratio_decimal | 배수(1.5) 입력 | 1.5 | 2 (1.0-1.5) |
| U-152 | test_score_current_ratio_high | > 2.0 배수 | 2.5 | 4 |
| U-153 | test_score_current_ratio_low | < 1.0 배수 | 0.8 | 1 |
| U-154 | test_score_current_ratio_boundary10 | 정확히 10 | 10 | 2 (10/100=0.1 < 1.0 → 1점? 아님. 10은 >10 아니므로 배수로 간주 → 10 > 2.0 → 4점) |
| U-160 | test_score_fcf_3years | 3년 양수 | 3 | 4 |
| U-161 | test_score_fcf_2years | 2년 양수 | 2 | 3 |
| U-162 | test_score_fcf_1year | 1년 양수 | 1 | 2 |
| U-163 | test_score_fcf_0years | 0년 양수 | 0 | 1 |
| U-170 | test_score_cagr_4pt | CAGR > 10% | 15 | 4 |
| U-171 | test_score_cagr_3pt | CAGR 5-10% | 7 | 3 |
| U-172 | test_score_cagr_2pt | CAGR 0-5% | 3 | 2 |
| U-173 | test_score_cagr_1pt | CAGR < 0% | -5 | 1 |

#### 1.3.2 _count_fcf_years_positive

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-180 | test_fcf_3years_consecutive | 3년 연속 양수 FCF | [양,양,양] | 3 |
| U-181 | test_fcf_break_in_middle | 중간 음수 → 중단 | [양,음,양] | 1 (역순: 양 → 음 break) |
| U-182 | test_fcf_empty | 빈 cashflow | [] | 0 |
| U-183 | test_fcf_with_direct_fcf | fcf 키 직접 제공 | [{fcf: 100}] | 1 |
| U-184 | test_fcf_op_cf_minus_capex | operating_cf - capex 계산 | [{operating_cf: 100, capex: 30}] | 1 (FCF=70 > 0) |

#### 1.3.3 _calc_revenue_cagr

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-190 | test_cagr_positive_growth | 매출 성장 | [100M, 133.1M] 1년 | ≈33.1% |
| U-191 | test_cagr_negative_growth | 매출 감소 | [100M, 80M] 1년 | -20% |
| U-192 | test_cagr_zero_first_revenue | 첫해 매출 0 | [0, 100M] | None |
| U-193 | test_cagr_single_year | 1개 연도 | [{revenue: 100}] | None (< 2년) |
| U-194 | test_cagr_empty | 빈 리스트 | [] | None |
| U-195 | test_cagr_3year | 3년 성장 | [100, 120, 140, 160] | CAGR(100→160, 3년) |

#### 1.3.4 compute_grade_7point (통합)

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-200 | test_grade_A_perfect | 모든 지표 최고 | 28점 | grade="A", valid_entry=True |
| U-201 | test_grade_A_boundary | 24점 | 24점 | grade="A" |
| U-202 | test_grade_Bplus_23 | 23점 | 23점 | grade="B+" |
| U-203 | test_grade_Bplus_20 | 20점 | 20점 | grade="B+" |
| U-204 | test_grade_B_19 | 19점 | 19점 | grade="B" |
| U-205 | test_grade_B_16 | 16점 | 16점 | grade="B" |
| U-206 | test_grade_C_15 | 15점 | 15점 | grade="C", valid_entry=False |
| U-207 | test_grade_C_12 | 12점 | 12점 | grade="C" |
| U-208 | test_grade_D_11 | 11점 | 11점 | grade="D", valid_entry=False |
| U-209 | test_grade_all_none | 모든 지표 None | 빈 dict | score >= 7, grade 검증 |
| U-210 | test_grade_details_structure | details 구조 | 정상 입력 | 7개 항목 전부 존재 |
| U-211 | test_grade_factor_mapping | grade_factor 매핑 | A/B+/B/C/D | 1.0/0.75/0.5/0/0 |

#### 1.3.5 compute_composite_score

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-220 | test_composite_basic | 기본 계산 | PER=10, PBR=1.0, ROE=15, DY=3.5 | (0.1*0.3 + 1.0*0.3 + 0.15*0.25 + 0.035*0.15)*100 ≈ 37.03 |
| U-221 | test_composite_none_metrics | None 입력 | None | None |
| U-222 | test_composite_empty_dict | 빈 dict | {} | None |
| U-223 | test_composite_negative_per | PER 음수 | PER=-5 | PER 역수 0 처리 |
| U-224 | test_composite_zero_per | PER 0 | PER=0 | PER 역수 0 처리 |
| U-225 | test_composite_max_clamp | 극단적 고점수 | PER=1, PBR=0.1, ROE=50 | min(100, ...) |
| U-226 | test_composite_dy_percent | DY % 형태 | DY=3.5 (>1 → %) | /100 변환 |
| U-227 | test_composite_dy_decimal | DY 소수점 형태 | DY=0.035 (<1 → 소수점) | 그대로 사용 |

#### 1.3.6 compute_regime_alignment

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-230 | test_alignment_perfect | 모든 항목 일치 | accumulation, score=28, fcf=3, stock=75 | 100.0 |
| U-231 | test_alignment_grade_below | 등급 미달 | selective, score=12, fcf=3, stock=65 | < 100 |
| U-232 | test_alignment_no_stock_pct | stock_pct None | selective, score=20, fcf=3 | 2항목 가중합 |
| U-233 | test_alignment_none_grade | grade None | selective, None, fcf=3 | grade_align=50 |
| U-234 | test_alignment_defensive | defensive 체제 | defensive, score=20, fcf=3, stock=25 | 등급 미달 감점 |
| U-235 | test_alignment_stock_pct_exact | 주식비중 정확 | ±5%p 이내 | stock_align=100 |
| U-236 | test_alignment_stock_pct_far | 주식비중 초과 | ±20%p 이상 | stock_align=0 |

#### 1.3.7 compute_position_size

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-240 | test_position_A_accumulation | A등급+accumulation | 1억, 500만, 5%, A | target=5%, qty=100 |
| U-241 | test_position_Bplus_selective | B+등급+selective | 1억, 500만, 4%, B+ | target=3%, qty=60 |
| U-242 | test_position_C_skip | C등급 진입 금지 | C등급 | qty=0, "SKIP" |
| U-243 | test_position_D_skip | D등급 진입 금지 | D등급 | qty=0, "SKIP" |
| U-244 | test_position_cash_limited | 예수금 부족 | max>cash | available=cash |
| U-245 | test_position_zero_price | 진입가 0 | entry=0 | qty=0, "SKIP" |
| U-246 | test_position_hold | 자금 부족 | cash=0 | qty=0, "HOLD" |

#### 1.3.8 compute_stop_loss / compute_risk_reward

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-250 | test_stop_loss_A | A등급 -8% | entry=50000, A | 46000 |
| U-251 | test_stop_loss_Bplus | B+등급 -10% | entry=50000, B+ | 45000 |
| U-252 | test_stop_loss_B | B등급 -12% | entry=50000, B | 44000 |
| U-253 | test_stop_loss_C | C등급 진입 금지 | entry=50000, C | None |
| U-254 | test_stop_loss_zero_price | 진입가 0 | entry=0 | None |
| U-260 | test_risk_reward_basic | 기본 계산 | 50000, 46000, 60000 | 2.5 |
| U-261 | test_risk_reward_below_2 | 보류 권고 | 50000, 46000, 55000 | 1.25 |
| U-262 | test_risk_reward_none_inputs | None 입력 | None, None, None | None |
| U-263 | test_risk_reward_stop_above_entry | 손절>진입 | 50000, 55000, 60000 | None |

### 1.4 services/macro_regime.py — 체제 판단

#### 1.4.1 분류 헬퍼

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-300 | test_buffett_low | 버핏 < 0.8 | 0.5 | "low" |
| U-301 | test_buffett_normal | 버핏 0.8-1.2 | 1.0 | "normal" |
| U-302 | test_buffett_high | 버핏 1.2-1.6 | 1.4 | "high" |
| U-303 | test_buffett_extreme | 버핏 >= 1.6 | 2.0 | "extreme" |
| U-304 | test_buffett_none | None | None | "normal" |
| U-305 | test_buffett_boundary_08 | 정확히 0.8 | 0.8 | "normal" (<0.8=low) |
| U-306 | test_buffett_boundary_12 | 정확히 1.2 | 1.2 | "high" (<1.2=normal) |
| U-307 | test_buffett_boundary_16 | 정확히 1.6 | 1.6 | "extreme" (<1.6=high) |
| U-310 | test_fg_extreme_fear | FG < 20 | 10 | "extreme_fear" |
| U-311 | test_fg_fear | FG 20-40 | 30 | "fear" |
| U-312 | test_fg_neutral | FG 40-60 | 50 | "neutral" |
| U-313 | test_fg_greed | FG 60-80 | 70 | "greed" |
| U-314 | test_fg_extreme_greed | FG >= 80 | 90 | "extreme_greed" |
| U-315 | test_fg_vix_override | VIX>35 오버라이드 | FG=90, VIX=36 | "extreme_fear" |
| U-316 | test_fg_none | None | None | "neutral" |
| U-317 | test_fg_vix_boundary_35 | VIX=35 (>35 아님) | FG=90, VIX=35 | "extreme_greed" (오버라이드 안 됨) |
| U-318 | test_fg_vix_boundary_35_01 | VIX=35.01 | FG=90, VIX=35.01 | "extreme_fear" (오버라이드) |
| U-319 | test_fg_string_score | 문자열 score | {"score": "45"} | float("45")=45 → "neutral" |

#### 1.4.2 REGIME_MATRIX 전수 검증 (20셀)

| # | 테스트명 | 설명 | 입력 (buffett, fg) | 기대 체제 |
|---|---------|------|-------------------|----------|
| U-320 | test_matrix_low_extreme_fear | | ("low", "extreme_fear") | accumulation |
| U-321 | test_matrix_low_fear | | ("low", "fear") | accumulation |
| U-322 | test_matrix_low_neutral | | ("low", "neutral") | selective |
| U-323 | test_matrix_low_greed | | ("low", "greed") | cautious |
| U-324 | test_matrix_low_extreme_greed | | ("low", "extreme_greed") | cautious |
| U-325 | test_matrix_normal_extreme_fear | | ("normal", "extreme_fear") | selective |
| U-326 | test_matrix_normal_fear | | ("normal", "fear") | selective |
| U-327 | test_matrix_normal_neutral | | ("normal", "neutral") | cautious |
| U-328 | test_matrix_normal_greed | | ("normal", "greed") | cautious |
| U-329 | test_matrix_normal_extreme_greed | | ("normal", "extreme_greed") | defensive |
| U-330 | test_matrix_high_extreme_fear | | ("high", "extreme_fear") | selective |
| U-331 | test_matrix_high_fear | | ("high", "fear") | cautious |
| U-332 | test_matrix_high_neutral | | ("high", "neutral") | cautious |
| U-333 | test_matrix_high_greed | | ("high", "greed") | defensive |
| U-334 | test_matrix_high_extreme_greed | | ("high", "extreme_greed") | defensive |
| U-335 | test_matrix_extreme_extreme_fear | | ("extreme", "extreme_fear") | cautious |
| U-336 | test_matrix_extreme_fear | | ("extreme", "fear") | defensive |
| U-337 | test_matrix_extreme_neutral | | ("extreme", "neutral") | defensive |
| U-338 | test_matrix_extreme_greed | | ("extreme", "greed") | defensive |
| U-339 | test_matrix_extreme_extreme_greed | | ("extreme", "extreme_greed") | defensive |

#### 1.4.3 하이스테리시스

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-340 | test_hysteresis_fg_boundary_up | FG 39→41 이전 fear | previous=fear, FG=41 | fear 유지 (40+5=45 미만) |
| U-341 | test_hysteresis_fg_boundary_up_clear | FG 39→46 이전 fear | previous=fear, FG=46 | neutral 전환 (45 초과) |
| U-342 | test_hysteresis_fg_boundary_down | FG 41→39 이전 neutral | previous=neutral, FG=39 | neutral 유지 (40-5=35 초과) |
| U-343 | test_hysteresis_fg_vix_override | VIX>35는 버퍼 무시 | VIX=36, previous=neutral | extreme_fear (즉각) |
| U-344 | test_hysteresis_buffett_up | 버핏 0.82 이전 low | previous=low, ratio=0.82 | low 유지 (0.80+0.05=0.85 미만) |
| U-345 | test_hysteresis_buffett_up_clear | 버핏 0.86 이전 low | previous=low, ratio=0.86 | normal 전환 (0.85 초과) |
| U-346 | test_hysteresis_no_previous | 이전 없음 | previous=None | 일반 분류 적용 |
| U-347 | test_hysteresis_fg_exact_buffer | FG 정확히 45 (fear→?) | previous=fear, FG=45 | neutral 전환 (< threshold+5 이므로 45 미포함) |
| U-348 | test_hysteresis_fg_just_below_buffer | FG 44 (fear→?) | previous=fear, FG=44 | fear 유지 (44 < 45) |
| U-349 | test_hysteresis_fg_down_pass | FG 34 (neutral→fear) | previous=neutral, FG=34 | fear 전환 (34 < 35) |
| U-350a | test_hysteresis_buffett_down | 버핏 0.78 이전 normal | previous=normal, ratio=0.78 | normal 유지 (0.78 > 0.75) |
| U-350b | test_hysteresis_buffett_down_pass | 버핏 0.74 이전 normal | previous=normal, ratio=0.74 | low 전환 (0.74 < 0.75) |

#### 1.4.4 determine_regime (통합)

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-360 | test_determine_basic | 기본 체제 결정 | buffett=0.5, fg=10 | accumulation |
| U-361 | test_determine_vix_override_low | VIX>35 + 저평가 | buffett=0.5, fg=90, vix=36 | accumulation (low+extreme_fear) |
| U-362 | test_determine_vix_override_normal | VIX>35 + 정상 | buffett=1.0, fg=70, vix=40 | selective (normal+extreme_fear) |
| U-363 | test_determine_vix_override_high | VIX>35 + 고평가 | buffett=1.4, fg=50, vix=50 | selective (high+extreme_fear) |
| U-364 | test_determine_vix_override_extreme | VIX>35 + 극단 | buffett=1.8, fg=10, vix=36 | cautious (extreme+extreme_fear) |
| U-365 | test_determine_vix_boundary_35 | VIX=35 (미달) | buffett=1.0, fg=90, vix=35 | defensive (normal+extreme_greed) |
| U-366 | test_determine_with_previous | 하이스테리시스 | previous="selective", fg=41 | 이전 유지 가능 |
| U-367 | test_determine_buffett_percent | 버핏 235.2(%) | buffett=235.2 | 2.352 변환 → extreme |
| U-368 | test_determine_buffett_10 | 버핏 10.0 (경계) | buffett=10.0 | 변환 안 됨 (>10이 아님) |
| U-369 | test_determine_buffett_10_1 | 버핏 10.1 | buffett=10.1 | 0.101 변환 → low |
| U-370 | test_determine_vix_dict | VIX dict 형태 | {"vix": {"value": 25}} | vix=25 추출 |
| U-371 | test_determine_vix_float | VIX float 형태 | {"vix": 25} | vix=25 |
| U-372 | test_determine_fg_score | FG score 키 | {"fear_greed": {"score": 45}} | fg=45 |
| U-373 | test_determine_fg_value | FG value 키 | {"fear_greed": {"value": 45}} | fg=45 |
| U-374 | test_determine_fg_string | FG 문자열 score | {"fear_greed": {"score": "45"}} | fg=45.0 |
| U-375 | test_determine_returns_params | 반환값 params | accumulation | REGIME_PARAMS["accumulation"] |
| U-376 | test_determine_returns_desc | 반환값 desc | accumulation | "축적 (탐욕 매수)" |
| U-377 | test_determine_empty_sentiment | 빈 sentiment | {} | cautious (None→normal+neutral) |
| U-378 | test_determine_buffett_indicator_key | buffett_indicator 키 | {"buffett_indicator": {"ratio": 0.5}} | buffett=0.5 |
| U-379 | test_determine_buffett_key | buffett 키 | {"buffett": {"ratio": 0.5}} | buffett=0.5 |

### 1.5 services/exceptions.py — 예외 계층

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-400 | test_service_error_default | 기본 status | ServiceError("err") | status_code=400 |
| U-401 | test_not_found_error | 404 | NotFoundError() | status_code=404 |
| U-402 | test_external_api_error | 502 | ExternalAPIError() | status_code=502 |
| U-403 | test_config_error | 503 | ConfigError() | status_code=503 |
| U-404 | test_payment_required_error | 402 | PaymentRequiredError() | status_code=402 |
| U-405 | test_conflict_error | 409 | ConflictError() | status_code=409 |
| U-406 | test_inheritance | 상속 관계 | NotFoundError() | isinstance(ServiceError) |
| U-407 | test_custom_message | 커스텀 메시지 | NotFoundError("없음") | message="없음" |

### 1.6 services/schemas/advisory_report_v2.py — Pydantic 스키마

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-410 | test_v2_schema_valid | 유효한 v2 리포트 | 완전한 JSON | (True, schema, None) |
| U-411 | test_v2_invalid_grade | 잘못된 등급 | 종목등급="X" | (False, None, error) |
| U-412 | test_v2_score_out_of_range | 점수 범위 초과 | 등급점수=30 (>28) | (False, None, error) |
| U-413 | test_v2_composite_out_of_range | 복합점수 초과 | 복합점수=101 | (False, None, error) |
| U-414 | test_v2_missing_required | 필수 필드 누락 | 종합투자의견 없음 | (False, None, error) |
| U-415 | test_extract_v2_fields | 필드 추출 | 완전한 JSON | grade, grade_score 등 |
| U-416 | test_extract_v2_partial | 부분 JSON | 일부 필드만 | 누락 필드 None |
| U-417 | test_v2_extra_keys_allowed | 추가 키 허용 | Config extra="allow" | 검증 통과 |

### 1.7 stock/cache.py — TTL 캐시

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-420 | test_sanitize_nan | NaN → None | float('nan') | None |
| U-421 | test_sanitize_inf | Inf → None | float('inf') | None |
| U-422 | test_sanitize_nested_dict | 중첩 dict NaN | {"a": float('nan')} | {"a": None} |
| U-423 | test_sanitize_nested_list | 중첩 list NaN | [float('nan'), 1.0] | [None, 1.0] |
| U-424 | test_sanitize_normal | 정상값 통과 | 3.14 | 3.14 |
| U-425 | test_sanitize_string | 문자열 통과 | "hello" | "hello" |
| U-426 | test_sanitize_none | None 통과 | None | None |

### 1.8 services/report_service.py — 보고서 Markdown (기존 + 확장)

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| U-430 | test_markdown_with_recs | 추천 있는 보고서 | 1건 추천 | "# 일일 투자 보고서" 포함 |
| U-431 | test_markdown_empty_recs | 추천 없는 보고서 | 0건 | "매수 추천 없음" 포함 |
| U-432 | test_markdown_no_regime | 체제 데이터 없음 | regime=None | "시장 체제" 미포함 |
| U-433 | test_markdown_multiple_recs | 다건 추천 | 2건 | "매수 추천 (2건)" 포함 |

---

## 2. 통합 테스트 (tests/integration/)

### 2.1 db/repositories/watchlist_repo.py

| # | 테스트명 | 설명 | 기대 결과 |
|---|---------|------|----------|
| I-001 | test_add_and_get | 추가 후 조회 | name, code 일치 |
| I-002 | test_add_duplicate | 중복 추가 | False 반환 |
| I-003 | test_remove | 삭제 후 조회 | None |
| I-004 | test_remove_nonexistent | 없는 항목 삭제 | False |
| I-005 | test_update_memo | 메모 수정 | 변경된 memo |
| I-006 | test_all_items | 전체 조회 | 정렬 순서 확인 |
| I-007 | test_market_filter | KR/US 구분 | market별 독립 |
| I-008 | test_save_and_get_order | 순서 저장/조회 | position 순서 |
| I-009 | test_save_order_replaces | 순서 재저장 | 기존 삭제 후 새 순서 |

### 2.2 db/repositories/order_repo.py

| # | 테스트명 | 설명 | 기대 결과 |
|---|---------|------|----------|
| I-020 | test_insert_order | 주문 삽입 | symbol, side 일치 |
| I-021 | test_insert_order_pending | PENDING 상태 삽입 | status="PENDING" |
| I-022 | test_update_order_status_filled | PLACED→FILLED | filled_at 설정 |
| I-023 | test_update_order_status_cancelled | PLACED→CANCELLED | status 변경 |
| I-024 | test_get_order_by_id | ID로 조회 | 일치 |
| I-025 | test_get_order_by_order_no | 주문번호로 조회 | 최신 것 반환 |
| I-026 | test_list_orders_filter | 필터 조회 | symbol/market/status 필터 |
| I-027 | test_list_active_orders | 활성 주문만 | PENDING/PLACED/PARTIAL |
| I-028 | test_update_order_details | 가격/수량 수정 | 변경 반영 |
| I-029 | test_update_nonexistent | 없는 주문 수정 | None |
| I-030 | test_insert_reservation | 예약주문 삽입 | condition_type 일치 |
| I-031 | test_list_reservations | 예약 목록 | status 필터 |
| I-032 | test_update_reservation_status | 상태 전이 | WAITING→TRIGGERED |
| I-033 | test_delete_reservation | 삭제 | True |

### 2.3 db/repositories/advisory_repo.py

| # | 테스트명 | 설명 | 기대 결과 |
|---|---------|------|----------|
| I-040 | test_add_stock | 자문종목 추가 | True |
| I-041 | test_add_stock_duplicate | 중복 추가 | False |
| I-042 | test_remove_stock | 삭제 | True |
| I-043 | test_all_stocks | 전체 조회 | 추가일 역순 |
| I-044 | test_get_stock | 단건 조회 | code/market 대소문자 무관 |
| I-045 | test_save_cache | 캐시 저장/조회 | fundamental/technical 일치 |
| I-046 | test_save_cache_update | 캐시 업데이트 | updated_at 갱신 |
| I-047 | test_save_report | 리포트 저장 | report_json 일치 |
| I-048 | test_get_latest_report | 최신 리포트 | 마지막 것 반환 |
| I-049 | test_list_reports | 리포트 목록 | limit 적용 |
| I-050 | test_save_portfolio_report | 포트폴리오 리포트 | 저장 확인 |
| I-051 | test_get_latest_portfolio_report | 최신 포트폴리오 | 마지막 것 반환 |

### 2.4 db/repositories/market_board_repo.py

| # | 테스트명 | 설명 | 기대 결과 |
|---|---------|------|----------|
| I-060 | test_add_item | 종목 추가 | True |
| I-061 | test_add_duplicate | 중복 | False |
| I-062 | test_remove_item | 삭제 | True |
| I-063 | test_all_items | 전체 조회 | 정렬 |
| I-064 | test_save_and_get_order | 순서 저장 | position 순서 |

### 2.5 db/repositories/stock_info_repo.py

| # | 테스트명 | 설명 | 기대 결과 |
|---|---------|------|----------|
| I-070 | test_get_stock_info_empty | 없는 종목 | None |
| I-071 | test_upsert_and_get | 저장 후 조회 | 값 일치 |
| I-072 | test_batch_get | 배치 조회 | (code, market) 키 dict |
| I-073 | test_is_stale_no_data | 데이터 없음 | True (stale) |
| I-074 | test_is_stale_fresh | 방금 저장 | False (not stale) |

### 2.6 db/repositories/macro_repo.py

| # | 테스트명 | 설명 | 기대 결과 |
|---|---------|------|----------|
| I-080 | test_save_and_get_today | 오늘 캐시 저장/조회 | result 일치 |
| I-081 | test_get_today_empty | 없는 카테고리 | None |
| I-082 | test_save_upsert | 같은 날 재저장 | 덮어쓰기 |
| I-083 | test_cleanup_old | 30일 이전 삭제 | 삭제 건수 반환 |

### 2.7 db/repositories/backtest_repo.py

| # | 테스트명 | 설명 | 기대 결과 |
|---|---------|------|----------|
| I-090 | test_create_job | Job 생성 | status="submitted" |
| I-091 | test_update_job_result | 결과 업데이트 | status="completed", metrics 저장 |
| I-092 | test_update_job_status | 상태 변경 | failed 시 completed_at 설정 |
| I-093 | test_get_job | Job 조회 | 일치 |
| I-094 | test_get_job_nonexistent | 없는 Job | None |
| I-095 | test_get_latest_metrics | 최신 메트릭 | 가장 최근 completed job |
| I-096 | test_list_jobs_filter | 필터 조회 | symbol/market 필터 |
| I-097 | test_save_strategy | 전략 저장 | name 일치 |
| I-098 | test_save_strategy_upsert | 같은 이름 재저장 | 덮어쓰기 |
| I-099 | test_list_strategies | 전략 목록 | strategy_type 필터 |

### 2.8 db/repositories/tax_repo.py

| # | 테스트명 | 설명 | 기대 결과 |
|---|---------|------|----------|
| I-100 | test_insert_transaction | 거래 삽입 | 필드 일치 |
| I-101 | test_list_transactions_by_year | 연도 필터 | 해당 연도만 |
| I-102 | test_list_transactions_by_symbol | 종목 필터 | 해당 종목만 |
| I-103 | test_list_transactions_by_side | 매수/매도 필터 | side별 |
| I-104 | test_get_transaction | 단건 조회 | 일치 |
| I-105 | test_delete_transaction | 삭제 | True |
| I-106 | test_exists_by_key | 중복 체크 | True/False |
| I-107 | test_insert_calculation | 양도세 계산 결과 | 필드 일치 |
| I-108 | test_list_calculations | 계산 결과 목록 | year/method 필터 |
| I-109 | test_delete_calculations_by_year | 연도별 삭제 | 삭제 건수 |
| I-110 | test_insert_fifo_lot | FIFO lot 삽입 | 필드 일치 |
| I-111 | test_list_fifo_lots | FIFO lot 목록 | 정렬 확인 |
| I-112 | test_delete_fifo_lots_by_year | 연도별 lot 삭제 | 삭제 건수 |

### 2.9 db/repositories/report_repo.py (기존 + 확장)

| # | 테스트명 | 설명 | 기대 결과 |
|---|---------|------|----------|
| I-120 | test_save_recommendation | 추천 저장 | id > 0 |
| I-121 | test_save_recommendations_batch | 배치 저장 | N개 id |
| I-122 | test_update_status_approved | 승인 | approved_at 설정 |
| I-123 | test_update_status_closed_pnl | 청산 + PnL | realized_pnl_pct 계산 |
| I-124 | test_list_by_market | 시장별 조회 | 필터 적용 |
| I-125 | test_performance_stats | 성과 통계 | total, win_rate |
| I-126 | test_save_regime | 체제 저장 | regime 일치 |
| I-127 | test_regime_upsert | 같은 날 재저장 | 덮어쓰기 |
| I-128 | test_latest_regime | 최신 체제 | 날짜순 |
| I-129 | test_save_daily_report | 일일 보고서 | markdown 일치 |
| I-130 | test_mark_telegram_sent | 텔레그램 발송 | True |

---

## 3. API 테스트 (tests/api/)

### 3.1 routers/watchlist.py — /api/watchlist

| # | 테스트명 | 설명 | 메서드/경로 | 기대 결과 |
|---|---------|------|-----------|----------|
| A-001 | test_list_watchlist | 목록 조회 | GET /api/watchlist | 200, list |
| A-002 | test_add_watchlist | 추가 | POST /api/watchlist | 201 |
| A-003 | test_add_watchlist_duplicate | 중복 추가 | POST /api/watchlist | 409 |
| A-004 | test_remove_watchlist | 삭제 | DELETE /api/watchlist/{code} | 200 |
| A-005 | test_remove_nonexistent | 없는 종목 삭제 | DELETE /api/watchlist/999999 | 404 |
| A-006 | test_update_memo | 메모 수정 | PATCH /api/watchlist/{code} | 200 |
| A-007 | test_get_dashboard | 대시보드 | GET /api/watchlist/dashboard | 200 |
| A-008 | test_get_stock_info | 종목 정보 | GET /api/watchlist/info/{code} | 200 |
| A-009 | test_get_order | 순서 조회 | GET /api/watchlist/order | 200 |
| A-010 | test_save_order | 순서 저장 | PUT /api/watchlist/order | 200 |

### 3.2 routers/order.py — /api/order

| # | 테스트명 | 설명 | 메서드/경로 | 기대 결과 |
|---|---------|------|-----------|----------|
| A-020 | test_place_order_no_kis | KIS 키 없이 발주 | POST /api/order/place | 503 (ConfigError) |
| A-021 | test_get_buyable | 매수가능 조회 | GET /api/order/buyable | 200 or 503 |
| A-022 | test_get_open_orders | 미체결 조회 | GET /api/order/open | 200 or 503 |
| A-023 | test_get_executions | 체결 내역 | GET /api/order/executions | 200 or 503 |
| A-024 | test_get_order_history | 주문 이력 | GET /api/order/history | 200 |
| A-025 | test_sync_orders | 대사 | POST /api/order/sync | 200 or 503 |
| A-026 | test_create_reservation | 예약주문 생성 | POST /api/order/reserve | 201 |
| A-027 | test_list_reservations | 예약 목록 | GET /api/order/reserves | 200 |
| A-028 | test_delete_reservation | 예약 삭제 | DELETE /api/order/reserve/{id} | 200 |
| A-029 | test_get_fno_price | FNO 현재가 | GET /api/order/fno-price | 200 or 503 |

### 3.3 routers/advisory.py — /api/advisory

| # | 테스트명 | 설명 | 메서드/경로 | 기대 결과 |
|---|---------|------|-----------|----------|
| A-040 | test_list_stocks | 자문종목 목록 | GET /api/advisory | 200 |
| A-041 | test_add_stock | 종목 추가 | POST /api/advisory | 201 |
| A-042 | test_add_stock_duplicate | 중복 추가 | POST /api/advisory | 409 |
| A-043 | test_remove_stock | 종목 삭제 | DELETE /api/advisory/{code} | 200 |
| A-044 | test_refresh_data | 데이터 갱신 | POST /api/advisory/{code}/refresh | 200 |
| A-045 | test_get_data | 캐시 데이터 | GET /api/advisory/{code}/data | 200 or 404 |
| A-046 | test_analyze_no_openai | AI분석 키 없음 | POST /api/advisory/{code}/analyze | 503 |
| A-047 | test_get_ohlcv | OHLCV 차트 | GET /api/advisory/{code}/ohlcv | 200 |
| A-048 | test_get_report_history | 리포트 이력 | GET /api/advisory/{code}/reports | 200 |
| A-049 | test_get_report | 최신 리포트 | GET /api/advisory/{code}/report | 200 or 404 |

### 3.4 routers/detail.py — /api/detail

| # | 테스트명 | 설명 | 메서드/경로 | 기대 결과 |
|---|---------|------|-----------|----------|
| A-060 | test_get_financials | 재무 테이블 | GET /api/detail/financials/{symbol} | 200 |
| A-061 | test_get_valuation | 밸류에이션 | GET /api/detail/valuation/{symbol} | 200 |
| A-062 | test_get_report | 종합 리포트 | GET /api/detail/report/{symbol} | 200 |
| A-063 | test_financials_us | 해외 재무 | GET /api/detail/financials/AAPL?market=US | 200 |

### 3.5 routers/balance.py — /api/balance

| # | 테스트명 | 설명 | 메서드/경로 | 기대 결과 |
|---|---------|------|-----------|----------|
| A-070 | test_get_balance_no_key | KIS 키 없음 | GET /api/balance | 503 (ConfigError) |
| A-071 | test_get_balance_response_shape | 응답 구조 | GET /api/balance | holdings, summary, fno_enabled |

### 3.6 routers/macro.py — /api/macro

| # | 테스트명 | 설명 | 메서드/경로 | 기대 결과 |
|---|---------|------|-----------|----------|
| A-080 | test_get_indices | 지수 데이터 | GET /api/macro/indices | 200 |
| A-081 | test_get_news | 뉴스 | GET /api/macro/news | 200 |
| A-082 | test_get_sentiment | 심리 지표 | GET /api/macro/sentiment | 200 |
| A-083 | test_get_investor_quotes | 투자자 발언 | GET /api/macro/investor-quotes | 200 |
| A-084 | test_get_summary | 종합 요약 | GET /api/macro/summary | 200 |

### 3.7 routers/market_board.py — /api/market-board

| # | 테스트명 | 설명 | 메서드/경로 | 기대 결과 |
|---|---------|------|-----------|----------|
| A-090 | test_get_new_highs_lows | 신고가/신저가 | GET /api/market-board/new-highs-lows | 200 |
| A-091 | test_post_sparklines | 스파크라인 | POST /api/market-board/sparklines | 200 |
| A-092 | test_list_custom_stocks | 별도 등록 목록 | GET /api/market-board/custom-stocks | 200 |
| A-093 | test_add_custom_stock | 별도 등록 | POST /api/market-board/custom-stocks | 201 |
| A-094 | test_remove_custom_stock | 별도 등록 삭제 | DELETE /api/market-board/custom-stocks/{code} | 204 |
| A-095 | test_get_board_order | 순서 조회 | GET /api/market-board/order | 200 |
| A-096 | test_save_board_order | 순서 저장 | PUT /api/market-board/order | 200 |

### 3.8 routers/screener.py — /api/screener

| # | 테스트명 | 설명 | 메서드/경로 | 기대 결과 |
|---|---------|------|-----------|----------|
| A-100 | test_get_stocks | 스크리너 목록 | GET /api/screener/stocks | 200 |
| A-101 | test_get_stocks_with_filters | 필터 적용 | GET /api/screener/stocks?per_max=15 | 200 |

### 3.9 routers/earnings.py — /api/earnings

| # | 테스트명 | 설명 | 메서드/경로 | 기대 결과 |
|---|---------|------|-----------|----------|
| A-110 | test_get_filings_kr | 국내 공시 | GET /api/earnings/filings?market=KR | 200 |
| A-111 | test_get_filings_us | 해외 공시 | GET /api/earnings/filings?market=US | 200 |
| A-112 | test_get_filings_date_range | 날짜 범위 | GET /api/earnings/filings?start=2026-01-01 | 200 |

### 3.10 routers/search.py — /api/search

| # | 테스트명 | 설명 | 메서드/경로 | 기대 결과 |
|---|---------|------|-----------|----------|
| A-120 | test_search_stocks | 종목 검색 | GET /api/search?q=삼성 | 200, list |
| A-121 | test_search_empty | 빈 쿼리 | GET /api/search?q= | 200, [] |

### 3.11 routers/pipeline.py — /api/pipeline

| # | 테스트명 | 설명 | 메서드/경로 | 기대 결과 |
|---|---------|------|-----------|----------|
| A-130 | test_run_pipeline | 파이프라인 실행 | POST /api/pipeline/run | 200 |
| A-131 | test_run_pipeline_sync | 동기 실행 | POST /api/pipeline/run-sync | 200 |
| A-132 | test_get_status | 상태 조회 | GET /api/pipeline/status | 200 |

### 3.12 routers/portfolio_advisor.py — /api/portfolio-advisor

| # | 테스트명 | 설명 | 메서드/경로 | 기대 결과 |
|---|---------|------|-----------|----------|
| A-140 | test_analyze | 포트폴리오 분석 | POST /api/portfolio-advisor/analyze | 200 or 503 |
| A-141 | test_get_history | 이력 조회 | GET /api/portfolio-advisor/history | 200 |
| A-142 | test_get_report | 단건 조회 | GET /api/portfolio-advisor/history/{id} | 200 or 404 |

### 3.13 routers/backtest.py — /api/backtest

| # | 테스트명 | 설명 | 메서드/경로 | 기대 결과 |
|---|---------|------|-----------|----------|
| A-150 | test_mcp_status | MCP 상태 | GET /api/backtest/status | 200 |
| A-151 | test_get_presets | 프리셋 목록 | GET /api/backtest/presets | 200 |
| A-152 | test_get_indicators | 지표 목록 | GET /api/backtest/indicators | 200 |
| A-153 | test_run_preset | 프리셋 실행 | POST /api/backtest/run/preset | 200 or 503 |
| A-154 | test_get_result | 결과 조회 | GET /api/backtest/result/{id} | 200 or 404 |
| A-155 | test_get_history | 이력 조회 | GET /api/backtest/history | 200 |

### 3.14 routers/tax.py — /api/tax

| # | 테스트명 | 설명 | 메서드/경로 | 기대 결과 |
|---|---------|------|-----------|----------|
| A-160 | test_get_summary | 양도세 요약 | GET /api/tax/summary | 200 |
| A-161 | test_get_transactions | 거래 목록 | GET /api/tax/transactions | 200 |
| A-162 | test_add_transaction | 수동 입력 | POST /api/tax/transactions | 201 |
| A-163 | test_delete_transaction | 거래 삭제 | DELETE /api/tax/transactions/{id} | 200 or 404 |
| A-164 | test_sync_transactions | KIS 동기화 | POST /api/tax/sync | 200 or 503 |
| A-165 | test_recalculate | 재계산 | POST /api/tax/recalculate | 200 |
| A-166 | test_get_calculations | 계산 결과 | GET /api/tax/calculations | 200 |
| A-167 | test_get_simulation_holdings | 시뮬레이션 보유 | GET /api/tax/simulate/holdings | 200 |
| A-168 | test_simulate_tax | 가상 매도 | POST /api/tax/simulate | 200 |

### 3.15 routers/report.py — /api/reports (기존 + 확장)

| # | 테스트명 | 설명 | 메서드/경로 | 기대 결과 |
|---|---------|------|-----------|----------|
| A-170 | test_list_reports | 보고서 목록 | GET /api/reports | 200, items/total |
| A-171 | test_list_reports_market | 시장 필터 | GET /api/reports?market=KR | 200 |
| A-172 | test_get_report_not_found | 없는 보고서 | GET /api/reports/99999 | 404 |
| A-173 | test_list_recommendations | 추천 목록 | GET /api/reports/recommendations | 200 |
| A-174 | test_get_recommendation_not_found | 없는 추천 | GET /api/reports/recommendations/99999 | 404 |
| A-175 | test_performance_stats | 성과 통계 | GET /api/reports/performance | 200 |
| A-176 | test_list_regimes | 체제 이력 | GET /api/reports/regimes | 200 |
| A-177 | test_latest_regime | 최신 체제 | GET /api/reports/regimes/latest | 200 |

### 3.16 routers/quote.py — WebSocket

| # | 테스트명 | 설명 | 메서드/경로 | 기대 결과 |
|---|---------|------|-----------|----------|
| A-180 | test_quote_ws_connect | WS 연결 | WS /ws/quote/005930 | 연결 성공 |
| A-181 | test_quote_ws_overseas | 해외 WS | WS /ws/quote/AAPL?market=US | 연결 성공 |
| A-182 | test_execution_notice_ws | 체결통보 WS | WS /ws/execution-notice | 연결 성공 |

---

## 4. 도메인 로직 테스트 (투자 전문가 자문 기반)

### 4.1 Graham Number 계산 (MarginAnalyst)

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| D-001 | test_graham_number_basic | sqrt(22.5 * EPS * BPS) | EPS=5000, BPS=50000 | sqrt(22.5*5000*50000) = 75000 |
| D-002 | test_graham_negative_eps | 적자 기업 | EPS=-1000 | None (음수 불가) |
| D-003 | test_graham_discount | 할인율 계산 | GN=75000, price=50000 | 50% |
| D-004 | test_graham_premium | 프리미엄 | GN=40000, price=50000 | -20% |

### 4.2 FIFO 양도세 (OrderAdvisor)

| # | 테스트명 | 설명 | 입력 | 기대 결과 |
|---|---------|------|------|----------|
| D-010 | test_fifo_single_buy_sell | 1매수 1매도 | 100주 매수@$10 → 50주 매도@$15 | 양도차익 = 50*($15-$10) |
| D-011 | test_fifo_multiple_buy | 다건 매수 소진 | 100@$10 + 100@$12 → 150주 매도@$15 | 100*($15-$10) + 50*($15-$12) |
| D-012 | test_fifo_basic_deduction | 기본공제 250만원 | 총 양도차익 300만원 | 과세대상 50만원 |
| D-013 | test_fifo_tax_rate | 세율 22% | 과세대상 100만원 | 세금 22만원 |
| D-014 | test_fifo_same_day | 동일일 매수+매도 | 같은 날 | 매도 시점 이전 매수만 소진 |
| D-015 | test_fifo_commission | 수수료 반영 | 0.25% 기본 | 양도차익에서 차감 |

---

## 5. 경계면 정합성 테스트

### 5.1 API 응답 → 프론트엔드 Shape

| # | 검증 대상 | 생산자 | 소비자 |
|---|----------|--------|--------|
| B-001 | 관심종목 대시보드 | GET /api/watchlist/dashboard | WatchlistPage |
| B-002 | 잔고 응답 | GET /api/balance | BalancePage |
| B-003 | 주문 이력 | GET /api/order/history | OrderPage |
| B-004 | AI자문 데이터 | GET /api/advisory/{code}/data | DetailPage |
| B-005 | OHLCV 차트 | GET /api/advisory/{code}/ohlcv | TechnicalPanel |
| B-006 | 매크로 심리 | GET /api/macro/sentiment | MacroPage |

### 5.2 라우트 등록 정합성

| # | 검증 대상 | 확인 포인트 |
|---|----------|------------|
| B-010 | main.py include_router prefix | App.jsx Route path와 일치 |
| B-011 | Header.jsx Link | 실제 라우트 존재 여부 |

---

## 6. 테스트 우선순위

### P0 (즉시 구현)
- U-110~U-211: safety_grade.py 전체 (투자 의사결정 핵심)
- U-300~U-359: macro_regime.py 전체 (체제 판단 핵심)
- U-090~U-101: indicators.py calc_technical_indicators
- U-400~U-407: exceptions.py (예외 계층 기반)
- I-001~I-009: watchlist_repo (기본 CRUD)
- I-020~I-033: order_repo (주문 핵심)

### P1 (단기)
- U-020~U-084: indicators.py 개별 함수
- U-220~U-263: 복합점수/포지션사이징/손절
- U-410~U-417: Pydantic v2 스키마
- I-040~I-051: advisory_repo
- I-100~I-112: tax_repo
- A-001~A-010: watchlist API
- A-020~A-029: order API

### P2 (중기)
- 나머지 통합 테스트
- 나머지 API 테스트
- 도메인 로직 테스트
- 경계면 정합성 테스트

---

## 7. 기존 conftest.py 패턴

```python
# tests/conftest.py — 그대로 유지
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()

@pytest.fixture
def client():
    from main import app
    return TestClient(app)
```

- **통합 테스트**: `db_session` fixture 사용, Repository 직접 인스턴스화
- **API 테스트**: `client` fixture 사용, TestClient로 HTTP 호출
- **단위 테스트**: fixture 불필요, 순수 함수 직접 호출

---

## 요약

| 카테고리 | 시나리오 수 | 커버리지 |
|---------|-----------|---------|
| 단위 테스트 | ~120개 | indicators, safety_grade, macro_regime, exceptions, schemas, cache, report_service |
| 통합 테스트 | ~60개 | 9개 Repository 전체 CRUD |
| API 테스트 | ~70개 | 16개 Router 전체 엔드포인트 |
| 도메인 테스트 | ~15개 | Graham Number, FIFO, 포지션 사이징 |
| 경계면 테스트 | ~10개 | API↔프론트, 라우팅 정합성 |
| **총계** | **~275개** | |
