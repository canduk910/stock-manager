function fmtKRW(val) {
  if (val === undefined || val === null) return '-'
  const n = Number(val)
  if (isNaN(n)) return val
  return n.toLocaleString('ko-KR') + '원'
}

function SummaryCard({ label, value }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <p className="text-xs font-medium text-gray-500 mb-1">{label}</p>
      <p className="text-xl font-bold text-gray-900">{value}</p>
    </div>
  )
}

export default function PortfolioSummary({ data }) {
  if (!data) return null
  return (
    <div className="grid grid-cols-3 gap-4">
      <SummaryCard label="총 평가금액" value={fmtKRW(data.total_evaluation)} />
      <SummaryCard label="주식 평가금액" value={fmtKRW(data.stock_eval)} />
      <SummaryCard label="예수금" value={fmtKRW(data.deposit)} />
    </div>
  )
}
