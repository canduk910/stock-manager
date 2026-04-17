/**
 * 백테스트 결과 메트릭 카드 (4칸).
 * 수익률 / 샤프 비율 / 최대 낙폭 / 승률
 */
export default function MetricsCard({ metrics }) {
  if (!metrics) return null

  const items = [
    {
      label: '총 수익률',
      value: metrics.total_return_pct,
      fmt: (v) => `${v >= 0 ? '+' : ''}${v?.toFixed(1)}%`,
      color: (v) => v >= 0 ? 'text-red-600' : 'text-blue-600',
    },
    {
      label: '샤프 비율',
      value: metrics.sharpe_ratio,
      fmt: (v) => v?.toFixed(2),
      color: (v) => v >= 1.5 ? 'text-green-600' : v >= 1.0 ? 'text-yellow-600' : 'text-gray-600',
    },
    {
      label: '최대 낙폭',
      value: metrics.max_drawdown,
      fmt: (v) => `${v?.toFixed(1)}%`,
      color: (v) => v > -10 ? 'text-green-600' : v > -20 ? 'text-yellow-600' : 'text-red-600',
    },
    {
      label: '승률',
      value: metrics.win_rate,
      fmt: (v) => `${v?.toFixed(1)}%`,
      color: (v) => v >= 55 ? 'text-green-600' : v >= 45 ? 'text-yellow-600' : 'text-red-600',
    },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {items.map(({ label, value, fmt, color }) => (
        <div key={label} className="bg-white rounded-lg border p-4 text-center">
          <div className="text-xs text-gray-500 mb-1">{label}</div>
          <div className={`text-xl font-bold ${value != null ? color(value) : 'text-gray-400'}`}>
            {value != null ? fmt(value) : 'N/A'}
          </div>
        </div>
      ))}
    </div>
  )
}
