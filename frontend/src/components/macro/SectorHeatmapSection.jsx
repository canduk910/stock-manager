import { useMemo } from 'react'
import LoadingSpinner from '../common/LoadingSpinner'
import ErrorAlert from '../common/ErrorAlert'

const fmt = (v) =>
  v != null
    ? v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : '-'

function heatmapStyle(val) {
  if (val == null) return { backgroundColor: '#f9fafb' } // gray-50
  const intensity = Math.min(Math.abs(val) / 30, 1)
  const alpha = 0.1 + intensity * 0.5
  if (val > 0) return { backgroundColor: `rgba(34,197,94,${alpha})` }
  return { backgroundColor: `rgba(239,68,68,${alpha})` }
}

function ReturnCell({ value }) {
  if (value == null) return <td className="px-3 py-2 text-center text-gray-400 text-sm">-</td>
  const sign = value > 0 ? '+' : ''
  const textColor = value > 0 ? 'text-red-600' : value < 0 ? 'text-blue-600' : 'text-gray-600'
  return (
    <td className="px-3 py-2 text-center text-sm font-medium" style={heatmapStyle(value)}>
      <span className={textColor}>{sign}{fmt(value)}%</span>
    </td>
  )
}

export default function SectorHeatmapSection({ data, loading, error }) {
  if (loading) return <LoadingSpinner message="섹터 히트맵 로딩 중..." />
  if (error) return <ErrorAlert message={error} />
  if (!data?.sectors?.length) return null

  // 3M 수익률 내림차순 정렬
  const sorted = useMemo(() => {
    return [...data.sectors].sort((a, b) => (b.return_3m ?? -999) - (a.return_3m ?? -999))
  }, [data.sectors])

  return (
    <section>
      <h2 className="text-lg font-semibold text-gray-900 mb-3">섹터 히트맵</h2>
      <div className="rounded-lg border bg-white shadow-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50">
              <th className="px-3 py-2 text-left font-medium text-gray-600">섹터</th>
              <th className="px-3 py-2 text-center font-medium text-gray-600">1M</th>
              <th className="px-3 py-2 text-center font-medium text-gray-600">3M</th>
              <th className="px-3 py-2 text-center font-medium text-gray-600">6M</th>
              <th className="px-3 py-2 text-center font-medium text-gray-600">1Y</th>
              <th className="px-3 py-2 text-center font-medium text-gray-600">3Y</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((s) => (
              <tr key={s.symbol} className="border-b last:border-b-0 hover:bg-gray-50/50">
                <td className="px-3 py-2 font-medium text-gray-900 whitespace-nowrap">
                  {s.name_ko || s.name}
                </td>
                <ReturnCell value={s.return_1m} />
                <ReturnCell value={s.return_3m} />
                <ReturnCell value={s.return_6m} />
                <ReturnCell value={s.return_1y} />
                <ReturnCell value={s.return_3y} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
