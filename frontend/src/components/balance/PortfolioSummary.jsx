function fmtKRW(val) {
  if (val === undefined || val === null || val === '') return '-'
  const n = Number(val)
  if (isNaN(n)) return String(val)
  return n.toLocaleString('ko-KR') + '원'
}

function SubItem({ label, value }) {
  return (
    <div className="flex justify-between items-center text-xs text-gray-500 mt-1">
      <span>{label}</span>
      <span className="font-medium">{fmtKRW(value)}</span>
    </div>
  )
}

function SummaryCard({ label, value, breakdown }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <p className="text-xs font-medium text-gray-500 mb-1">{label}</p>
      <p className="text-xl font-bold text-gray-900 mb-2">{value}</p>
      {breakdown && breakdown.length > 0 && (
        <div className="border-t border-gray-100 pt-2 space-y-0.5">
          {breakdown.map((item) => (
            <SubItem key={item.label} label={item.label} value={item.value} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function PortfolioSummary({ data }) {
  if (!data) return null

  const hasOverseasStockEval = Number(data.stock_eval_overseas_krw) !== 0
  const hasOverseasDeposit = Number(data.deposit_overseas_krw) !== 0

  return (
    <div className="grid grid-cols-3 gap-4">
      <SummaryCard label="총 평가금액" value={fmtKRW(data.total_evaluation)} />

      <SummaryCard
        label="주식 평가금액"
        value={fmtKRW(data.stock_eval)}
        breakdown={hasOverseasStockEval ? [
          { label: '국내주식', value: data.stock_eval_domestic },
          { label: '해외주식 (원화환산)', value: data.stock_eval_overseas_krw },
        ] : null}
      />

      <SummaryCard
        label="예수금"
        value={fmtKRW(data.deposit)}
        breakdown={hasOverseasDeposit ? [
          { label: '원화', value: data.deposit_domestic },
          { label: '외화 (원화환산)', value: data.deposit_overseas_krw },
        ] : null}
      />
    </div>
  )
}