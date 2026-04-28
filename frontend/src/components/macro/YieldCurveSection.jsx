import {
  ResponsiveContainer, LineChart, Line, AreaChart, Area,
  XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine,
} from 'recharts'
import LoadingSpinner from '../common/LoadingSpinner'
import ErrorAlert from '../common/ErrorAlert'

const fmt = (v) =>
  v != null
    ? v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : '-'

function CurrentRatesCards({ current, spread, inverted }) {
  const entries = [
    { label: '3개월', value: current?.['3m'] },
    { label: '5년', value: current?.['5y'] },
    { label: '10년', value: current?.['10y'] },
    { label: '30년', value: current?.['30y'] },
  ]
  return (
    <div className="flex flex-wrap gap-3 mb-4">
      {entries.map((e) => (
        <div key={e.label} className="rounded-lg border bg-white px-4 py-2 shadow-sm">
          <div className="text-xs text-gray-500">{e.label}</div>
          <div className="text-lg font-bold text-gray-900">{fmt(e.value)}%</div>
        </div>
      ))}
      <div className="rounded-lg border bg-white px-4 py-2 shadow-sm">
        <div className="text-xs text-gray-500">10Y-3M 스프레드</div>
        <div className={`text-lg font-bold ${spread < 0 ? 'text-red-600' : 'text-emerald-600'}`}>
          {fmt(spread)}%
        </div>
      </div>
      {inverted && (
        <div className="flex items-center">
          <span className="inline-block px-2 py-1 rounded bg-red-100 text-red-700 text-xs font-semibold">
            역전 경고
          </span>
        </div>
      )}
    </div>
  )
}

function CurveShapeChart({ current }) {
  if (!current) return null
  const points = [
    { maturity: '3M', rate: current['3m'] },
    { maturity: '5Y', rate: current['5y'] },
    { maturity: '10Y', rate: current['10y'] },
    { maturity: '30Y', rate: current['30y'] },
  ].filter((p) => p.rate != null)

  // 역전 구간 감지
  const isInverted = (i) => i > 0 && points[i].rate < points[i - 1].rate

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="text-sm font-medium text-gray-500 mb-2">수익률 곡선</div>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="maturity" tick={{ fontSize: 12 }} />
            <YAxis
              tick={{ fontSize: 12 }}
              domain={['auto', 'auto']}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              formatter={(v) => [`${fmt(v)}%`, '수익률']}
              contentStyle={{ fontSize: 12, borderRadius: 8 }}
            />
            <Line
              type="monotone"
              dataKey="rate"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={(props) => {
                const { cx, cy, index } = props
                const inv = isInverted(index)
                return (
                  <circle
                    key={index}
                    cx={cx}
                    cy={cy}
                    r={5}
                    fill={inv ? '#ef4444' : '#3b82f6'}
                    stroke="white"
                    strokeWidth={2}
                  />
                )
              }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function SpreadHistoryChart({ history }) {
  if (!history?.length) return null

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="text-sm font-medium text-gray-500 mb-2">10Y-3M 스프레드 추이</div>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={history}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11 }}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 12 }}
              domain={['auto', 'auto']}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              formatter={(v) => [`${fmt(v)}%`, '스프레드']}
              labelFormatter={(l) => l}
              contentStyle={{ fontSize: 12, borderRadius: 8 }}
            />
            <ReferenceLine y={0} stroke="#6b7280" strokeDasharray="4 4" strokeWidth={1.5} />
            <defs>
              <linearGradient id="spreadPos" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#22c55e" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#22c55e" stopOpacity={0.05} />
              </linearGradient>
              <linearGradient id="spreadNeg" x1="0" y1="1" x2="0" y2="0">
                <stop offset="0%" stopColor="#ef4444" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#ef4444" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey="spread"
              stroke="#6b7280"
              strokeWidth={1.5}
              fill="url(#spreadPos)"
              dot={false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default function YieldCurveSection({ data, loading, error }) {
  if (loading) return <LoadingSpinner message="금리 데이터 로딩 중..." />
  if (error) return <ErrorAlert message={error} />
  if (!data) return null

  // API 응답: { yield_curve: {...}, updated_at, errors }
  const yc = data.yield_curve || data

  return (
    <section>
      <h2 className="text-lg font-semibold text-gray-900 mb-3">장단기 금리차</h2>
      <CurrentRatesCards
        current={yc.current}
        spread={yc.spread_10y_3m}
        inverted={yc.inverted}
      />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CurveShapeChart current={yc.current} />
        <SpreadHistoryChart history={yc.history} />
      </div>
    </section>
  )
}
