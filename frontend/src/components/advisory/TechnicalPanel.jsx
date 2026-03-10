/**
 * 기술적 분석 탭
 * 캔들스틱 + MA + BB + 거래량 + MACD + RSI + Stochastic
 * 타임프레임 (15분/60분/1일/1주) + 기간 선택 지원
 *
 * [캔들 렌더링 원리]
 * Recharts Bar에 background={{ fill:'transparent' }} 를 주면
 * shape 함수에 background={x, y, width, height} 가 전달된다.
 *   - background.y      = 차트 플롯 영역 상단 픽셀 (= dMax 에 해당)
 *   - background.height = 차트 플롯 영역 높이 픽셀
 * YAxis domain=[dMin,dMax] 를 명시하면
 *   toY(v) = background.y + background.height * (dMax - v) / (dMax - dMin)
 * 으로 임의 가격 → 픽셀 변환이 가능하다.
 */
import { useState, useEffect, useMemo, useCallback } from 'react'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, LineChart, BarChart,
} from 'recharts'
import { useAdvisoryOhlcv } from '../../hooks/useAdvisory'

// ── 타임프레임/기간 옵션 ──────────────────────────────────────────────────────
const INTERVAL_OPTS = [
  { id: '15m', label: '15분' },
  { id: '60m', label: '60분' },
  { id: '1d',  label: '1일'  },
  { id: '1wk', label: '1주'  },
]

const PERIOD_OPTIONS = {
  '15m': [
    { id: '5d',  label: '5일'   },
    { id: '1mo', label: '1개월' },
    { id: '60d', label: '2개월' },
  ],
  '60m': [
    { id: '1mo', label: '1개월' },
    { id: '3mo', label: '3개월' },
    { id: '6mo', label: '6개월' },
    { id: '1y',  label: '1년'   },
    { id: '2y',  label: '2년'   },
  ],
  '1d': [
    { id: '3mo', label: '3개월' },
    { id: '6mo', label: '6개월' },
    { id: '1y',  label: '1년'   },
    { id: '3y',  label: '3년'   },
    { id: '5y',  label: '5년'   },
    { id: '10y', label: '10년'  },
  ],
  '1wk': [
    { id: '1y',  label: '1년'  },
    { id: '3y',  label: '3년'  },
    { id: '5y',  label: '5년'  },
    { id: '10y', label: '10년' },
  ],
}

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

// ── X축 레이블 포맷 ───────────────────────────────────────────────────────
function makeTickFormatter(interval) {
  if (interval === '1d' || interval === '1wk') {
    return (val) => {
      if (!val) return ''
      const date = val.split('T')[0]
      return date.slice(5)   // MM-DD
    }
  }
  return (val) => {
    if (!val) return ''
    const [date, time] = val.split('T')
    if (!time) return val.slice(5, 10)
    return `${date.slice(5)} ${time.slice(0, 5)}`  // MM-DD HH:mm
  }
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
  const bb      = indicators.bb     || {}
  const ma      = indicators.ma     || {}

  const times = macd.times || rsi.times || ohlcv.map(b => b.time)

  // ── 가격 Y축 도메인 (ohlcv + BB 포함, ±5% 여유) ────────────────────────
  const priceDomain = useMemo(() => {
    if (!ohlcv.length) return [0, 1]
    const vals = [
      ...ohlcv.map(d => d.low).filter(v => v != null),
      ...ohlcv.map(d => d.high).filter(v => v != null),
      ...(bb.upper || []).filter(v => v != null),
      ...(bb.lower || []).filter(v => v != null),
    ]
    if (!vals.length) return [0, 1]
    const minP = Math.min(...vals)
    const maxP = Math.max(...vals)
    const pad  = (maxP - minP) * 0.05
    return [minP - pad, maxP + pad]
  }, [ohlcv, bb])

  const [dMin, dMax] = priceDomain
  const dRange = dMax - dMin

  // ── 캔들스틱 Bar shape ─────────────────────────────────────────────────
  const candleShape = useCallback((props) => {
    const { x, width, background, payload } = props
    if (!payload) return null
    if (!background || !background.height) return null

    const chartTop = background.y
    const chartH   = background.height
    if (dRange <= 0 || chartH <= 0) return null

    const toY = (v) => chartTop + chartH * (dMax - v) / dRange

    const { open, high, low, close } = payload
    if (open == null || close == null || high == null || low == null) return null

    const isUp  = close >= open
    const color = isUp ? '#ef4444' : '#3b82f6'
    const cx    = x + width / 2
    const bw    = Math.max(width * 0.65, 1.5)

    const yH    = toY(high)
    const yL    = toY(low)
    const yO    = toY(open)
    const yC    = toY(close)
    const yTop  = Math.min(yO, yC)
    const yBot  = Math.max(yO, yC)
    const bodyH = Math.max(yBot - yTop, 1)

    return (
      <g>
        {/* 꼬리: 저가 ~ 고가 */}
        <line x1={cx} y1={yH} x2={cx} y2={yL} stroke={color} strokeWidth={1} />
        {/* 몸통: 시가 ~ 종가 */}
        <rect x={cx - bw / 2} y={yTop} width={bw} height={bodyH} fill={color} />
      </g>
    )
  }, [dMin, dMax, dRange])

  // ── 거래량 Bar shape (상승/하락 색 분리) ──────────────────────────────
  const volumeShape = useCallback((props) => {
    const { x, y, width, height, payload } = props
    if (!payload) return null
    const isUp = (payload.close ?? 0) >= (payload.open ?? 0)
    return (
      <rect
        x={x} y={y} width={Math.max(width, 1)} height={Math.max(height, 0)}
        fill={isUp ? '#ef4444' : '#3b82f6'}
        opacity={0.7}
      />
    )
  }, [])

  // ── 차트 데이터 병합 ──────────────────────────────────────────────────
  const chartData = times.map((t, i) => ({
    time:       t,
    open:       ohlcv[i]?.open,
    high:       ohlcv[i]?.high,
    low:        ohlcv[i]?.low,
    close:      ohlcv[i]?.close,
    volume:     ohlcv[i]?.volume,
    macd:       (macd.macd      || [])[i],
    macdSignal: (macd.signal    || [])[i],
    macdHist:   (macd.histogram || [])[i],
    rsi:        (rsi.values     || [])[i],
    stochK:     (stoch.k        || [])[i],
    stochD:     (stoch.d        || [])[i],
    bbUpper:    (bb.upper       || [])[i],
    bbMid:      (bb.mid         || [])[i],
    bbLower:    (bb.lower       || [])[i],
    ma5:        (ma.ma5         || [])[i],
    ma20:       (ma.ma20        || [])[i],
    ma60:       (ma.ma60        || [])[i],
  }))

  const tickFormatter = makeTickFormatter(activeInterval)
  const xInterval     = Math.max(Math.floor(chartData.length / 8), 1)

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
  const volTarget   = indicators.volatility_target

  const macdLabel  = { golden: '골든크로스', dead: '데드크로스', none: '크로스없음' }[macdCross] || '-'
  const rsiLabel   = { overbought: '과매수', oversold: '과매도', neutral: '중립' }[rsiSignal] || '-'
  const stochLabel = { overbought: '과매수', oversold: '과매도', neutral: '중립' }[stochSignal] || '-'

  const commonXAxisProps = {
    dataKey:       'time',
    tickFormatter: tickFormatter,
    tick:          { fontSize: 9 },
    interval:      xInterval,
  }

  return (
    <div className="space-y-3">

      {/* ── 타임프레임 / 기간 선택 ──────────────────────────────────────────── */}
      <div className="flex items-center gap-2 flex-wrap">
        {/* interval 선택 */}
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

        {/* period 선택 */}
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
        {volTarget != null && (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs border bg-purple-50 text-purple-700 border-purple-300 font-medium">
            변동성 돌파 목표가: {volTarget.toLocaleString()}
          </span>
        )}
      </div>

      {/* ── 캔들스틱 + MA + BB ─────────────────────────────────────────────── */}
      <div>
        <p className="text-xs font-semibold text-gray-600 mb-1">
          가격 ({INTERVAL_LABEL[activeInterval]})
        </p>
        <ResponsiveContainer width="100%" height={280}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <XAxis {...commonXAxisProps} />
            <YAxis
              domain={priceDomain}
              tick={{ fontSize: 10 }}
              width={65}
              tickFormatter={v => v.toLocaleString()}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const d = payload[0]?.payload
                if (!d) return null
                return (
                  <div className="bg-white border border-gray-200 rounded shadow p-2 text-xs">
                    <p className="text-gray-500 mb-1">{tickFormatter(d.time)}</p>
                    <p>시: {d.open?.toLocaleString()}</p>
                    <p>고: {d.high?.toLocaleString()}</p>
                    <p>저: {d.low?.toLocaleString()}</p>
                    <p className={d.close >= d.open ? 'text-red-600' : 'text-blue-600'}>
                      종: {d.close?.toLocaleString()}
                    </p>
                  </div>
                )
              }}
            />
            {/* 볼린저밴드 */}
            <Line type="monotone" dataKey="bbUpper" stroke="#94a3b8" strokeWidth={1} dot={false} strokeDasharray="3 3" name="BB상단" />
            <Line type="monotone" dataKey="bbMid"   stroke="#64748b" strokeWidth={1} dot={false} strokeDasharray="3 3" name="BB중간" />
            <Line type="monotone" dataKey="bbLower" stroke="#94a3b8" strokeWidth={1} dot={false} strokeDasharray="3 3" name="BB하단" />
            {/* 이동평균 */}
            <Line type="monotone" dataKey="ma5"  stroke="#f59e0b" strokeWidth={1.5} dot={false} name="MA5" />
            <Line type="monotone" dataKey="ma20" stroke="#8b5cf6" strokeWidth={1.5} dot={false} name="MA20" />
            <Line type="monotone" dataKey="ma60" stroke="#06b6d4" strokeWidth={1.5} dot={false} name="MA60" />
            {/* 캔들스틱 */}
            <Bar
              dataKey="close"
              background={{ fill: 'transparent' }}
              shape={candleShape}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* ── 거래량 ─────────────────────────────────────────────────────────── */}
      <div>
        <p className="text-xs font-semibold text-gray-600 mb-1">거래량</p>
        <ResponsiveContainer width="100%" height={70}>
          <BarChart data={chartData} margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
            <XAxis {...commonXAxisProps} />
            <YAxis tick={{ fontSize: 9 }} width={50} tickFormatter={v => (v / 1000).toFixed(0) + 'K'} />
            <Tooltip formatter={v => v?.toLocaleString()} />
            <Bar dataKey="volume" shape={volumeShape} isAnimationActive={false} name="거래량" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* ── MACD ───────────────────────────────────────────────────────────── */}
      <div>
        <p className="text-xs font-semibold text-gray-600 mb-1">MACD</p>
        <ResponsiveContainer width="100%" height={110}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
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
          <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
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
          <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
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
