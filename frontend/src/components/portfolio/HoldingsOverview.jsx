import { useNavigate } from 'react-router-dom'

const GRADE_STYLES = {
  'A':  { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-400' },
  'B+': { bg: 'bg-emerald-50', text: 'text-emerald-600', border: 'border-emerald-300' },
  'B':  { bg: 'bg-gray-100', text: 'text-gray-600', border: 'border-gray-300' },
  'C':  { bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-400' },
  'D':  { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-400' },
}

function GradeBadge({ grade }) {
  if (!grade) return <span className="text-xs text-gray-300">-</span>
  const s = GRADE_STYLES[grade] || GRADE_STYLES['B']
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold border ${s.bg} ${s.text} ${s.border}`}>
      {grade}
    </span>
  )
}

function fmtAmt(val, currency) {
  const n = Number(val)
  if (isNaN(n)) return '-'
  if (currency === 'KRW') {
    if (n >= 1e8) return `${(n / 1e8).toFixed(1)}억`
    return n.toLocaleString() + '원'
  }
  return '$' + n.toLocaleString()
}

export default function HoldingsOverview({ holdings }) {
  const navigate = useNavigate()

  if (!holdings || holdings.length === 0) return null

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-700">보유 종목 현황</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-gray-500 text-xs">
              <th className="px-4 py-2 text-left font-medium">종목</th>
              <th className="px-3 py-2 text-right font-medium">비중</th>
              <th className="px-3 py-2 text-right font-medium">평가금액</th>
              <th className="px-3 py-2 text-right font-medium">수익률</th>
              <th className="px-3 py-2 text-right font-medium">PER</th>
              <th className="px-3 py-2 text-right font-medium">PBR</th>
              <th className="px-3 py-2 text-right font-medium">ROE</th>
              <th className="px-3 py-2 text-center font-medium">안전마진</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {holdings.map((h, i) => {
              const profitColor = h.profitRate >= 0 ? 'text-red-600' : 'text-blue-600'
              return (
                <tr
                  key={`${h.code}-${h.market}`}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => navigate(`/detail/${h.code}`)}
                >
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <div>
                        <div className="font-medium text-gray-900">{h.name}</div>
                        <div className="text-xs text-gray-400">{h.code} · {h.market}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-2.5 text-right text-gray-700">{h.weight}%</td>
                  <td className="px-3 py-2.5 text-right text-gray-700">{fmtAmt(h.evalKrw, 'KRW')}</td>
                  <td className={`px-3 py-2.5 text-right font-medium ${profitColor}`}>
                    {h.profitRate >= 0 ? '+' : ''}{h.profitRate}%
                  </td>
                  <td className="px-3 py-2.5 text-right text-gray-600">
                    {h.per != null ? Math.floor(h.per) : '-'}
                  </td>
                  <td className="px-3 py-2.5 text-right text-gray-600">
                    {h.pbr != null ? h.pbr.toFixed(1) : '-'}
                  </td>
                  <td className="px-3 py-2.5 text-right text-gray-600">
                    {h.roe != null ? h.roe.toFixed(1) + '%' : '-'}
                  </td>
                  <td className="px-3 py-2.5 text-center">
                    <GradeBadge grade={h.grade} />
                    {h.discountRate != null && (
                      <div className="text-xs text-gray-400 mt-0.5">
                        {h.discountRate >= 0 ? '+' : ''}{h.discountRate}%
                      </div>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
