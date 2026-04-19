/**
 * 백테스트 결과 메트릭 카드 (4칸).
 * 수익률 / 샤프 비율 / 최대 낙폭 / 승률 + 간단 설명
 */
export default function MetricsCard({ metrics }) {
  if (!metrics) return null

  const items = [
    {
      label: '총 수익률',
      desc: '투자 원금 대비 최종 손익 비율',
      value: metrics.total_return_pct,
      fmt: (v) => `${v >= 0 ? '+' : ''}${v?.toFixed(1)}%`,
      color: (v) => v >= 0 ? 'text-red-600' : 'text-blue-600',
    },
    {
      label: '샤프 비율',
      desc: '위험 대비 수익. 1 이상 양호, 2 이상 우수',
      value: metrics.sharpe_ratio,
      fmt: (v) => v?.toFixed(2),
      color: (v) => v >= 1.5 ? 'text-green-600' : v >= 1.0 ? 'text-yellow-600' : 'text-gray-600',
    },
    {
      label: '최대 낙폭',
      desc: '고점 대비 최대 하락폭. 작을수록 안정적',
      value: metrics.max_drawdown,
      fmt: (v) => `${v?.toFixed(1)}%`,
      color: (v) => v > -10 ? 'text-green-600' : v > -20 ? 'text-yellow-600' : 'text-red-600',
    },
    {
      label: '승률',
      desc: '수익을 낸 거래 비율. 50% 이상 양호',
      value: metrics.win_rate,
      fmt: (v) => `${v?.toFixed(1)}%`,
      color: (v) => v >= 55 ? 'text-green-600' : v >= 45 ? 'text-yellow-600' : 'text-red-600',
    },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {items.map(({ label, desc, value, fmt, color }) => (
        <div key={label} className="bg-white rounded-lg border p-4 text-center">
          <div className="text-xs text-gray-500 mb-1">{label}</div>
          <div className={`text-xl font-bold ${value != null ? color(value) : 'text-gray-400'}`}>
            {value != null ? fmt(value) : 'N/A'}
          </div>
          <div className="text-[10px] text-gray-400 mt-1">{desc}</div>
        </div>
      ))}
    </div>
  )
}
