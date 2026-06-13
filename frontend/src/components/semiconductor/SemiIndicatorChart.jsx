/**
 * Recharts 시계열 + 임계값 ReferenceLine.
 */

import {
  LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine,
  ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { useSemiconductorHistory } from '../../hooks/useSemiconductor'

export default function SemiIndicatorChart({ name, days = 180, threshold = null, label = '' }) {
  const { data, loading, error } = useSemiconductorHistory(name, days)

  if (loading) return <div className="text-gray-400 text-sm">로딩…</div>
  if (error) return <div className="text-red-500 text-sm">차트 로딩 실패</div>
  const points = (data?.points || [])
    .filter((p) => typeof p.value === 'number')
    .map((p) => ({ date: p.observed_at, value: p.value }))

  if (points.length === 0) {
    return <div className="text-xs text-gray-500">관측 데이터 없음</div>
  }

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer>
        <LineChart data={points} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="2 3" stroke="#e5e7eb" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={20} />
          <YAxis tick={{ fontSize: 11 }} width={48} />
          <Tooltip
            contentStyle={{ fontSize: '12px' }}
            labelStyle={{ fontSize: '11px' }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ r: 2 }}
            name={label || name}
          />
          {threshold !== null && (
            <ReferenceLine
              y={threshold}
              stroke="#ef4444"
              strokeDasharray="3 3"
              label={{ value: `임계 ${threshold}`, fontSize: 10, fill: '#ef4444' }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
