/**
 * 기술적 분석 탭
 * 캔들스틱 + MA + BB + 거래량 + MACD + RSI + Stochastic
 * 타임프레임 (15분/60분/1일/1주) + 기간 선택 지원
 */
import { useState, useEffect, useMemo } from 'react'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, LineChart,
} from 'recharts'
import { useAdvisoryOhlcv } from '../../hooks/useAdvisory'
import CandlestickChart, {
  INTERVAL_OPTS,
  PERIOD_OPTIONS,
  makeTickFormatter,
} from '../common/CandlestickChart'

const DEFAULT_PERIOD  = { '15m': '60d', '60m': '6mo', '1d': '1y', '1wk': '3y' }
const INTERVAL_LABEL  = { '15m': '15분봉', '60m': '60분봉', '1d': '일봉', '1wk': '주봉' }

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
export default function TechnicalPanel({ data, symbol, market }) {
  const [activeInterval, setActiveInterval] = useState('15m')
  const [activePeriod,   setActivePeriod]   = useState('60d')

  const { result: fetchedResult, loading: ohlcvLoading, load: loadOhlcv } = useAdvisoryOhlcv()

  // interval/period 변경 시 API 호출
  useEffect(() => {
    if (symbol && market) {
      loadOhlcv(symbol, market, activeInterval, activePeriod)
    }
  }, [symbol, market, activeInterval, activePeriod]) // eslint-disable-line

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
            <Tooltip formatter={v => v?.toFixed(4)} />
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
            <Tooltip formatter={v => v?.toFixed(1)} />
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
            <Tooltip formatter={v => v?.toFixed(1)} />
            <ReferenceLine y={80} stroke="#ef4444" strokeDasharray="3 3" />
            <ReferenceLine y={20} stroke="#3b82f6" strokeDasharray="3 3" />
            <Line type="monotone" dataKey="stochK" stroke="#10b981" strokeWidth={1.5} dot={false} name="%K" />
            <Line type="monotone" dataKey="stochD" stroke="#f59e0b" strokeWidth={1.5} dot={false} name="%D" />
          </LineChart>
        </ResponsiveContainer>
      </div>

    </div>
  )
}
