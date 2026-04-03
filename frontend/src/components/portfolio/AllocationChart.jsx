import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'

function fmtKRW(val) {
  const n = Number(val)
  if (isNaN(n)) return '-'
  if (n >= 1e8) return `${(n / 1e8).toFixed(0)}억`
  if (n >= 1e4) return `${(n / 1e4).toFixed(0)}만`
  return n.toLocaleString() + '원'
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.[0]) return null
  const d = payload[0].payload
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow px-3 py-2 text-sm">
      <p className="font-medium text-gray-900">{d.name}</p>
      <p className="text-gray-600">{fmtKRW(d.value)} ({d.pct}%)</p>
    </div>
  )
}

export default function AllocationChart({ allocation }) {
  if (!allocation || allocation.length === 0) return null

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">자산 배분</h3>
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie
            data={allocation}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={100}
            dataKey="value"
            stroke="none"
            label={({ name, pct }) => `${name} ${pct}%`}
            labelLine={false}
          >
            {allocation.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>
      {/* 범례 */}
      <div className="flex justify-center gap-6 mt-2">
        {allocation.map((a, i) => (
          <div key={i} className="flex items-center gap-1.5 text-xs text-gray-600">
            <span className="w-3 h-3 rounded-full" style={{ backgroundColor: a.color }} />
            {a.name} {a.pct}%
          </div>
        ))}
      </div>
    </div>
  )
}
