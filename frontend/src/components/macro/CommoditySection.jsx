import { ResponsiveContainer, AreaChart, Area, YAxis, Tooltip } from 'recharts'
import LoadingSpinner from '../common/LoadingSpinner'
import ErrorAlert from '../common/ErrorAlert'

const fmt = (v) =>
  v != null
    ? v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : '-'

function CommodityCard({ item }) {
  const { symbol, name, price, change, change_pct, sparkline } = item
  const isUp = change > 0
  const isDown = change < 0
  const color = isUp ? '#ef4444' : isDown ? '#3b82f6' : '#6b7280'
  const sign = isUp ? '+' : ''
  const gradId = `comm-${symbol.replace(/[^a-zA-Z0-9]/g, '')}`

  const chartData = (sparkline || []).map((item, i) =>
    typeof item === 'object' ? item : { i, v: item }
  )

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="text-sm font-medium text-gray-500 mb-1">{name}</div>
      <div className="text-2xl font-bold text-gray-900">{fmt(price)}</div>
      <div className="flex items-center gap-2 mt-1">
        <span className="text-sm font-semibold" style={{ color }}>
          {change != null ? `${sign}${fmt(change)}` : ''}
        </span>
        <span className="text-sm" style={{ color }}>
          {change_pct != null ? `(${sign}${change_pct.toFixed(2)}%)` : ''}
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
                      {d.date && <div>{d.date}</div>}
                      <div className="font-semibold">{fmt(d.v)}</div>
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

export default function CommoditySection({ data, loading, error }) {
  if (loading) return <LoadingSpinner message="원자재 로딩 중..." />
  if (error) return <ErrorAlert message={error} />
  if (!data?.commodities?.length) return null

  return (
    <section>
      <h2 className="text-lg font-semibold text-gray-900 mb-3">원자재</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {data.commodities.map((item) => (
          <CommodityCard key={item.symbol} item={item} />
        ))}
      </div>
    </section>
  )
}
