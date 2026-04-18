const fmt = (v) => (v ?? 0).toLocaleString('ko-KR')

function Card({ label, value, sub, color }) {
  const textColor = color === 'red' ? 'text-red-600' : color === 'blue' ? 'text-blue-600' : 'text-gray-900'
  return (
    <div className="bg-white rounded-lg border p-4 flex flex-col">
      <span className="text-xs text-gray-500 mb-1">{label}</span>
      <span className={`text-xl font-bold ${textColor}`}>{fmt(value)}원</span>
      {sub && <span className="text-xs text-gray-400 mt-1">{sub}</span>}
    </div>
  )
}

export default function TaxSummaryCards({ summary }) {
  if (!summary) return null

  const netColor = summary.net_gain >= 0 ? 'red' : 'blue'
  const sellCount = summary.transaction_count?.sell || 0

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <Card
        label="순 양도차익 (손익통산)"
        value={summary.net_gain}
        sub={`이익 ${fmt(summary.total_gain)} / 손실 ${fmt(summary.total_loss)} · 매도 ${sellCount}건`}
        color={netColor}
      />
      <Card
        label="기본공제"
        value={summary.basic_deduction}
        sub="연 250만원"
      />
      <Card
        label="과세표준"
        value={summary.taxable_amount}
        sub="순이익 - 기본공제 (0 이상)"
      />
      <Card
        label="예상 세액"
        value={summary.estimated_tax}
        sub={`세율 ${(summary.tax_rate * 100).toFixed(0)}%`}
        color={summary.estimated_tax > 0 ? 'red' : undefined}
      />
    </div>
  )
}
