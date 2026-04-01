import { ResponsiveContainer, AreaChart, Area, YAxis, Tooltip } from 'recharts'
import LoadingSpinner from '../common/LoadingSpinner'
import ErrorAlert from '../common/ErrorAlert'

function IndexCard({ index }) {
  const { symbol, name, price, change, change_pct: changePct, sparkline } = index
  const isUp = change > 0
  const isDown = change < 0
  const color = isUp ? '#ef4444' : isDown ? '#3b82f6' : '#6b7280'
  const sign = isUp ? '+' : ''
  const gradId = `grad-${symbol.replace(/[^a-zA-Z0-9]/g, '')}`

  // sparkline: [{date, v}] 또는 [float] (하위호환)
  const chartData = (sparkline || []).map((item, i) =>
    typeof item === 'object' ? item : { i, v: item }
  )

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="text-sm font-medium text-gray-500 mb-1">{name}</div>
      <div className="text-2xl font-bold text-gray-900">
        {price != null ? price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}
      </div>
      <div className="flex items-center gap-2 mt-1">
        <span className="text-sm font-semibold" style={{ color }}>
          {change != null ? `${sign}${change.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : ''}
        </span>
        <span className="text-sm" style={{ color }}>
          {changePct != null ? `(${sign}${changePct.toFixed(2)}%)` : ''}
        </span>
      </div>
      {chartData.length > 0 && (
        <div className="mt-3 h-16">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <YAxis domain={['dataMin', 'dataMax']} hide />
              <Tooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.[0]) return null
                  const d = payload[0].payload
                  return (
                    <div className="rounded bg-gray-800 text-white text-xs px-2 py-1 shadow">
                      <div>{d.date}</div>
                      <div className="font-semibold">{d.v?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                    </div>
                  )
                }}
                cursor={{ stroke: '#9ca3af', strokeWidth: 1 }}
              />
              <defs>
                <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={color} stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="v"
                stroke={color}
                strokeWidth={1.5}
                fill={`url(#${gradId})`}
                dot={false}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

export default function IndexSection({ data, loading, error }) {
  if (loading) return <LoadingSpinner message="지수 로딩 중..." />
  if (error) return <ErrorAlert message={error} />
  if (!data?.indices?.length) return null

  return (
    <section>
      <h2 className="text-lg font-semibold text-gray-900 mb-3">주요 지수</h2>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {data.indices.map((idx) => (
          <IndexCard key={idx.symbol} index={idx} />
        ))}
      </div>
    </section>
  )
}
