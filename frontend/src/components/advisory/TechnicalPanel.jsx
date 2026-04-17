/**
 * 기술적 분석 탭
 * 캔들스틱 + MA + BB + 거래량 + MACD + RSI + Stochastic + PER/PBR 밸류에이션
 * 타임프레임 (15분/60분/1일/1주) + 기간 선택 지원
 */
import { useState, useEffect, useMemo } from 'react'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, LineChart,
} from 'recharts'
import { useAdvisoryOhlcv } from '../../hooks/useAdvisory'
import { fetchDetailValuation } from '../../api/detail'
import ValuationChart from '../detail/ValuationChart'
import CandlestickChart, {
  INTERVAL_OPTS,
  PERIOD_OPTIONS,
  makeTickFormatter,
  makeTooltipFormatter,
} from '../common/CandlestickChart'

const DEFAULT_PERIOD  = { '15m': '60d', '60m': '6mo', '1d': '1y', '1wk': '3y' }
const INTERVAL_LABEL  = { '15m': '15분봉', '60m': '60분봉', '1d': '일봉', '1wk': '주봉' }
const PERIOD_TO_YEARS = { '3mo': 1, '6mo': 1, '1y': 1, '3y': 3, '5y': 5, '10y': 10 }

// ── 시그널 배지 ────────────────────────────────────────────────────────────
function SignalBadge({ label, value, type }) {
  const color = {
    golden:     'bg-red-100 text-red-700 border-red-300',
    dead:       'bg-blue-100 text-blue-700 border-blue-300',
    overbought: 'bg-blue-100 text-blue-700 border-blue-300',
    oversold:   'bg-red-100 text-red-700 border-red-300',
    neutral:    'bg-gray-100 text-gray-600 border-gray-300',
    up:         'bg-red-100 text-red-700 border-red-300',
    down:       'bg-blue-100 text-blue-700 border-blue-300',
  }[type] || 'bg-gray-100 text-gray-600 border-gray-300'

  const arrow = { golden: '↑', dead: '↓', overbought: '↑', oversold: '↓', up: '↑', down: '↓' }[type] || ''

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs border font-medium ${color}`}>
      {label}: {value} {arrow}
    </span>
  )
}

// ── 메인 컴포넌트 ─────────────────────────────────────────────────────────
export default function TechnicalPanel({ data, symbol, market, valuationData }) {
  const [activeInterval, setActiveInterval] = useState('15m')
  const [activePeriod,   setActivePeriod]   = useState('60d')

  const { result: fetchedResult, loading: ohlcvLoading, load: loadOhlcv } = useAdvisoryOhlcv()

  // PER/PBR 밸류에이션 상태
  const [valData, setValData] = useState(valuationData || null)
  const [valLoading, setValLoading] = useState(false)

  // interval/period 변경 시 API 호출
  useEffect(() => {
    if (symbol && market) {
      loadOhlcv(symbol, market, activeInterval, activePeriod)
    }
  }, [symbol, market, activeInterval, activePeriod]) // eslint-disable-line

  // 1d/1wk 전환 시 밸류에이션 데이터 fetch
  useEffect(() => {
    const isEligible = activeInterval === '1d' || activeInterval === '1wk'
    if (!isEligible || !symbol) return

    const years = PERIOD_TO_YEARS[activePeriod] || 5

    // prop에서 받은 기본 데이터 사용 (최초 로드)
    if (valuationData && years >= 10) {
      setValData(valuationData)
      return
    }

    let cancelled = false
    setValLoading(true)
    fetchDetailValuation(symbol, years)
      .then(result => { if (!cancelled) setValData(result) })
      .catch(() => { if (!cancelled) setValData(null) })
      .finally(() => { if (!cancelled) setValLoading(false) })
    return () => { cancelled = true }
  }, [symbol, activeInterval, activePeriod]) // eslint-disable-line

  const handleIntervalChange = (newInterval) => {
    setActiveInterval(newInterval)
    setActivePeriod(DEFAULT_PERIOD[newInterval])
  }

  // 표시할 OHLCV / indicators (새 fetch 결과 우선, 없으면 캐시)
  const cachedTechnical  = data?.technical  || {}
  const cachedOhlcv      = cachedTechnical.ohlcv      || []
  const cachedIndicators = cachedTechnical.indicators  || {}

  const ohlcv      = fetchedResult?.ohlcv      ?? cachedOhlcv
  const indicators = fetchedResult?.indicators ?? cachedIndicators

  const signals = indicators.current_signals || {}
  const macd    = indicators.macd   || {}
  const rsi     = indicators.rsi    || {}
  const stoch   = indicators.stoch  || {}

  const times = macd.times || rsi.times || ohlcv.map(b => b.time)

  // MACD/RSI/Stochastic 데이터를 extraChartData로 병합
  const extraChartData = useMemo(() => {
    if (!macd.macd && !rsi.values && !stoch.k) return undefined
    return (_d, i) => ({
      macd:       (macd.macd      || [])[i],
      macdSignal: (macd.signal    || [])[i],
      macdHist:   (macd.histogram || [])[i],
      rsi:        (rsi.values     || [])[i],
      stochK:     (stoch.k        || [])[i],
      stochD:     (stoch.d        || [])[i],
    })
  }, [macd, rsi, stoch])

  // 하위 차트용 데이터 (times 기반)
  const subChartData = useMemo(() =>
    times.map((t, i) => ({
      time:       t,
      open:       ohlcv[i]?.open,
      close:      ohlcv[i]?.close,
      volume:     ohlcv[i]?.volume,
      macd:       (macd.macd      || [])[i],
      macdSignal: (macd.signal    || [])[i],
      macdHist:   (macd.histogram || [])[i],
      rsi:        (rsi.values     || [])[i],
      stochK:     (stoch.k        || [])[i],
      stochD:     (stoch.d        || [])[i],
    })),
  [times, ohlcv, macd, rsi, stoch])

  const tickFormatter = makeTickFormatter(activeInterval)
  const tooltipFormatter = makeTooltipFormatter(activeInterval)
  const xInterval     = Math.max(Math.floor(subChartData.length / 8), 1)

  if (!ohlcv.length && !ohlcvLoading) {
    return (
      <div className="text-center py-12 text-gray-400 text-sm">
        데이터가 없습니다.
        <br />
        <span className="text-xs">새로고침을 클릭하여 데이터를 수집해주세요.</span>
      </div>
    )
  }

  // 시그널 요약
  const macdCross   = signals.macd_cross   || 'none'
  const rsiSignal   = signals.rsi_signal   || 'neutral'
  const rsiVal      = signals.rsi_value
  const stochSignal = signals.stoch_signal || 'neutral'
  const stochK      = signals.stoch_k
  const aboveMa20   = signals.above_ma20
  const maAlignment = signals.ma_alignment || '혼합'
  const atrVal      = signals.atr
  const vtK03 = signals.volatility_target_k03 ?? indicators.volatility_target_k03
  const vtK05 = signals.volatility_target_k05 ?? indicators.volatility_target_k05
  const vtK07 = signals.volatility_target_k07 ?? indicators.volatility_target_k07

  const macdLabel  = { golden: '골든크로스', dead: '데드크로스', none: '크로스없음' }[macdCross] || '-'
  const rsiLabel   = { overbought: '과매수', oversold: '과매도', neutral: '중립' }[rsiSignal] || '-'
  const stochLabel = { overbought: '과매수', oversold: '과매도', neutral: '중립' }[stochSignal] || '-'

  const commonXAxisProps = {
    dataKey:       'time',
    tickFormatter,
    tick:          { fontSize: 9 },
    interval:      xInterval,
  }

  return (
    <div className="space-y-3">

      {/* ── 타임프레임 / 기간 선택 ──────────────────────────────────────────── */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="flex rounded border border-gray-200 overflow-hidden text-xs">
          {INTERVAL_OPTS.map(opt => (
            <button
              key={opt.id}
              onClick={() => handleIntervalChange(opt.id)}
              className={`px-3 py-1.5 font-medium transition-colors ${
                activeInterval === opt.id
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="flex rounded border border-gray-200 overflow-hidden text-xs">
          {(PERIOD_OPTIONS[activeInterval] || []).map(opt => (
            <button
              key={opt.id}
              onClick={() => setActivePeriod(opt.id)}
              className={`px-3 py-1.5 font-medium transition-colors ${
                activePeriod === opt.id
                  ? 'bg-gray-700 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {ohlcvLoading && (
          <div className="flex items-center gap-1.5 text-xs text-gray-400">
            <div className="w-3.5 h-3.5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
            로딩 중...
          </div>
        )}
      </div>

      {/* ── 시그널 요약 카드 ─────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-2 p-3 bg-gray-50 rounded-lg border border-gray-200">
        <SignalBadge
          label="MACD" value={macdLabel}
          type={macdCross === 'golden' ? 'golden' : macdCross === 'dead' ? 'dead' : 'neutral'}
        />
        <SignalBadge
          label={`RSI ${rsiVal != null ? rsiVal.toFixed(1) : ''}`}
          value={rsiLabel} type={rsiSignal}
        />
        <SignalBadge
          label={`스토캐스틱 ${stochK != null ? stochK.toFixed(1) : ''}`}
          value={stochLabel} type={stochSignal}
        />
        <SignalBadge label="MA20" value={aboveMa20 ? '상회' : '하회'} type={aboveMa20 ? 'up' : 'down'} />

        {/* MA 정배열/역배열 */}
        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs border font-medium ${
          maAlignment === '정배열'
            ? 'bg-red-50 text-red-700 border-red-300'
            : maAlignment === '역배열'
            ? 'bg-blue-50 text-blue-700 border-blue-300'
            : 'bg-gray-100 text-gray-600 border-gray-300'
        }`}>
          MA배열: {maAlignment}
        </span>

        {/* ATR */}
        {atrVal != null && (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs border bg-gray-100 text-gray-600 border-gray-300 font-medium">
            ATR(14): {atrVal.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </span>
        )}

        {/* 변동성 돌파 목표가 K=0.3/0.5/0.7 */}
        {[
          { label: 'K=0.3', val: vtK03 },
          { label: 'K=0.5', val: vtK05 },
          { label: 'K=0.7', val: vtK07 },
        ].filter(x => x.val != null).map(({ label, val }) => (
          <span key={label} className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs border bg-purple-50 text-purple-700 border-purple-300 font-medium">
            변동성돌파{label}: {val.toLocaleString()}
          </span>
        ))}
      </div>

      {/* ── 캔들스틱 + MA + BB ─────────────────────────────────────────────── */}
      <div>
        <p className="text-xs font-semibold text-gray-600 mb-1">
          가격 ({INTERVAL_LABEL[activeInterval]})
        </p>
        <CandlestickChart
          ohlcv={ohlcv}
          indicators={indicators}
          interval={activeInterval}
          height={280}
          volumeHeight={70}
          showMA60
          extraChartData={extraChartData}
        />
      </div>

      {/* ── MACD ───────────────────────────────────────────────────────────── */}
      <div>
        <p className="text-xs font-semibold text-gray-600 mb-1">MACD</p>
        <ResponsiveContainer width="100%" height={110}>
          <ComposedChart data={subChartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <XAxis {...commonXAxisProps} />
            <YAxis tick={{ fontSize: 9 }} width={50} />
            <Tooltip formatter={v => v?.toFixed(4)} labelFormatter={tooltipFormatter} />
            <ReferenceLine y={0} stroke="#e2e8f0" />
            <Bar
              dataKey="macdHist"
              isAnimationActive={false}
              shape={(props) => {
                const v = props.payload?.macdHist
                const { x, y, width, height } = props
                return (
                  <rect
                    x={x} y={y}
                    width={Math.max(width, 1)} height={Math.max(height, 0)}
                    fill={v >= 0 ? '#ef4444' : '#3b82f6'}
                  />
                )
              }}
              name="히스토그램"
            />
            <Line type="monotone" dataKey="macd"       stroke="#3b82f6" strokeWidth={1.5} dot={false} name="MACD" />
            <Line type="monotone" dataKey="macdSignal" stroke="#f59e0b" strokeWidth={1.5} dot={false} name="Signal" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* ── RSI ────────────────────────────────────────────────────────────── */}
      <div>
        <p className="text-xs font-semibold text-gray-600 mb-1">RSI (14)</p>
        <ResponsiveContainer width="100%" height={90}>
          <LineChart data={subChartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <XAxis {...commonXAxisProps} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 9 }} width={30} />
            <Tooltip formatter={v => v?.toFixed(1)} labelFormatter={tooltipFormatter} />
            <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="3 3" />
            <ReferenceLine y={30} stroke="#3b82f6" strokeDasharray="3 3" />
            <Line type="monotone" dataKey="rsi" stroke="#8b5cf6" strokeWidth={1.5} dot={false} name="RSI" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* ── Stochastic ─────────────────────────────────────────────────────── */}
      <div>
        <p className="text-xs font-semibold text-gray-600 mb-1">Stochastic (14,3)</p>
        <ResponsiveContainer width="100%" height={90}>
          <LineChart data={subChartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <XAxis {...commonXAxisProps} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 9 }} width={30} />
            <Tooltip formatter={v => v?.toFixed(1)} labelFormatter={tooltipFormatter} />
            <ReferenceLine y={80} stroke="#ef4444" strokeDasharray="3 3" />
            <ReferenceLine y={20} stroke="#3b82f6" strokeDasharray="3 3" />
            <Line type="monotone" dataKey="stochK" stroke="#10b981" strokeWidth={1.5} dot={false} name="%K" />
            <Line type="monotone" dataKey="stochD" stroke="#f59e0b" strokeWidth={1.5} dot={false} name="%D" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* ── PER/PBR 밸류에이션 (1d/1wk만) ────────────────────────────────── */}
      {(activeInterval === '1d' || activeInterval === '1wk') && (
        <div className="mt-4">
          <p className="text-xs font-semibold text-gray-600 mb-2">PER / PBR 밸류에이션</p>
          {valLoading ? (
            <div className="flex items-center gap-1.5 text-xs text-gray-400 py-4 justify-center">
              <div className="w-3.5 h-3.5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
              로딩 중...
            </div>
          ) : (
            <ValuationChart data={valData} compact />
          )}
        </div>
      )}

      {/* ── KIS 전략 신호 (MCP 연동) ────────────────────────────────── */}
      <StrategySignalCard strategySignals={data?.strategy_signals} symbol={symbol} />

    </div>
  )
}

// ── KIS 전략 신호 카드 ─────────────────────────────────────────
function StrategySignalCard({ strategySignals, symbol }) {
  if (!strategySignals) return null

  const signals = strategySignals.signals || []
  const consensus = strategySignals.consensus || 'HOLD'
  const avgStrength = strategySignals.avg_strength
  const bt = strategySignals.backtest_metrics

  const signalColor = (s) => {
    if (s === 'BUY') return 'bg-red-50 text-red-700 border-red-200'
    if (s === 'SELL') return 'bg-blue-50 text-blue-700 border-blue-200'
    return 'bg-gray-50 text-gray-600 border-gray-200'
  }

  const STRATEGY_LABELS = {
    sma_crossover: 'SMA 크로스',
    momentum: '모멘텀',
    trend_filter_signal: '추세 필터',
  }

  return (
    <div className="mt-4 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg border border-indigo-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-semibold text-indigo-800">KIS 전략 신호 (퀀트 백테스팅)</p>
        {symbol && (
          <a
            href={`/backtest`}
            className="text-xs text-indigo-600 hover:text-indigo-800 underline"
          >
            상세 백테스트 &rarr;
          </a>
        )}
      </div>

      {/* 개별 전략 신호 */}
      <div className="space-y-1.5 mb-3">
        {signals.map((s) => (
          <div key={s.strategy} className="flex items-center justify-between">
            <span className="text-xs text-gray-700">{STRATEGY_LABELS[s.strategy] || s.strategy}</span>
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 rounded text-xs font-medium border ${signalColor(s.signal)}`}>
                {s.signal}
              </span>
              <span className="text-xs text-gray-500 w-10 text-right">
                {(s.strength * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* 합의 */}
      <div className="flex items-center justify-between pt-2 border-t border-indigo-200">
        <span className="text-xs font-medium text-gray-700">전략 합의</span>
        <div className="flex items-center gap-2">
          <span className={`px-2.5 py-0.5 rounded text-xs font-bold border ${signalColor(consensus)}`}>
            {consensus}
          </span>
          {avgStrength != null && (
            <span className="text-xs text-gray-500">평균 {(avgStrength * 100).toFixed(0)}%</span>
          )}
        </div>
      </div>

      {/* 백테스트 메트릭 */}
      {bt && (
        <div className="mt-2 pt-2 border-t border-indigo-200 grid grid-cols-4 gap-2 text-center">
          {bt.total_return_pct != null && (
            <div>
              <div className="text-[10px] text-gray-500">수익률</div>
              <div className={`text-xs font-semibold ${bt.total_return_pct >= 0 ? 'text-red-600' : 'text-blue-600'}`}>
                {bt.total_return_pct >= 0 ? '+' : ''}{bt.total_return_pct.toFixed(1)}%
              </div>
            </div>
          )}
          {bt.sharpe_ratio != null && (
            <div>
              <div className="text-[10px] text-gray-500">샤프</div>
              <div className="text-xs font-semibold">{bt.sharpe_ratio.toFixed(2)}</div>
            </div>
          )}
          {bt.max_drawdown != null && (
            <div>
              <div className="text-[10px] text-gray-500">낙폭</div>
              <div className="text-xs font-semibold text-blue-600">{bt.max_drawdown.toFixed(1)}%</div>
            </div>
          )}
          {bt.win_rate != null && (
            <div>
              <div className="text-[10px] text-gray-500">승률</div>
              <div className="text-xs font-semibold">{bt.win_rate.toFixed(1)}%</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
