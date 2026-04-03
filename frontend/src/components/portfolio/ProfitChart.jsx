import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.[0]) return null
  const d = payload[0].payload
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow px-3 py-2 text-sm">
      <p className="font-medium text-gray-900">{d.name}</p>
      <p className={d.profitRate >= 0 ? 'text-red-600' : 'text-blue-600'}>
        {d.profitRate >= 0 ? '+' : ''}{d.profitRate}%
      </p>
    </div>
  )
}

export default function ProfitChart({ holdings }) {
  if (!holdings || holdings.length === 0) return null

  const data = [...holdings]
    .sort((a, b) => b.profitRate - a.profitRate)
    .slice(0, 15)
    .map(h => ({
      name: h.name?.length > 6 ? h.name.slice(0, 6) + '..' : h.name,
      fullName: h.name,
      profitRate: h.profitRate,
    }))

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">종목별 수익률</h3>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} layout="vertical" margin={{ left: 0, right: 20, top: 0, bottom: 0 }}>
          <XAxis type="number" tickFormatter={v => `${v}%`} fontSize={11} />
          <YAxis type="category" dataKey="name" width={70} fontSize={11} />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="profitRate" radius={[0, 4, 4, 0]} barSize={16}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.profitRate >= 0 ? '#ef4444' : '#3b82f6'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
