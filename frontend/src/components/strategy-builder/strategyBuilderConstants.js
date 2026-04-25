/**
 * 전략빌더 상수 정의.
 *
 * KIS AI Extensions MCP가 지원하는 83개 기술지표 + 66종 캔들패턴을 프론트엔드에 정적 정의.
 * 빌더 UI의 지표 카탈로그, 조건 연산자, 가격 필드, 프리셋 전략 등을 export한다.
 *
 * @see docs/KIS_AI_EXTENSIONS_ANALYSIS.md
 * @see components/backtest/StrategySelector.jsx (PARAM_KR 매핑)
 */

// ────────────────────────────────────────────────────────────
// 1. INDICATOR_CATALOG — 지표 ID를 키로 하는 카탈로그 (83개 + 66 캔들)
// ────────────────────────────────────────────────────────────

/** @typedef {{ label: string, default: number, min: number, max: number, step: number }} ParamSpec */
/** @typedef {{ nameKo: string, nameEn: string, category: string, description: string, params: Record<string, ParamSpec>, outputs: string[], defaultOutput: string }} IndicatorDef */

/** @type {Record<string, IndicatorDef>} */
export const INDICATOR_CATALOG = {
  // ═══════════════════════════════════════════════════════════
  // 이동평균 (moving_average) — 3개
  // ═══════════════════════════════════════════════════════════
  sma: {
    nameKo: '단순이동평균',
    nameEn: 'Simple Moving Average',
    category: 'moving_average',
    description: '일정 기간 종가의 산술 평균. 추세 방향 판단의 기본 지표.',
    params: {
      period: { label: '기간', default: 20, min: 2, max: 200, step: 1 },
    },
    outputs: ['value'],
    defaultOutput: 'value',
  },
  ema: {
    nameKo: '지수이동평균',
    nameEn: 'Exponential Moving Average',
    category: 'moving_average',
    description: '최근 가격에 더 큰 가중치를 부여하는 이동평균. SMA보다 민감.',
    params: {
      period: { label: '기간', default: 20, min: 2, max: 200, step: 1 },
    },
    outputs: ['value'],
    defaultOutput: 'value',
  },
  vwap: {
    nameKo: 'VWAP',
    nameEn: 'Volume Weighted Average Price',
    category: 'moving_average',
    description: '거래량 가중 평균 가격. 기관 매매의 기준선으로 활용.',
    params: {},
    outputs: ['value'],
    defaultOutput: 'value',
  },

  // ═══════════════════════════════════════════════════════════
  // 모멘텀 (momentum) — 5개
  // ═══════════════════════════════════════════════════════════
  rsi: {
    nameKo: 'RSI',
    nameEn: 'Relative Strength Index',
    category: 'momentum',
    description: '상승/하락 강도의 비율. 70 이상 과매수, 30 이하 과매도.',
    params: {
      period: { label: '기간', default: 14, min: 2, max: 100, step: 1 },
    },
    outputs: ['value'],
    defaultOutput: 'value',
  },
  macd: {
    nameKo: 'MACD',
    nameEn: 'Moving Average Convergence Divergence',
    category: 'momentum',
    description: '두 이동평균의 차이와 시그널선. 추세 전환 포착에 활용.',
    params: {
      fast:   { label: '빠른선', default: 12, min: 2, max: 50, step: 1 },
      slow:   { label: '느린선', default: 26, min: 5, max: 100, step: 1 },
      signal: { label: '시그널', default: 9, min: 2, max: 50, step: 1 },
    },
    outputs: ['value', 'signal', 'histogram'],
    defaultOutput: 'value',
  },
  roc: {
    nameKo: '변화율',
    nameEn: 'Rate of Change',
    category: 'momentum',
    description: '일정 기간 전 대비 가격 변화 비율(%). 모멘텀 강도 측정.',
    params: {
      period: { label: '기간', default: 12, min: 1, max: 100, step: 1 },
    },
    outputs: ['value'],
    defaultOutput: 'value',
  },
  returns: {
    nameKo: '수익률',
    nameEn: 'Returns',
    category: 'momentum',
    description: '일정 기간의 가격 수익률. 기본 1일 수익률.',
    params: {
      period: { label: '기간', default: 1, min: 1, max: 100, step: 1 },
    },
    outputs: ['value'],
    defaultOutput: 'value',
  },
  momentum: {
    nameKo: '모멘텀',
    nameEn: 'Momentum',
    category: 'momentum',
    description: '현재 가격과 N일 전 가격의 차이. 추세 가속/감속 판단.',
    params: {
      period: { label: '기간', default: 10, min: 1, max: 100, step: 1 },
    },
    outputs: ['value'],
    defaultOutput: 'value',
  },

  // ═══════════════════════════════════════════════════════════
  // 오실레이터 (oscillator) — 5개
  // ═══════════════════════════════════════════════════════════
  stochastic: {
    nameKo: '스토캐스틱',
    nameEn: 'Stochastic Oscillator',
    category: 'oscillator',
    description: '최근 가격이 일정 기간 고저 범위 내 어디에 위치하는지 측정.',
    params: {
      k_period: { label: '%K 기간', default: 14, min: 2, max: 100, step: 1 },
      d_period: { label: '%D 기간', default: 3, min: 1, max: 50, step: 1 },
      smooth_k: { label: '%K 평활', default: 3, min: 1, max: 20, step: 1 },
    },
    outputs: ['k', 'd'],
    defaultOutput: 'k',
  },
  cci: {
    nameKo: 'CCI',
    nameEn: 'Commodity Channel Index',
    category: 'oscillator',
    description: '평균 가격 대비 현재 가격의 편차. +100/-100 과매수/과매도 기준.',
    params: {
      period: { label: '기간', default: 20, min: 2, max: 100, step: 1 },
    },
    outputs: ['value'],
    defaultOutput: 'value',
  },
  williams_r: {
    nameKo: 'Williams %R',
    nameEn: 'Williams %R',
    category: 'oscillator',
    description: '최고가 대비 현재 가격의 위치. -20 이상 과매수, -80 이하 과매도.',
    params: {
      period: { label: '기간', default: 14, min: 2, max: 100, step: 1 },
    },
    outputs: ['value'],
    defaultOutput: 'value',
  },
  mfi: {
    nameKo: 'MFI',
    nameEn: 'Money Flow Index',
    category: 'oscillator',
    description: '거래량 가중 RSI. 자금 유입/유출 강도 측정. 80/20 과매수/과매도.',
    params: {
      period: { label: '기간', default: 14, min: 2, max: 100, step: 1 },
    },
    outputs: ['value'],
    defaultOutput: 'value',
  },
  ibs: {
    nameKo: 'IBS',
    nameEn: 'Internal Bar Strength',
    category: 'oscillator',
    description: '당일 캔들 내 종가의 상대 위치. 0에 가까우면 저가 근처, 1이면 고가 근처.',
    params: {},
    outputs: ['value'],
    defaultOutput: 'value',
  },

  // ═══════════════════════════════════════════════════════════
  // 변동성 (volatility) — 4개
  // ═══════════════════════════════════════════════════════════
  bollinger: {
    nameKo: '볼린저 밴드',
    nameEn: 'Bollinger Bands',
    category: 'volatility',
    description: '이동평균 ± 표준편차 밴드. 밴드 수축/확장으로 변동성 구간 판단.',
    params: {
      period:  { label: '기간', default: 20, min: 2, max: 200, step: 1 },
      std_dev: { label: '표준편차 배수', default: 2, min: 0.5, max: 4, step: 0.1 },
    },
    outputs: ['upper', 'middle', 'lower'],
    defaultOutput: 'middle',
  },
  atr: {
    nameKo: 'ATR',
    nameEn: 'Average True Range',
    category: 'volatility',
    description: '일정 기간 평균 진폭(True Range). 변동성 크기의 절대 지표.',
    params: {
      period: { label: '기간', default: 14, min: 2, max: 100, step: 1 },
    },
    outputs: ['value'],
    defaultOutput: 'value',
  },
  stddev: {
    nameKo: '표준편차',
    nameEn: 'Standard Deviation',
    category: 'volatility',
    description: '가격의 통계적 분산 정도. 변동성의 수학적 측정.',
    params: {
      period: { label: '기간', default: 20, min: 2, max: 200, step: 1 },
    },
    outputs: ['value'],
    defaultOutput: 'value',
  },
  zscore: {
    nameKo: 'Z-Score',
    nameEn: 'Z-Score',
    category: 'volatility',
    description: '평균 대비 현재 가격의 표준편차 수. 평균회귀 전략의 핵심 지표.',
    params: {
      period: { label: '기간', default: 20, min: 2, max: 200, step: 1 },
    },
    outputs: ['value'],
    defaultOutput: 'value',
  },

  // ═══════════════════════════════════════════════════════════
  // 추세 (trend) — 2개
  // ═══════════════════════════════════════════════════════════
  adx: {
    nameKo: 'ADX',
    nameEn: 'Average Directional Index',
    category: 'trend',
    description: '추세 강도 측정(0~100). 25 이상이면 추세 존재, 방향은 DI로 판단.',
    params: {
      period: { label: '기간', default: 14, min: 2, max: 100, step: 1 },
    },
    outputs: ['adx', 'plus_di', 'minus_di'],
    defaultOutput: 'adx',
  },
  disparity: {
    nameKo: '이격도',
    nameEn: 'Disparity Index',
    category: 'trend',
    description: '현재 가격과 이동평균의 괴리 정도(%). 100 기준 상하 이탈 판단.',
    params: {
      period: { label: '기간', default: 20, min: 2, max: 200, step: 1 },
    },
    outputs: ['value'],
    defaultOutput: 'value',
  },

  // ═══════════════════════════════════════════════════════════
  // 거래량 (volume) — 1개
  // ═══════════════════════════════════════════════════════════
  obv: {
    nameKo: 'OBV',
    nameEn: 'On-Balance Volume',
    category: 'volume',
    description: '가격 방향에 따라 거래량을 누적. 가격에 선행하는 거래량 추세 파악.',
    params: {},
    outputs: ['value'],
    defaultOutput: 'value',
  },

  // ═══════════════════════════════════════════════════════════
  // 기타 — 1개
  // ═══════════════════════════════════════════════════════════
  consecutive_candles: {
    nameKo: '연속캔들',
    nameEn: 'Consecutive Candles',
    category: 'momentum',
    description: 'N일 연속 양봉/음봉 감지. 단기 추세 반전 신호로 활용.',
    params: {
      count: { label: '연속 수', default: 3, min: 2, max: 10, step: 1 },
    },
    outputs: ['value'],
    defaultOutput: 'value',
  },

  // ═══════════════════════════════════════════════════════════
  // 캔들패턴 (candle_pattern) — 66종
  // 모두 params: {}, outputs: ['signal'], defaultOutput: 'signal'
  // ═══════════════════════════════════════════════════════════

  // ── 단일 캔들 (11종) ──
  doji:              { nameKo: '도지', nameEn: 'Doji', category: 'candle_pattern', description: '시가와 종가가 거의 같은 십자형 캔들. 추세 전환 가능성.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  long_legged_doji:  { nameKo: '장대 도지', nameEn: 'Long-Legged Doji', category: 'candle_pattern', description: '위아래 꼬리가 긴 도지. 극심한 매수·매도 공방.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  dragonfly_doji:    { nameKo: '잠자리 도지', nameEn: 'Dragonfly Doji', category: 'candle_pattern', description: '긴 아래꼬리의 도지. 하락 후 반등 신호.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  gravestone_doji:   { nameKo: '비석 도지', nameEn: 'Gravestone Doji', category: 'candle_pattern', description: '긴 윗꼬리의 도지. 상승 후 하락 신호.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  hammer:            { nameKo: '해머', nameEn: 'Hammer', category: 'candle_pattern', description: '하락 추세 후 긴 아래꼬리 양봉. 바닥 반전 신호.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  inverted_hammer:   { nameKo: '역해머', nameEn: 'Inverted Hammer', category: 'candle_pattern', description: '하락 추세 후 긴 윗꼬리. 반전 가능성 시사.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  hanging_man:       { nameKo: '교수형', nameEn: 'Hanging Man', category: 'candle_pattern', description: '상승 추세 후 해머 형태. 천장 반전 경고.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  shooting_star:     { nameKo: '유성형', nameEn: 'Shooting Star', category: 'candle_pattern', description: '상승 추세 후 긴 윗꼬리. 하락 반전 신호.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  marubozu_white:    { nameKo: '백색 마루보즈', nameEn: 'White Marubozu', category: 'candle_pattern', description: '꼬리 없는 장대양봉. 강한 매수세.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  marubozu_black:    { nameKo: '흑색 마루보즈', nameEn: 'Black Marubozu', category: 'candle_pattern', description: '꼬리 없는 장대음봉. 강한 매도세.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  spinning_top:      { nameKo: '팽이', nameEn: 'Spinning Top', category: 'candle_pattern', description: '짧은 몸통에 양쪽 꼬리. 매수·매도 균형, 방향 불확실.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },

  // ── 2봉 패턴 (18종) ──
  engulfing_bullish:       { nameKo: '상승 장악형', nameEn: 'Bullish Engulfing', category: 'candle_pattern', description: '음봉을 완전히 감싸는 양봉. 강한 상승 반전.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  engulfing_bearish:       { nameKo: '하락 장악형', nameEn: 'Bearish Engulfing', category: 'candle_pattern', description: '양봉을 완전히 감싸는 음봉. 강한 하락 반전.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  harami_bullish:          { nameKo: '상승 잉태형', nameEn: 'Bullish Harami', category: 'candle_pattern', description: '큰 음봉 안에 작은 양봉. 하락 둔화 신호.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  harami_bearish:          { nameKo: '하락 잉태형', nameEn: 'Bearish Harami', category: 'candle_pattern', description: '큰 양봉 안에 작은 음봉. 상승 둔화 신호.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  harami_cross_bullish:    { nameKo: '상승 십자 잉태형', nameEn: 'Bullish Harami Cross', category: 'candle_pattern', description: '큰 음봉 안에 도지. 강한 반전 가능성.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  harami_cross_bearish:    { nameKo: '하락 십자 잉태형', nameEn: 'Bearish Harami Cross', category: 'candle_pattern', description: '큰 양봉 안에 도지. 천장 가능성.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  piercing_line:           { nameKo: '관통형', nameEn: 'Piercing Line', category: 'candle_pattern', description: '하락 후 양봉이 전일 음봉 중간 이상 관통. 반등 신호.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  dark_cloud_cover:        { nameKo: '먹구름형', nameEn: 'Dark Cloud Cover', category: 'candle_pattern', description: '상승 후 음봉이 전일 양봉 중간 이하 침투. 하락 신호.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  belt_hold_bullish:       { nameKo: '상승 띠잡이형', nameEn: 'Bullish Belt Hold', category: 'candle_pattern', description: '갭다운 후 시가=저가인 장대양봉. 반등 기대.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  belt_hold_bearish:       { nameKo: '하락 띠잡이형', nameEn: 'Bearish Belt Hold', category: 'candle_pattern', description: '갭업 후 시가=고가인 장대음봉. 하락 전환.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  kicking_bullish:         { nameKo: '상승 되차기형', nameEn: 'Bullish Kicking', category: 'candle_pattern', description: '흑색 마루보즈 후 갭업 백색 마루보즈. 극강 상승 신호.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  kicking_bearish:         { nameKo: '하락 되차기형', nameEn: 'Bearish Kicking', category: 'candle_pattern', description: '백색 마루보즈 후 갭다운 흑색 마루보즈. 극강 하락 신호.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  counterattack_bullish:   { nameKo: '상승 반격형', nameEn: 'Bullish Counterattack', category: 'candle_pattern', description: '하락 중 양봉이 전일 종가까지 반등. 반전 시도.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  counterattack_bearish:   { nameKo: '하락 반격형', nameEn: 'Bearish Counterattack', category: 'candle_pattern', description: '상승 중 음봉이 전일 종가까지 하락. 반전 시도.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  matching_low:            { nameKo: '일치 저가', nameEn: 'Matching Low', category: 'candle_pattern', description: '연속 2일 동일 종가(저점). 지지선 형성 신호.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  matching_high:           { nameKo: '일치 고가', nameEn: 'Matching High', category: 'candle_pattern', description: '연속 2일 동일 종가(고점). 저항선 형성 신호.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  tweezer_top:             { nameKo: '족집게 천장형', nameEn: 'Tweezer Top', category: 'candle_pattern', description: '연속 2봉 고가 동일. 천장 반전 경고.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  tweezer_bottom:          { nameKo: '족집게 바닥형', nameEn: 'Tweezer Bottom', category: 'candle_pattern', description: '연속 2봉 저가 동일. 바닥 반전 신호.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },

  // ── 3봉 패턴 (24종) ──
  morning_star:       { nameKo: '샛별형', nameEn: 'Morning Star', category: 'candle_pattern', description: '장대음봉-소형봉-장대양봉. 대표적 바닥 반전 패턴.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  evening_star:       { nameKo: '석별형', nameEn: 'Evening Star', category: 'candle_pattern', description: '장대양봉-소형봉-장대음봉. 대표적 천장 반전 패턴.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  morning_doji_star:  { nameKo: '샛별 도지형', nameEn: 'Morning Doji Star', category: 'candle_pattern', description: '장대음봉-도지-장대양봉. 샛별형보다 강한 반전 신호.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  evening_doji_star:  { nameKo: '석별 도지형', nameEn: 'Evening Doji Star', category: 'candle_pattern', description: '장대양봉-도지-장대음봉. 석별형보다 강한 반전 신호.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  three_white_soldiers: { nameKo: '적삼병', nameEn: 'Three White Soldiers', category: 'candle_pattern', description: '연속 3일 장대양봉. 강한 상승 추세 시작.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  three_black_crows:    { nameKo: '흑삼병', nameEn: 'Three Black Crows', category: 'candle_pattern', description: '연속 3일 장대음봉. 강한 하락 추세 시작.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  abandoned_baby_bullish: { nameKo: '상승 버림받은 아기형', nameEn: 'Bullish Abandoned Baby', category: 'candle_pattern', description: '음봉-갭다운 도지-갭업 양봉. 희귀하지만 강력한 바닥 신호.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  abandoned_baby_bearish: { nameKo: '하락 버림받은 아기형', nameEn: 'Bearish Abandoned Baby', category: 'candle_pattern', description: '양봉-갭업 도지-갭다운 음봉. 희귀하지만 강력한 천장 신호.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  three_inside_up:    { nameKo: '상승 삼내형', nameEn: 'Three Inside Up', category: 'candle_pattern', description: '잉태형+확인봉(양봉). 바닥 반전 확인.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  three_inside_down:  { nameKo: '하락 삼내형', nameEn: 'Three Inside Down', category: 'candle_pattern', description: '잉태형+확인봉(음봉). 천장 반전 확인.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  three_outside_up:   { nameKo: '상승 삼외형', nameEn: 'Three Outside Up', category: 'candle_pattern', description: '장악형+확인봉(양봉). 강한 반전 확인.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  three_outside_down: { nameKo: '하락 삼외형', nameEn: 'Three Outside Down', category: 'candle_pattern', description: '장악형+확인봉(음봉). 강한 반전 확인.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  on_neck:            { nameKo: '목선형', nameEn: 'On Neck', category: 'candle_pattern', description: '음봉 후 양봉이 전일 저가까지만 회복. 하락 지속.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  in_neck:            { nameKo: '목안형', nameEn: 'In Neck', category: 'candle_pattern', description: '음봉 후 양봉이 전일 종가 근처까지 회복. 약한 하락 지속.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  thrusting:          { nameKo: '밀어넣기형', nameEn: 'Thrusting', category: 'candle_pattern', description: '음봉 후 양봉이 전일 몸통 중간까지 관통. 하락 지속 가능.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  advance_block:      { nameKo: '전진저지형', nameEn: 'Advance Block', category: 'candle_pattern', description: '연속 양봉이나 점차 약화. 상승 피로 경고.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  deliberation:       { nameKo: '숙고형', nameEn: 'Deliberation', category: 'candle_pattern', description: '2장대양봉 후 소형양봉/팽이. 상승 둔화 경고.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  two_crows:          { nameKo: '까마귀 2마리', nameEn: 'Two Crows', category: 'candle_pattern', description: '장대양봉 후 갭업 음봉+관통 음봉. 하락 반전 경고.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  upside_gap_two_crows: { nameKo: '상승갭 까마귀 2마리', nameEn: 'Upside Gap Two Crows', category: 'candle_pattern', description: '상승갭 후 연속 2음봉. 갭 미달 시 하락 신호.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  three_line_strike_bullish: { nameKo: '상승 삼선타격형', nameEn: 'Bullish Three Line Strike', category: 'candle_pattern', description: '3음봉 후 전체를 감싸는 장대양봉. 반전.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  three_line_strike_bearish: { nameKo: '하락 삼선타격형', nameEn: 'Bearish Three Line Strike', category: 'candle_pattern', description: '3양봉 후 전체를 감싸는 장대음봉. 반전.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  concealing_baby_swallow:   { nameKo: '은폐 삼키기형', nameEn: 'Concealing Baby Swallow', category: 'candle_pattern', description: '2흑색 마루보즈+잉태 고가형+장대음봉. 희귀 바닥 패턴.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  stick_sandwich:     { nameKo: '스틱 샌드위치', nameEn: 'Stick Sandwich', category: 'candle_pattern', description: '음봉-양봉-음봉, 첫째·셋째 종가 동일. 지지선 확인.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  unique_three_river_bottom: { nameKo: '독특한 삼천저', nameEn: 'Unique Three River Bottom', category: 'candle_pattern', description: '장대음봉+해머형+소형양봉. 희귀 바닥 반전.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  homing_pigeon:      { nameKo: '귀소 비둘기', nameEn: 'Homing Pigeon', category: 'candle_pattern', description: '음봉 안에 작은 음봉. 잉태형의 음봉 변형. 하락 둔화.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  identical_three_crows: { nameKo: '동일 흑삼병', nameEn: 'Identical Three Crows', category: 'candle_pattern', description: '연속 3음봉, 각 시가=전일 종가. 흑삼병보다 강한 하락.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },

  // ── 5봉+ 패턴 (9종) ──
  rising_three_methods:  { nameKo: '상승 삼법형', nameEn: 'Rising Three Methods', category: 'candle_pattern', description: '장대양봉+3소형음봉+장대양봉. 상승 추세 지속 확인.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  falling_three_methods: { nameKo: '하락 삼법형', nameEn: 'Falling Three Methods', category: 'candle_pattern', description: '장대음봉+3소형양봉+장대음봉. 하락 추세 지속 확인.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  ladder_bottom:       { nameKo: '사다리 바닥형', nameEn: 'Ladder Bottom', category: 'candle_pattern', description: '연속 하락 후 반전 양봉. 바닥 탈출 신호.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  ladder_top:          { nameKo: '사다리 천장형', nameEn: 'Ladder Top', category: 'candle_pattern', description: '연속 상승 후 반전 음봉. 천장 확인 신호.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  breakaway_bullish:   { nameKo: '상승 이탈형', nameEn: 'Bullish Breakaway', category: 'candle_pattern', description: '장대음봉+갭다운+3봉 정체+갭업 양봉. 하락 반전.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  breakaway_bearish:   { nameKo: '하락 이탈형', nameEn: 'Bearish Breakaway', category: 'candle_pattern', description: '장대양봉+갭업+3봉 정체+갭다운 음봉. 상승 반전.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  tasuki_gap_up:       { nameKo: '상승 타스키 갭', nameEn: 'Upside Tasuki Gap', category: 'candle_pattern', description: '양봉+갭업 양봉+음봉(갭 미봉합). 상승 지속.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  tasuki_gap_down:     { nameKo: '하락 타스키 갭', nameEn: 'Downside Tasuki Gap', category: 'candle_pattern', description: '음봉+갭다운 음봉+양봉(갭 미봉합). 하락 지속.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  side_by_side_white:  { nameKo: '나란히 백색선', nameEn: 'Side by Side White Lines', category: 'candle_pattern', description: '갭업 후 비슷한 크기 양봉 2개 나란히. 추세 지속.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },

  // ── 삼성(3봉) 도지 패턴 (2종) ──
  tri_star_bullish:  { nameKo: '상승 삼성형', nameEn: 'Bullish Tri-Star', category: 'candle_pattern', description: '연속 3도지(가운데 갭). 극히 희귀한 바닥 반전.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
  tri_star_bearish:  { nameKo: '하락 삼성형', nameEn: 'Bearish Tri-Star', category: 'candle_pattern', description: '연속 3도지(가운데 갭). 극히 희귀한 천장 반전.', params: {}, outputs: ['signal'], defaultOutput: 'signal' },
}


// ────────────────────────────────────────────────────────────
// 2. INDICATOR_CATEGORIES — 카테고리별 메타
// ────────────────────────────────────────────────────────────

export const INDICATOR_CATEGORIES = {
  moving_average: { label: '이동평균', color: 'blue' },
  momentum:       { label: '모멘텀', color: 'orange' },
  oscillator:     { label: '오실레이터', color: 'purple' },
  volatility:     { label: '변동성', color: 'emerald' },
  trend:          { label: '추세', color: 'cyan' },
  volume:         { label: '거래량', color: 'amber' },
  candle_pattern: { label: '캔들패턴', color: 'pink' },
}


// ────────────────────────────────────────────────────────────
// 3. CONDITION_OPERATORS — 조건 연산자
// ────────────────────────────────────────────────────────────

export const CONDITION_OPERATORS = [
  { value: 'greater_than',  label: '> 보다 큰',    desc: '왼쪽 값이 오른쪽보다 클 때' },
  { value: 'less_than',     label: '< 보다 작은',  desc: '왼쪽 값이 오른쪽보다 작을 때' },
  { value: 'cross_above',   label: '↗ 상향 돌파',  desc: '아래에서 위로 교차할 때 (골든크로스)' },
  { value: 'cross_below',   label: '↘ 하향 돌파',  desc: '위에서 아래로 교차할 때 (데드크로스)' },
  { value: 'equals',        label: '= 같다',       desc: '두 값이 동일할 때' },
  { value: 'not_equal',     label: '≠ 다르다',     desc: '두 값이 다를 때' },
  { value: 'breaks',        label: '⬆ 돌파',      desc: '지지선/저항선 돌파' },
]


// ────────────────────────────────────────────────────────────
// 4. PRICE_FIELDS — 가격 필드
// ────────────────────────────────────────────────────────────

export const PRICE_FIELDS = [
  { value: 'open',   label: '시가' },
  { value: 'high',   label: '고가' },
  { value: 'low',    label: '저가' },
  { value: 'close',  label: '종가' },
  { value: 'volume', label: '거래량' },
]


// ────────────────────────────────────────────────────────────
// 5. BUILDER_PRESETS — 빌더 프리셋 6개
// ────────────────────────────────────────────────────────────

export const BUILDER_PRESETS = [
  // ── 1) 골든크로스 ──
  {
    id: 'golden_cross',
    name: '골든크로스',
    description: '단기 이동평균이 장기 이동평균을 상향 돌파할 때 매수, 하향 돌파할 때 매도',
    category: 'trend',
    state: {
      metadata: {
        name: '골든크로스',
        description: '단기 이동평균이 장기 이동평균을 상향 돌파할 때 매수',
        category: 'trend',
        tags: ['이동평균', '추세'],
      },
      indicators: [
        { id: 'sma', alias: 'sma_short', params: { period: 5 }, selectedOutputs: ['value'] },
        { id: 'sma', alias: 'sma_long', params: { period: 20 }, selectedOutputs: ['value'] },
      ],
      entryGroups: [{
        operator: 'AND',
        conditions: [{
          left: { type: 'indicator', alias: 'sma_short', output: 'value' },
          operator: 'cross_above',
          right: { type: 'indicator', alias: 'sma_long', output: 'value' },
        }],
      }],
      exitGroups: [{
        operator: 'AND',
        conditions: [{
          left: { type: 'indicator', alias: 'sma_short', output: 'value' },
          operator: 'cross_below',
          right: { type: 'indicator', alias: 'sma_long', output: 'value' },
        }],
      }],
      risk: {
        stopLoss: { enabled: true, percent: 5 },
        takeProfit: { enabled: true, percent: 10 },
        trailingStop: { enabled: false, percent: 3 },
      },
    },
  },

  // ── 2) RSI 과매도 반등 ──
  {
    id: 'rsi_oversold',
    name: 'RSI 과매도 반등',
    description: 'RSI가 30 이하로 하락 후 30을 상향 돌파할 때 매수, 70 이상에서 매도',
    category: 'momentum',
    state: {
      metadata: {
        name: 'RSI 과매도 반등',
        description: 'RSI 과매도 구간 진입 후 반등 시 매수',
        category: 'momentum',
        tags: ['RSI', '과매도', '역추세'],
      },
      indicators: [
        { id: 'rsi', alias: 'rsi_14', params: { period: 14 }, selectedOutputs: ['value'] },
      ],
      entryGroups: [{
        operator: 'AND',
        conditions: [{
          left: { type: 'indicator', alias: 'rsi_14', output: 'value' },
          operator: 'cross_above',
          right: { type: 'number', value: 30 },
        }],
      }],
      exitGroups: [{
        operator: 'AND',
        conditions: [{
          left: { type: 'indicator', alias: 'rsi_14', output: 'value' },
          operator: 'greater_than',
          right: { type: 'number', value: 70 },
        }],
      }],
      risk: {
        stopLoss: { enabled: true, percent: 3 },
        takeProfit: { enabled: true, percent: 8 },
        trailingStop: { enabled: false, percent: 3 },
      },
    },
  },

  // ── 3) MACD 골든크로스 ──
  {
    id: 'macd_golden_cross',
    name: 'MACD 골든크로스',
    description: 'MACD 라인이 시그널 라인을 상향 돌파할 때 매수, 하향 돌파할 때 매도',
    category: 'momentum',
    state: {
      metadata: {
        name: 'MACD 골든크로스',
        description: 'MACD 라인과 시그널 라인의 교차로 추세 전환 포착',
        category: 'momentum',
        tags: ['MACD', '시그널', '추세전환'],
      },
      indicators: [
        { id: 'macd', alias: 'macd_default', params: { fast: 12, slow: 26, signal: 9 }, selectedOutputs: ['value', 'signal', 'histogram'] },
      ],
      entryGroups: [{
        operator: 'AND',
        conditions: [{
          left: { type: 'indicator', alias: 'macd_default', output: 'value' },
          operator: 'cross_above',
          right: { type: 'indicator', alias: 'macd_default', output: 'signal' },
        }],
      }],
      exitGroups: [{
        operator: 'AND',
        conditions: [{
          left: { type: 'indicator', alias: 'macd_default', output: 'value' },
          operator: 'cross_below',
          right: { type: 'indicator', alias: 'macd_default', output: 'signal' },
        }],
      }],
      risk: {
        stopLoss: { enabled: true, percent: 4 },
        takeProfit: { enabled: true, percent: 12 },
        trailingStop: { enabled: false, percent: 3 },
      },
    },
  },

  // ── 4) 볼린저밴드 수축 ──
  {
    id: 'bollinger_squeeze',
    name: '볼린저밴드 수축',
    description: '볼린저밴드 수축 후 종가가 상단 밴드를 돌파할 때 매수, 하단 밴드 이탈 시 매도',
    category: 'volatility',
    state: {
      metadata: {
        name: '볼린저밴드 수축',
        description: '변동성 수축 구간에서 상단 돌파 시 진입',
        category: 'volatility',
        tags: ['볼린저', '변동성', '돌파'],
      },
      indicators: [
        { id: 'bollinger', alias: 'bb_20', params: { period: 20, std_dev: 2 }, selectedOutputs: ['upper', 'middle', 'lower'] },
      ],
      entryGroups: [{
        operator: 'AND',
        conditions: [{
          left: { type: 'price', field: 'close' },
          operator: 'cross_above',
          right: { type: 'indicator', alias: 'bb_20', output: 'upper' },
        }],
      }],
      exitGroups: [{
        operator: 'AND',
        conditions: [{
          left: { type: 'price', field: 'close' },
          operator: 'cross_below',
          right: { type: 'indicator', alias: 'bb_20', output: 'lower' },
        }],
      }],
      risk: {
        stopLoss: { enabled: true, percent: 3 },
        takeProfit: { enabled: true, percent: 10 },
        trailingStop: { enabled: true, percent: 5 },
      },
    },
  },

  // ── 5) 추세필터 (ADX + EMA) ──
  {
    id: 'trend_filter',
    name: '추세필터',
    description: 'ADX가 25 이상이고 EMA 단기가 장기를 상향 돌파할 때 매수. 강한 추세에서만 진입.',
    category: 'trend',
    state: {
      metadata: {
        name: '추세필터',
        description: 'ADX로 추세 강도를 확인한 후 EMA 교차로 진입',
        category: 'trend',
        tags: ['ADX', 'EMA', '추세강도', '필터'],
      },
      indicators: [
        { id: 'adx', alias: 'adx_14', params: { period: 14 }, selectedOutputs: ['adx', 'plus_di', 'minus_di'] },
        { id: 'ema', alias: 'ema_short', params: { period: 10 }, selectedOutputs: ['value'] },
        { id: 'ema', alias: 'ema_long', params: { period: 30 }, selectedOutputs: ['value'] },
      ],
      entryGroups: [{
        operator: 'AND',
        conditions: [
          {
            left: { type: 'indicator', alias: 'adx_14', output: 'adx' },
            operator: 'greater_than',
            right: { type: 'number', value: 25 },
          },
          {
            left: { type: 'indicator', alias: 'ema_short', output: 'value' },
            operator: 'cross_above',
            right: { type: 'indicator', alias: 'ema_long', output: 'value' },
          },
        ],
      }],
      exitGroups: [{
        operator: 'OR',
        conditions: [
          {
            left: { type: 'indicator', alias: 'adx_14', output: 'adx' },
            operator: 'less_than',
            right: { type: 'number', value: 20 },
          },
          {
            left: { type: 'indicator', alias: 'ema_short', output: 'value' },
            operator: 'cross_below',
            right: { type: 'indicator', alias: 'ema_long', output: 'value' },
          },
        ],
      }],
      risk: {
        stopLoss: { enabled: true, percent: 5 },
        takeProfit: { enabled: true, percent: 15 },
        trailingStop: { enabled: true, percent: 4 },
      },
    },
  },

  // ── 6) 변동성 돌파 ──
  {
    id: 'volatility_breakout',
    name: '변동성 돌파',
    description: '전일 ATR을 기반으로 당일 시가 + ATR*K 돌파 시 매수. 래리 윌리엄스 전략 변형.',
    category: 'volatility',
    state: {
      metadata: {
        name: '변동성 돌파',
        description: '전일 변동폭(ATR) 기준 일정 비율 돌파 시 진입',
        category: 'volatility',
        tags: ['ATR', '변동성', '돌파', '래리윌리엄스'],
      },
      indicators: [
        { id: 'atr', alias: 'atr_14', params: { period: 14 }, selectedOutputs: ['value'] },
        { id: 'sma', alias: 'sma_trend', params: { period: 20 }, selectedOutputs: ['value'] },
      ],
      entryGroups: [{
        operator: 'AND',
        conditions: [
          {
            left: { type: 'price', field: 'close' },
            operator: 'greater_than',
            right: { type: 'indicator', alias: 'sma_trend', output: 'value' },
          },
          {
            left: { type: 'indicator', alias: 'atr_14', output: 'value' },
            operator: 'greater_than',
            right: { type: 'number', value: 0 },
          },
        ],
      }],
      exitGroups: [{
        operator: 'OR',
        conditions: [
          {
            left: { type: 'price', field: 'close' },
            operator: 'cross_below',
            right: { type: 'indicator', alias: 'sma_trend', output: 'value' },
          },
        ],
      }],
      risk: {
        stopLoss: { enabled: true, percent: 2 },
        takeProfit: { enabled: true, percent: 5 },
        trailingStop: { enabled: true, percent: 3 },
      },
    },
  },
]
