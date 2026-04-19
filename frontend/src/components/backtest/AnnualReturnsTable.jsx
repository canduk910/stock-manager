import { useMemo } from 'react'
import { computeAnnualReturns } from './backtestUtils'

export default function AnnualReturnsTable({ equityCurve }) {
  const rows = useMemo(() => computeAnnualReturns(equityCurve), [equityCurve])

  if (!rows.length) return null

  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="text-sm font-medium text-gray-700 mb-3">연간 수익률</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left">연도</th>
              <th className="px-3 py-2 text-right">수익률</th>
              <th className="px-3 py-2 text-right">시작 자산</th>
              <th className="px-3 py-2 text-right">종료 자산</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.year} className="border-t">
                <td className="px-3 py-1.5 font-medium">{r.year}</td>
                <td className={`px-3 py-1.5 text-right font-semibold ${
                  r.return_pct >= 0 ? 'text-red-600' : 'text-blue-600'
                }`}>
                  {r.return_pct >= 0 ? '+' : ''}{r.return_pct.toFixed(2)}%
                </td>
                <td className="px-3 py-1.5 text-right text-gray-600">
                  {r.start_equity?.toLocaleString()}
                </td>
                <td className="px-3 py-1.5 text-right text-gray-600">
                  {r.end_equity?.toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
