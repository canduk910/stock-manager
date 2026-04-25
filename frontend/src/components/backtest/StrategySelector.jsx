/**
 * 전략 선택기 — 프리셋 드롭다운(상세 설명 카드) / 커스텀 YAML 텍스트 에디터.
 */
import { useMemo } from 'react'

/** 파라미터 한글 매핑: { label: 한글명, desc: 비유적 설명 } */
export const PARAM_KR = {
  // ── 이동평균 ──
  short_period:   { label: '단기 이평선',       desc: '빠른 흐름을 잡는 짧은 안테나 (일)' },
  long_period:    { label: '장기 이평선',       desc: '큰 추세를 보는 긴 안테나 (일)' },
  fast_period:    { label: '빠른 이평선',       desc: '민감하게 반응하는 단기 평균 (일)' },
  slow_period:    { label: '느린 이평선',       desc: '느긋하게 따라가는 장기 평균 (일)' },
  signal_period:  { label: '시그널 기간',       desc: 'MACD의 매매 타이밍 판단선 (일)' },
  sma_period:     { label: 'SMA 기간',         desc: '단순이동평균 계산 기간 (일)' },
  ema_period:     { label: 'EMA 기간',         desc: '최근 가격에 가중치를 둔 평균 (일)' },
  ma_period:      { label: '이동평균 기간',     desc: '평균 가격 계산에 사용할 기간 (일)' },
  period:         { label: '기간',              desc: '지표 계산에 사용할 기간 (일)' },
  window:         { label: '계산 기간',         desc: '지표를 계산할 윈도우 크기 (일)' },
  lookback:       { label: '되돌아보기',        desc: '과거 몇 일을 참고할지 (일)' },
  lookback_period:{ label: '참조 기간',         desc: '과거 데이터 참조 범위 (일)' },
  // ── RSI ──
  rsi_period:     { label: 'RSI 기간',          desc: '과열/침체 체온계의 측정 주기 (일)' },
  rsi_upper:      { label: 'RSI 과매수',        desc: '이 온도 이상이면 "과열" 매도 신호' },
  rsi_lower:      { label: 'RSI 과매도',        desc: '이 온도 이하이면 "침체" 매수 신호' },
  rsi_overbought: { label: 'RSI 과매수',        desc: '이 값 이상이면 과열 → 매도 고려' },
  rsi_oversold:   { label: 'RSI 과매도',        desc: '이 값 이하이면 침체 → 매수 고려' },
  // ── 볼린저 밴드 ──
  bb_period:      { label: 'BB 기간',           desc: '볼린저 밴드의 중심선 평균 기간 (일)' },
  bb_std:         { label: 'BB 표준편차',       desc: '밴드 폭 — 클수록 범위가 넓어짐 (배)' },
  bb_mult:        { label: 'BB 승수',           desc: '밴드 폭을 조절하는 배수 (배)' },
  num_std:        { label: '표준편차 배수',     desc: '밴드의 너비를 결정하는 배수 (배)' },
  // ── 변동성 / ATR ──
  k_value:        { label: 'K 계수',            desc: '어제 변동폭의 몇 배를 돌파 기준으로 삼을지' },
  k_factor:       { label: 'K 계수',            desc: '변동성 돌파의 민감도 조절 계수' },
  atr_period:     { label: 'ATR 기간',          desc: '평균 변동폭(진폭) 측정 기간 (일)' },
  atr_mult:       { label: 'ATR 승수',          desc: '변동폭 몇 배를 기준으로 삼을지 (배)' },
  volatility_period: { label: '변동성 기간',    desc: '가격 변동 크기를 측정할 기간 (일)' },
  // ── 모멘텀 ──
  momentum_period:{ label: '모멘텀 기간',       desc: '며칠 전 대비 상승/하락을 볼지 (일)' },
  mom_period:     { label: '모멘텀 기간',       desc: '가격 탄력을 측정하는 기간 (일)' },
  ranking_period: { label: '순위 기간',         desc: '종목 간 수익률 비교 기간 (일)' },
  // ── 스토캐스틱 ──
  stoch_period:   { label: '스토캐스틱 기간',   desc: '최근 가격 위치를 파악하는 기간 (일)' },
  stoch_k:        { label: '%K 기간',           desc: '빠른 스토캐스틱 산출 기간 (일)' },
  stoch_d:        { label: '%D 기간',           desc: '%K의 이동평균 (매끄럽게)' },
  smooth_k:       { label: '%K 평활',           desc: '%K를 부드럽게 만드는 평균 기간' },
  smooth_d:       { label: '%D 평활',           desc: '%D를 부드럽게 만드는 평균 기간' },
  // ── 리스크 관리 ──
  stop_loss:      { label: '손절선',            desc: '최대 허용 손실 — 이 이상 떨어지면 매도 (%)' },
  stop_loss_pct:  { label: '손절선',            desc: '최대 허용 손실 — 이 이상 떨어지면 매도 (%)' },
  take_profit:    { label: '익절선',            desc: '목표 수익 달성 시 매도 (%)' },
  take_profit_pct:{ label: '익절선',            desc: '목표 수익 달성 시 매도 (%)' },
  trailing_stop:  { label: '추적 손절',         desc: '고점 대비 이만큼 하락하면 매도 (%)' },
  trailing_stop_pct: { label: '추적 손절',      desc: '고점 대비 이만큼 하락하면 매도 (%)' },
  max_holding:    { label: '최대 보유일',       desc: '포지션을 유지할 최대 기간 (일)' },
  max_holding_days: { label: '최대 보유일',     desc: '이 기간이 지나면 무조건 청산 (일)' },
  // ── 매매 비율 ──
  buy_ratio:      { label: '매수 비율',         desc: '보유 현금 중 매수에 사용할 비율 (0~1)' },
  sell_ratio:     { label: '매도 비율',         desc: '보유 수량 중 매도할 비율 (0~1)' },
  // ── 포지션 / 거래비용 ──
  position_size:  { label: '포지션 크기',       desc: '한 번에 투자할 금액 비중 (%)' },
  position_size_pct: { label: '투자 비중',      desc: '총 자산 대비 한 종목 투자 비율 (%)' },
  commission:     { label: '수수료율',          desc: '매매 시 발생하는 거래 수수료 (%)' },
  commission_pct: { label: '수수료율',          desc: '매매 시 발생하는 거래 수수료 (%)' },
  slippage:       { label: '슬리피지',          desc: '주문가와 실제 체결가의 차이 (%)' },
  slippage_pct:   { label: '슬리피지',          desc: '주문가와 실제 체결가의 차이 (%)' },
  max_drawdown_pct: { label: '최대 낙폭',      desc: '허용 가능한 최대 자산 하락폭 (%)' },
  // ── MACD 전용 ──
  macd_fast:      { label: 'MACD 빠른선',      desc: 'MACD 빠른 이동평균 기간 (일)' },
  macd_slow:      { label: 'MACD 느린선',      desc: 'MACD 느린 이동평균 기간 (일)' },
  macd_signal:    { label: 'MACD 시그널선',    desc: '매매 타이밍을 잡는 MACD 시그널 기간 (일)' },
  // ── ADX / 추세 필터 ──
  trend_period:   { label: '추세 기간',         desc: '추세 방향을 판단할 기간 (일)' },
  adx_period:     { label: 'ADX 기간',          desc: '추세 강도 측정 기간 (일)' },
  adx_threshold:  { label: 'ADX 임계값',        desc: '이 값 이상이면 "추세 있음"으로 판단' },
  // ── 평균회귀 ──
  z_score:        { label: 'Z스코어 기준',      desc: '평균에서 몇 표준편차 벗어나면 신호 발생' },
  zscore_threshold: { label: 'Z스코어 임계',    desc: '평균 복귀 진입/청산 기준점' },
  entry_z:        { label: '진입 Z스코어',      desc: '이만큼 벗어나면 역추세 매수' },
  exit_z:         { label: '청산 Z스코어',      desc: '평균 근처로 돌아오면 청산' },
  mean_period:    { label: '평균 기간',         desc: '되돌아갈 "평균"을 계산할 기간 (일)' },
  deviation:      { label: '편차',              desc: '평균에서의 허용 이탈 폭' },
  // ── 듀얼 모멘텀 ──
  abs_momentum_period: { label: '절대 모멘텀',  desc: '자기 자신의 과거 대비 수익률 기간 (일)' },
  rel_momentum_period: { label: '상대 모멘텀',  desc: '다른 자산 대비 상대 강도 기간 (일)' },
  // ── 워밍업 / 돌파 / 거래량 ──
  warmup:         { label: '워밍업 기간',       desc: '지표 안정화를 위해 건너뛸 초기 구간 (일)' },
  warmup_period:  { label: '워밍업 기간',       desc: '지표가 정확해지려면 필요한 준비 기간 (일)' },
  breakout_period:{ label: '돌파 기간',         desc: '며칠간의 고가/저가 돌파를 감지할지 (일)' },
  volume_factor:  { label: '거래량 배수',       desc: '평균 거래량의 몇 배를 신호 기준으로 삼을지' },
  volume_period:  { label: '거래량 기간',       desc: '평균 거래량 산출 기간 (일)' },
  // ── 보유 / 재진입 ──
  min_holding:    { label: '최소 보유일',       desc: '최소 이 기간은 보유해야 매도 가능 (일)' },
  min_holding_days: { label: '최소 보유일',     desc: '잦은 매매 방지를 위한 최소 보유 기간 (일)' },
  cooldown:       { label: '재진입 대기',       desc: '매도 후 다시 매수하기까지 쉬는 기간 (일)' },
  cooldown_period:{ label: '재진입 대기',       desc: '연속 매매 방지를 위한 휴지 기간 (일)' },
  // ── 연속일 / 청산 ──
  up_days:        { label: '연속 상승일',       desc: '며칠 연속 올라야 신호로 인정할지 (일)' },
  down_days:      { label: '연속 하락일',       desc: '며칠 연속 내려야 신호로 인정할지 (일)' },
  exit_days:      { label: '청산 대기일',       desc: '진입 후 며칠 뒤 자동 청산할지 (일)' },
  min_close_ratio:{ label: '최소 종가 비율',    desc: '종가가 당일 레인지 내 이 비율 이상이어야 유효 (0~1)' },
  breakout_pct:   { label: '돌파 기준',         desc: '기준가 대비 이 비율 이상 돌파 시 진입 (%)' },
  threshold_pct:  { label: '임계 비율',         desc: '신호 발생 기준 비율 (%)' },
  // ── 기타 ──
  n_period:       { label: 'N 기간',            desc: '범용 기간 파라미터 (일)' },
  threshold:      { label: '임계값',            desc: '신호 발생 기준점' },
  entry_threshold:{ label: '진입 임계값',       desc: '이 값을 넘으면 매수 신호' },
  exit_threshold: { label: '청산 임계값',       desc: '이 값을 넘으면 매도 신호' },
  profit_target:  { label: '수익 목표',         desc: '목표 수익에 도달하면 청산 (%)' },
  max_loss:       { label: '최대 손실',         desc: '허용 가능한 최대 손실폭 (%)' },
  rebalance_period: { label: '리밸런싱 주기',   desc: '포트폴리오 재조정 간격 (일)' },
  initial_capital:{ label: '초기 자본',         desc: '백테스트 시작 금액' },
  resolution:     { label: '데이터 해상도',     desc: '분석에 사용할 봉의 시간 단위' },
}

export const CATEGORY_LABELS = {
  trend: '추세추종',
  momentum: '모멘텀',
  mean_reversion: '역추세',
  volatility: '변동성',
  composite: '복합',
}

export const CATEGORY_COLORS = {
  trend: 'bg-blue-100 text-blue-700',
  momentum: 'bg-orange-100 text-orange-700',
  mean_reversion: 'bg-green-100 text-green-700',
  volatility: 'bg-purple-100 text-purple-700',
  composite: 'bg-indigo-100 text-indigo-700',
}

export default function StrategySelector({ presets, selectedPreset, customParams, onPresetChange, onParamsChange, mode, onModeChange, yamlContent, onYamlChange }) {
  const presetDetail = useMemo(() => {
    if (!selectedPreset || !presets?.length) return null
    return presets.find((p) => {
      const id = typeof p === 'string' ? p : p.id || p.strategy_id
      return id === selectedPreset
    })
  }, [selectedPreset, presets])

  return (
    <div className="space-y-3">
      {/* 모드 선택 탭 */}
      <div className="flex gap-2">
        <button
          onClick={() => onModeChange('preset')}
          className={`px-4 py-1.5 text-sm rounded font-medium transition-colors ${
            mode === 'preset'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          프리셋 전략
        </button>
        <button
          onClick={() => onModeChange('custom')}
          className={`px-4 py-1.5 text-sm rounded font-medium transition-colors ${
            mode === 'custom'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          커스텀 YAML
        </button>
      </div>

      {mode === 'preset' ? (
        <div>
          <select
            value={selectedPreset}
            onChange={(e) => onPresetChange(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">전략 선택...</option>
            {(presets || []).map((p) => {
              const id = typeof p === 'string' ? p : p.id || p.strategy_id
              const label = typeof p === 'object' ? p.name : id
              return (
                <option key={id} value={id}>
                  {label}
                </option>
              )
            })}
          </select>

          {/* 선택된 전략 상세 설명 카드 */}
          {presetDetail && typeof presetDetail === 'object' && (
            <div className="mt-3 bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm">
              <div className="flex items-center gap-2 mb-2">
                <span className="font-semibold text-gray-900">{presetDetail.name}</span>
                {presetDetail.category && (
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${CATEGORY_COLORS[presetDetail.category] || 'bg-gray-100 text-gray-600'}`}>
                    {CATEGORY_LABELS[presetDetail.category] || presetDetail.category}
                  </span>
                )}
              </div>

              {presetDetail.description && (
                <p className="text-gray-600 mb-3 leading-relaxed">{presetDetail.description}</p>
              )}

              {presetDetail.tags?.length > 0 && (
                <div className="flex gap-1 flex-wrap mb-3">
                  {presetDetail.tags.map((tag) => (
                    <span key={tag} className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded">
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              {(presetDetail.params || presetDetail.parameters) && Object.keys(presetDetail.params || presetDetail.parameters).length > 0 && (
                <div className="border-t border-gray-200 pt-3">
                  <p className="text-xs font-medium text-gray-500 mb-2">파라미터</p>
                  <div className="space-y-2">
                    {Object.entries(presetDetail.params || presetDetail.parameters).map(([key, spec]) => {
                      const kr = PARAM_KR[key]
                      return (
                        <div key={key} className="flex items-start gap-3 bg-white rounded border px-3 py-2">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="text-xs font-medium text-gray-800">{kr?.label || key}</span>
                              <span className="text-[10px] font-mono text-gray-400">{key}</span>
                            </div>
                            {kr?.desc && (
                              <p className="text-[11px] text-gray-400 mt-0.5 leading-snug">{kr.desc}</p>
                            )}
                          </div>
                          {spec?.min != null && spec?.max != null ? (
                            <div className="flex items-center gap-2 shrink-0 w-40">
                              <input
                                type="range"
                                value={customParams?.[key] ?? spec?.default ?? spec.min}
                                onChange={(e) => onParamsChange?.({ ...customParams, [key]: Number(e.target.value) })}
                                min={spec.min}
                                max={spec.max}
                                step={spec?.step ?? 1}
                                className="flex-1 h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
                              />
                              <span className="text-xs font-mono font-medium text-gray-700 w-10 text-right tabular-nums">
                                {customParams?.[key] ?? spec?.default ?? spec.min}
                              </span>
                            </div>
                          ) : (
                            <input
                              type="number"
                              value={customParams?.[key] ?? spec?.default ?? ''}
                              onChange={(e) => onParamsChange?.({ ...customParams, [key]: Number(e.target.value) })}
                              min={spec?.min}
                              max={spec?.max}
                              step={spec?.step}
                              className="w-20 text-right border rounded px-1.5 py-1 text-xs font-mono focus:ring-1 focus:ring-blue-500 shrink-0"
                            />
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-xs text-gray-500">KIS AI Extensions YAML 포맷으로 전략을 직접 작성하세요.</p>
          <textarea
            value={yamlContent}
            onChange={(e) => onYamlChange(e.target.value)}
            placeholder="KIS AI Extensions 전략 YAML을 붙여넣으세요"
            rows={12}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      )}
    </div>
  )
}
