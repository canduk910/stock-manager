/**
 * 주문 페이지 가격 차트 패널.
 * 캔들스틱 + MA5/MA20 + 볼린저밴드 + 거래량.
 * RSI/MACD/Stochastic 없이 가격·거래량만 표시.
 *
 * Props:
 *   symbol  - 종목코드 (예: '005930', 'AAPL')
 *   market  - 'KR' | 'US'
 */
import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, BarChart,
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
    { id: '30d', label: '1개월' },
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
    { id: '2y',  label: '2년'   },
    { id: '5y',  label: '5년'   },
    { id: '10y', label: '10년'  },
  ],
  '1wk': [
    { id: '1y',  label: '1년'  },
    { id: '2y',  label: '2년'  },
    { id: '5y',  label: '5년'  },
    { id: '10y', label: '10년' },
  ],
}

const DEFAULT_PERIOD = { '15m': '5d', '60m': '3mo', '1d': '3mo', '1wk': '1y' }

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
export default function PriceChartPanel({ symbol, market = 'KR' }) {
  const [activeInterval, setActiveInterval] = useState('1d')
  const [activePeriod,   setActivePeriod]   = useState('3mo')

  const { result, loading, load } = useAdvisoryOhlcv()
  const debounceRef = useRef(null)

  // symbol / interval / period 변경 시 API 호출 (symbol 변경은 500ms debounce)
  useEffect(() => {
    if (!symbol) return
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      load(symbol, market, activeInterval, activePeriod)
    }, 500)
    return () => clearTimeout(debounceRef.current)
  }, [symbol, market, activeInterval, activePeriod]) // eslint-disable-line

  const handleIntervalChange = (newInterval) => {
    setActiveInterval(newInterval)
    setActivePeriod(DEFAULT_PERIOD[newInterval])
  }

  const ohlcv      = result?.ohlcv      || []
  const indicators = result?.indicators || {}
  const bb         = indicators.bb      || {}
  const ma         = indicators.ma      || {}

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
        <line x1={cx} y1={yH} x2={cx} y2={yL} stroke={color} strokeWidth={1} />
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
  const chartData = ohlcv.map((d, i) => ({
    time:    d.time,
    open:    d.open,
    high:    d.high,
    low:     d.low,
    close:   d.close,
    volume:  d.volume,
    bbUpper: (bb.upper || [])[i],
    bbMid:   (bb.mid   || [])[i],
    bbLower: (bb.lower || [])[i],
    ma5:     (ma.ma5   || [])[i],
    ma20:    (ma.ma20  || [])[i],
  }))

  const tickFormatter = makeTickFormatter(activeInterval)
  const xInterval     = Math.max(Math.floor(chartData.length / 6), 1)

  const commonXAxisProps = {
    dataKey:       'time',
    tickFormatter: tickFormatter,
    tick:          { fontSize: 9 },
    interval:      xInterval,
  }

  if (!symbol) return null

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
      {/* 헤더 + 타임프레임 선택 */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <span className="text-xs font-semibold text-gray-700">가격 차트</span>
        <div className="flex items-center gap-2 flex-wrap">
          {/* interval 선택 */}
          <div className="flex rounded border border-gray-200 overflow-hidden text-xs">
            {INTERVAL_OPTS.map(opt => (
              <button
                key={opt.id}
                onClick={() => handleIntervalChange(opt.id)}
                className={`px-2.5 py-1 font-medium transition-colors ${
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
                className={`px-2.5 py-1 font-medium transition-colors ${
                  activePeriod === opt.id
                    ? 'bg-gray-700 text-white'
                    : 'bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {loading && (
            <div className="flex items-center gap-1 text-xs text-gray-400">
              <div className="w-3 h-3 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
              로딩 중...
            </div>
          )}
        </div>
      </div>

      {/* 데이터 없음 */}
      {!loading && ohlcv.length === 0 && (
        <div className="text-center py-8 text-gray-400 text-xs">
          차트 데이터가 없습니다
        </div>
      )}

      {/* 캔들스틱 + MA + BB 차트 */}
      {ohlcv.length > 0 && (
        <>
          <ResponsiveContainer width="100%" height={240}>
            <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <XAxis {...commonXAxisProps} />
              <YAxis
                domain={priceDomain}
                tick={{ fontSize: 9 }}
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
              {/* 캔들스틱 */}
              <Bar
                dataKey="close"
                background={{ fill: 'transparent' }}
                shape={candleShape}
                isAnimationActive={false}
              />
            </ComposedChart>
          </ResponsiveContainer>

          {/* 거래량 */}
          <ResponsiveContainer width="100%" height={55}>
            <BarChart data={chartData} margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
              <XAxis {...commonXAxisProps} hide />
              <YAxis tick={{ fontSize: 9 }} width={50} tickFormatter={v => (v / 1000).toFixed(0) + 'K'} />
              <Tooltip formatter={v => v?.toLocaleString()} />
              <Bar dataKey="volume" shape={volumeShape} isAnimationActive={false} name="거래량" />
            </BarChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  )
}
