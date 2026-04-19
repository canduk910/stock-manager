import { useMemo } from 'react'
import { computeMonthlyReturns } from './backtestUtils'

const MONTHS = ['1월','2월','3월','4월','5월','6월','7월','8월','9월','10월','11월','12월']

function cellColor(pct) {
  if (pct == null) return 'bg-gray-50 text-gray-300'
  if (pct > 5)  return 'bg-red-600 text-white'
  if (pct > 2)  return 'bg-red-400 text-white'
  if (pct > 0)  return 'bg-red-100 text-red-800'
  if (pct > -2) return 'bg-blue-100 text-blue-800'
  if (pct > -5) return 'bg-blue-400 text-white'
  return 'bg-blue-600 text-white'
}

export default function MonthlyReturnsHeatmap({ equityCurve }) {
  const { data, years } = useMemo(() => computeMonthlyReturns(equityCurve), [equityCurve])

  if (!data.length || years.length === 0) return null

  // year-month lookup
  const lookup = useMemo(() => {
    const m = new Map()
    for (const d of data) m.set(`${d.year}-${d.month}`, d.return_pct)
    return m
  }, [data])

  // 연간 합계
  const yearTotal = useMemo(() => {
    const t = new Map()
    for (const d of data) {
      t.set(d.year, (t.get(d.year) || 0) + d.return_pct)
    }
    return t
  }, [data])

  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="text-sm font-medium text-gray-700 mb-3">월별 수익률</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-[11px] border-collapse">
          <thead>
            <tr>
              <th className="px-2 py-1.5 text-left text-gray-500 font-medium">연도</th>
              {MONTHS.map((m) => (
                <th key={m} className="px-1 py-1.5 text-center text-gray-500 font-medium w-[60px]">{m}</th>
              ))}
              <th className="px-2 py-1.5 text-center text-gray-500 font-medium">합계</th>
            </tr>
          </thead>
          <tbody>
            {years.map((year) => {
              const total = yearTotal.get(year) || 0
              return (
                <tr key={year}>
                  <td className="px-2 py-1 font-medium text-gray-700">{year}</td>
                  {Array.from({ length: 12 }, (_, i) => {
                    const pct = lookup.get(`${year}-${i + 1}`)
                    return (
                      <td key={i} className={`px-1 py-1 text-center rounded-sm ${cellColor(pct)}`}>
                        {pct != null ? `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}` : '-'}
                      </td>
                    )
                  })}
                  <td className={`px-2 py-1 text-center font-semibold ${
                    total >= 0 ? 'text-red-600' : 'text-blue-600'
                  }`}>
                    {total >= 0 ? '+' : ''}{total.toFixed(1)}%
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {/* 범례 */}
      <div className="flex gap-2 mt-2 text-[10px] text-gray-500 justify-end items-center">
        <span>손실</span>
        <span className="inline-block w-4 h-3 bg-blue-600 rounded-sm" />
        <span className="inline-block w-4 h-3 bg-blue-400 rounded-sm" />
        <span className="inline-block w-4 h-3 bg-blue-100 rounded-sm" />
        <span className="inline-block w-4 h-3 bg-gray-50 rounded-sm border" />
        <span className="inline-block w-4 h-3 bg-red-100 rounded-sm" />
        <span className="inline-block w-4 h-3 bg-red-400 rounded-sm" />
        <span className="inline-block w-4 h-3 bg-red-600 rounded-sm" />
        <span>수익</span>
      </div>
    </div>
  )
}
