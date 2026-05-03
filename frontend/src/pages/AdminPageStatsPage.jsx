/**
 * /admin/page-stats — 페이지별 이용현황 통계 (admin only).
 *
 * Phase 4 단계 5. 호출수 + 평균/최대 latency + 유저수 + 일별 시계열 차트.
 */
import { useEffect, useState, useMemo } from 'react'
import { fetchPageStats } from '../api/admin'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorAlert from '../components/common/ErrorAlert'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

function dateOffset(days) {
  const d = new Date(Date.now() + 9 * 3600_000)
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

const RANGES = [
  { key: 7, label: '7일' },
  { key: 30, label: '30일' },
  { key: 90, label: '90일' },
]

export default function AdminPageStatsPage() {
  const [range, setRange] = useState(7)
  const [top, setTop] = useState(10)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchPageStats({
      from: dateOffset(-range),
      to: dateOffset(0),
      top,
    })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [range, top])

  // timeseries → recharts 형식 (date 별 row, path 별 컬럼)
  const chartData = useMemo(() => {
    if (!data?.timeseries) return []
    const byDate = {}
    for (const row of data.timeseries) {
      if (!byDate[row.date]) byDate[row.date] = { date: row.date }
      byDate[row.date][row.path] = row.calls
    }
    return Object.values(byDate).sort((a, b) => a.date.localeCompare(b.date))
  }, [data])

  const paths = useMemo(() => {
    if (!data?.summary) return []
    return data.summary.slice(0, 5).map(s => s.path)
  }, [data])

  const colors = ['#2563eb', '#dc2626', '#16a34a', '#9333ea', '#ea580c']

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">페이지별 이용현황</h1>

      <div className="flex items-center gap-3">
        <div className="flex gap-1">
          {RANGES.map(r => (
            <button
              key={r.key}
              onClick={() => setRange(r.key)}
              className={`px-3 py-1.5 text-sm rounded ${range === r.key ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >{r.label}</button>
          ))}
        </div>
        <label className="text-sm text-gray-500">
          상위
          <input
            type="number" value={top} onChange={(e) => setTop(parseInt(e.target.value) || 10)}
            className="w-16 mx-2 border rounded px-2 py-1 text-sm"
            min={1} max={100}
          /> path
        </label>
      </div>

      {error && <ErrorAlert message={error} />}
      {loading ? <LoadingSpinner /> : (
        <>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">상위 5개 path 일별 호출수</h3>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                {paths.map((p, i) => (
                  <Line key={p} type="monotone" dataKey={p} stroke={colors[i % colors.length]} strokeWidth={2} dot={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-2.5 text-left">Path</th>
                  <th className="px-4 py-2.5 text-right">호출수</th>
                  <th className="px-4 py-2.5 text-right">평균 (ms)</th>
                  <th className="px-4 py-2.5 text-right">최대 (ms)</th>
                  <th className="px-4 py-2.5 text-right">유저 수</th>
                </tr>
              </thead>
              <tbody>
                {(data?.summary || []).map(row => (
                  <tr key={row.path} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="px-4 py-2.5 font-mono text-xs">{row.path}</td>
                    <td className="px-4 py-2.5 text-right font-mono">{row.calls}</td>
                    <td className="px-4 py-2.5 text-right font-mono">{row.avg_ms}</td>
                    <td className="px-4 py-2.5 text-right font-mono">{row.max_ms}</td>
                    <td className="px-4 py-2.5 text-right font-mono">{row.unique_users}</td>
                  </tr>
                ))}
                {(!data?.summary || data.summary.length === 0) && (
                  <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">데이터 없음</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
