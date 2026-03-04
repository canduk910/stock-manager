/**
 * 기술적 분석 탭
 * 캔들스틱 + MA + 거래량 + MACD + RSI + Stochastic
 */
import {
  ComposedChart, Bar, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, LineChart, BarChart,
} from 'recharts'

// ── 시그널 배지 ────────────────────────────────────────────────────────────
function SignalBadge({ label, value, type }) {
  const color = {
    golden: 'bg-red-100 text-red-700 border-red-300',
    dead:   'bg-blue-100 text-blue-700 border-blue-300',
    overbought: 'bg-blue-100 text-blue-700 border-blue-300',
    oversold:   'bg-red-100 text-red-700 border-red-300',
    neutral: 'bg-gray-100 text-gray-600 border-gray-300',
    up:  'bg-red-100 text-red-700 border-red-300',
    down: 'bg-blue-100 text-blue-700 border-blue-300',
  }[type] || 'bg-gray-100 text-gray-600 border-gray-300'

  const arrow = {
    golden: '↑', dead: '↓', overbought: '↑', oversold: '↓',
    up: '↑', down: '↓',
  }[type] || ''

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs border font-medium ${color}`}>
      {label}: {value} {arrow}
    </span>
  )
}

// ── 캔들스틱 Bar (커스텀 Shape) ───────────────────────────────────────────
function CandleShape(props) {
  const { x, y, width, payload } = props
  if (!payload) return null
  const { open, close, high, low } = payload
  if (open == null || close == null) return null

  const isUp = close >= open
  const color = isUp ? '#ef4444' : '#3b82f6'
  const bodyTop = isUp ? close : open
  const bodyBot = isUp ? open : close

  // Y 좌표 계산: recharts YAxis의 scale이 props에 없으므로 직접 계산 생략
  // ComposedChart 내 Bar shape는 y/height가 자동으로 계산된 값
  return (
    <g>
      <line x1={x + width / 2} y1={props.background?.y || 0} x2={x + width / 2} y2={y} stroke={color} strokeWidth={1} />
      <rect
        x={x + 1}
        y={y}
        width={Math.max(width - 2, 1)}
        height={Math.max(props.height, 1)}
        fill={color}
        stroke={color}
      />
    </g>
  )
}

// ── 차트 공통 틱 포맷 ─────────────────────────────────────────────────────
function shortTime(val) {
  if (!val) return ''
  // "2026-03-04T09:15:00" → "09:15"
  const parts = val.split('T')
  if (parts[1]) return parts[1].slice(0, 5)
  return val.slice(5, 10) // fallback: MM-DD
}

// ── 메인 컴포넌트 ─────────────────────────────────────────────────────────
export default function TechnicalPanel({ data }) {
  const technical = data?.technical || {}
  const ohlcv = technical.ohlcv || []
  const indicators = technical.indicators || {}
  const signals = indicators.current_signals || {}
  const macd = indicators.macd || {}
  const rsi = indicators.rsi || {}
  const stoch = indicators.stoch || {}
  const bb = indicators.bb || {}
  const ma = indicators.ma || {}

  const times = macd.times || rsi.times || ohlcv.map(b => b.time)

  // 차트 데이터 병합
  const chartData = times.map((t, i) => ({
    time: t,
    open: ohlcv[i]?.open,
    high: ohlcv[i]?.high,
    low: ohlcv[i]?.low,
    close: ohlcv[i]?.close,
    volume: ohlcv[i]?.volume,
    macd: (macd.macd || [])[i],
    macdSignal: (macd.signal || [])[i],
    macdHist: (macd.histogram || [])[i],
    rsi: (rsi.values || [])[i],
    stochK: (stoch.k || [])[i],
    stochD: (stoch.d || [])[i],
    bbUpper: (bb.upper || [])[i],
    bbMid: (bb.mid || [])[i],
    bbLower: (bb.lower || [])[i],
    ma5: (ma.ma5 || [])[i],
    ma20: (ma.ma20 || [])[i],
    ma60: (ma.ma60 || [])[i],
  }))

  const hasOhlcv = ohlcv.length > 0

  if (!hasOhlcv) {
    return (
      <div className="text-center py-12 text-gray-400 text-sm">
        15분봉 데이터가 없습니다.
        <br />
        <span className="text-xs">새로고침을 클릭하여 데이터를 수집해주세요.</span>
      </div>
    )
  }

  // 시그널 요약
  const macdCross = signals.macd_cross || 'none'
  const rsiSignal = signals.rsi_signal || 'neutral'
  const rsiVal = signals.rsi_value
  const stochSignal = signals.stoch_signal || 'neutral'
  const stochK = signals.stoch_k
  const aboveMa20 = signals.above_ma20
  const volTarget = indicators.volatility_target

  const macdLabel = { golden: '골든크로스', dead: '데드크로스', none: '크로스없음' }[macdCross] || '-'
  const rsiLabel = { overbought: '과매수', oversold: '과매도', neutral: '중립' }[rsiSignal] || '-'
  const stochLabel = { overbought: '과매수', oversold: '과매도', neutral: '중립' }[stochSignal] || '-'

  return (
    <div className="space-y-3">
      {/* 시그널 요약 */}
      <div className="flex flex-wrap gap-2 p-3 bg-gray-50 rounded-lg border border-gray-200">
        <SignalBadge
          label="MACD"
          value={macdLabel}
          type={macdCross === 'golden' ? 'golden' : macdCross === 'dead' ? 'dead' : 'neutral'}
        />
        <SignalBadge
          label={`RSI ${rsiVal != null ? rsiVal.toFixed(1) : ''}`}
          value={rsiLabel}
          type={rsiSignal}
        />
        <SignalBadge
          label={`스토캐스틱 ${stochK != null ? stochK.toFixed(1) : ''}`}
          value={stochLabel}
          type={stochSignal}
        />
        <SignalBadge
          label="MA20"
          value={aboveMa20 ? '상회' : '하회'}
          type={aboveMa20 ? 'up' : 'down'}
        />
        {volTarget != null && (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs border bg-purple-50 text-purple-700 border-purple-300 font-medium">
            변동성 돌파 목표가: {volTarget.toLocaleString()}
          </span>
        )}
      </div>

      {/* 캔들 + MA + BB */}
      <div>
        <p className="text-xs font-semibold text-gray-600 mb-1">가격 (15분봉)</p>
        <ResponsiveContainer width="100%" height={260}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <XAxis dataKey="time" tickFormatter={shortTime} tick={{ fontSize: 9 }} interval="preserveStartEnd" />
            <YAxis domain={['auto', 'auto']} tick={{ fontSize: 10 }} width={60} tickFormatter={v => v.toLocaleString()} />
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const d = payload[0]?.payload
                if (!d) return null
                return (
                  <div className="bg-white border border-gray-200 rounded shadow p-2 text-xs">
                    <p className="text-gray-500 mb-1">{shortTime(d.time)}</p>
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
            <Line type="monotone" dataKey="bbMid" stroke="#64748b" strokeWidth={1} dot={false} strokeDasharray="3 3" name="BB중간" />
            <Line type="monotone" dataKey="bbLower" stroke="#94a3b8" strokeWidth={1} dot={false} strokeDasharray="3 3" name="BB하단" />
            {/* 이동평균 */}
            <Line type="monotone" dataKey="ma5" stroke="#f59e0b" strokeWidth={1.5} dot={false} name="MA5" />
            <Line type="monotone" dataKey="ma20" stroke="#8b5cf6" strokeWidth={1.5} dot={false} name="MA20" />
            <Line type="monotone" dataKey="ma60" stroke="#06b6d4" strokeWidth={1.5} dot={false} name="MA60" />
            {/* 캔들 (종가 기준 Bar — 간략 표현) */}
            <Bar
              dataKey="close"
              fill="#ef4444"
              shape={(props) => {
                const d = props.payload
                if (!d?.open || !d?.close) return null
                const isUp = d.close >= d.open
                return <rect {...props} fill={isUp ? '#ef4444' : '#3b82f6'} />
              }}
              barSize={4}
              name="종가"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* 거래량 */}
      <div>
        <p className="text-xs font-semibold text-gray-600 mb-1">거래량</p>
        <ResponsiveContainer width="100%" height={70}>
          <BarChart data={chartData} margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
            <XAxis dataKey="time" tickFormatter={shortTime} tick={{ fontSize: 9 }} interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 9 }} width={50} tickFormatter={v => (v / 1000).toFixed(0) + 'K'} />
            <Tooltip formatter={(v) => v?.toLocaleString()} />
            <Bar dataKey="volume" fill="#94a3b8" barSize={3} name="거래량" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* MACD */}
      <div>
        <p className="text-xs font-semibold text-gray-600 mb-1">MACD</p>
        <ResponsiveContainer width="100%" height={110}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <XAxis dataKey="time" tickFormatter={shortTime} tick={{ fontSize: 9 }} interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 9 }} width={50} />
            <Tooltip formatter={(v) => v?.toFixed(4)} />
            <ReferenceLine y={0} stroke="#e2e8f0" />
            <Bar dataKey="macdHist" fill="#94a3b8"
              shape={(props) => {
                const v = props.payload?.macdHist
                return <rect {...props} fill={v >= 0 ? '#ef4444' : '#3b82f6'} />
              }}
              barSize={3} name="히스토그램"
            />
            <Line type="monotone" dataKey="macd" stroke="#3b82f6" strokeWidth={1.5} dot={false} name="MACD" />
            <Line type="monotone" dataKey="macdSignal" stroke="#f59e0b" strokeWidth={1.5} dot={false} name="Signal" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* RSI */}
      <div>
        <p className="text-xs font-semibold text-gray-600 mb-1">RSI (14)</p>
        <ResponsiveContainer width="100%" height={90}>
          <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <XAxis dataKey="time" tickFormatter={shortTime} tick={{ fontSize: 9 }} interval="preserveStartEnd" />
            <YAxis domain={[0, 100]} tick={{ fontSize: 9 }} width={30} />
            <Tooltip formatter={(v) => v?.toFixed(1)} />
            <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="3 3" />
            <ReferenceLine y={30} stroke="#3b82f6" strokeDasharray="3 3" />
            <Line type="monotone" dataKey="rsi" stroke="#8b5cf6" strokeWidth={1.5} dot={false} name="RSI" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Stochastic */}
      <div>
        <p className="text-xs font-semibold text-gray-600 mb-1">Stochastic (14,3)</p>
        <ResponsiveContainer width="100%" height={90}>
          <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <XAxis dataKey="time" tickFormatter={shortTime} tick={{ fontSize: 9 }} interval="preserveStartEnd" />
            <YAxis domain={[0, 100]} tick={{ fontSize: 9 }} width={30} />
            <Tooltip formatter={(v) => v?.toFixed(1)} />
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
