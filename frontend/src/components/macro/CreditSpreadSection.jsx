import {
  ResponsiveContainer, AreaChart, Area,
  XAxis, YAxis, Tooltip, CartesianGrid,
} from 'recharts'
import LoadingSpinner from '../common/LoadingSpinner'
import ErrorAlert from '../common/ErrorAlert'

const fmt = (v) =>
  v != null
    ? v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : '-'

const DIRECTION_STYLE = {
  widening: { bg: 'bg-red-100', text: 'text-red-700', label: '확대 중' },
  narrowing: { bg: 'bg-emerald-100', text: 'text-emerald-700', label: '축소 중' },
  stable: { bg: 'bg-gray-100', text: 'text-gray-600', label: '안정' },
}

function StatCard({ title, value, suffix = '%', extra }) {
  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="text-sm font-medium text-gray-500 mb-1">{title}</div>
      <div className="text-2xl font-bold text-gray-900">
        {fmt(value)}{suffix}
      </div>
      {extra}
    </div>
  )
}

export default function CreditSpreadSection({ data, loading, error }) {
  if (loading) return <LoadingSpinner message="크레딧 스프레드 로딩 중..." />
  if (error) return <ErrorAlert message={error} />
  if (!data) return null

  const { hyg_yield, lqd_yield, spread, spread_direction, history } = data
  const dirStyle = DIRECTION_STYLE[spread_direction] || DIRECTION_STYLE.stable

  return (
    <section>
      <h2 className="text-lg font-semibold text-gray-900 mb-3">하이일드 스프레드</h2>

      {/* 상단 3카드 */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
        <StatCard title="HYG 수익률" value={hyg_yield} />
        <StatCard title="LQD 수익률" value={lqd_yield} />
        <StatCard
          title="스프레드"
          value={spread}
          extra={
            <span
              className={`inline-block mt-1 px-2 py-0.5 rounded text-xs font-medium ${dirStyle.bg} ${dirStyle.text}`}
            >
              {dirStyle.label}
            </span>
          }
        />
      </div>

      {/* HYG/LQD 비율 시계열 */}
      {history?.length > 0 && (
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <div className="text-sm font-medium text-gray-500 mb-2">HYG/LQD 비율 추이</div>
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
                  tickFormatter={(v) => v.toFixed(3)}
                />
                <Tooltip
                  formatter={(v) => [v.toFixed(4), 'HYG/LQD']}
                  labelFormatter={(l) => l}
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                />
                <defs>
                  <linearGradient id="creditGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f97316" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#f97316" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="ratio"
                  stroke="#f97316"
                  strokeWidth={1.5}
                  fill="url(#creditGrad)"
                  dot={false}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="text-xs text-gray-400 mt-1">
            비율 상승 = 스프레드 확대(위험 증가) / 비율 하락 = 스프레드 축소(안정)
          </div>
        </div>
      )}
    </section>
  )
}
