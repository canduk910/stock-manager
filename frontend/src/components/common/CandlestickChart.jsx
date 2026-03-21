/**
 * 공통 캔들스틱 차트 컴포넌트.
 * 캔들스틱 + MA(5/20/60) + 볼린저밴드 + 거래량.
 * PriceChartPanel과 TechnicalPanel에서 공유.
 *
 * Props:
 *   ohlcv       - [{time, open, high, low, close, volume}, ...]
 *   indicators  - {bb: {upper, mid, lower}, ma: {ma5, ma20, ma60}}
 *   interval    - '15m' | '60m' | '1d' | '1wk'
 *   height      - 캔들 차트 높이 (default: 280)
 *   volumeHeight- 거래량 차트 높이 (default: 70)
 *   showMA60    - MA60 표시 여부 (default: false)
 *   showVolume  - 거래량 차트 표시 여부 (default: true)
 *   extraChartData - 추가 데이터 키 (MACD 등 병합용)
 */
import { useMemo, useCallback } from 'react'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, BarChart,
} from 'recharts'

// ── 타임프레임/기간 옵션 (PriceChartPanel, TechnicalPanel 공용 export) ────────
export const INTERVAL_OPTS = [
  { id: '15m', label: '15분' },
  { id: '60m', label: '60분' },
  { id: '1d',  label: '1일'  },
  { id: '1wk', label: '1주'  },
]

export const PERIOD_OPTIONS = {
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

// ── X축 레이블 포맷 ───────────────────────────────────────────────────────
export function makeTickFormatter(interval) {
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
export default function CandlestickChart({
  ohlcv = [],
  indicators = {},
  interval = '1d',
  height = 280,
  volumeHeight = 70,
  showMA60 = false,
  showVolume = true,
  extraChartData,
  xTickDivisor = 8,
}) {
  const bb = indicators.bb || {}
  const ma = indicators.ma || {}

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
    const { x, y, width, height: h, payload } = props
    if (!payload) return null
    const isUp = (payload.close ?? 0) >= (payload.open ?? 0)
    return (
      <rect
        x={x} y={y} width={Math.max(width, 1)} height={Math.max(h, 0)}
        fill={isUp ? '#ef4444' : '#3b82f6'}
        opacity={0.7}
      />
    )
  }, [])

  // ── 차트 데이터 병합 ──────────────────────────────────────────────────
  const chartData = useMemo(() =>
    ohlcv.map((d, i) => ({
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
      ma60:    (ma.ma60  || [])[i],
      ...(extraChartData ? extraChartData(d, i) : {}),
    })),
  [ohlcv, bb, ma, extraChartData])

  const tickFormatter = makeTickFormatter(interval)
  const xInterval = Math.max(Math.floor(chartData.length / xTickDivisor), 1)

  const commonXAxisProps = {
    dataKey:       'time',
    tickFormatter,
    tick:          { fontSize: 9 },
    interval:      xInterval,
  }

  if (!ohlcv.length) return null

  return (
    <>
      {/* 캔들스틱 + MA + BB */}
      <ResponsiveContainer width="100%" height={height}>
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
          {showMA60 && <Line type="monotone" dataKey="ma60" stroke="#06b6d4" strokeWidth={1.5} dot={false} name="MA60" />}
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
      {showVolume && (
        <ResponsiveContainer width="100%" height={volumeHeight}>
          <BarChart data={chartData} margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
            <XAxis {...commonXAxisProps} hide={volumeHeight < 60} />
            <YAxis tick={{ fontSize: 9 }} width={50} tickFormatter={v => (v / 1000).toFixed(0) + 'K'} />
            <Tooltip formatter={v => v?.toLocaleString()} />
            <Bar dataKey="volume" shape={volumeShape} isAnimationActive={false} name="거래량" />
          </BarChart>
        </ResponsiveContainer>
      )}
    </>
  )
}
