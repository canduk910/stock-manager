import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const fmt = (v) => (v ?? 0).toLocaleString('ko-KR')

export default function TaxBySymbolChart({ bySymbol }) {
  if (!bySymbol || bySymbol.length === 0) return null

  const data = bySymbol.map((s) => ({
    name: s.symbol,
    fullName: s.symbol_name || s.symbol,
    value: s.gain_loss,
    sellCount: s.sell_count,
  }))

  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">종목별 양도차익</h3>
      <ResponsiveContainer width="100%" height={Math.max(200, data.length * 40)}>
        <BarChart data={data} layout="vertical" margin={{ left: 60, right: 20, top: 5, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" tickFormatter={(v) => `${(v / 10000).toFixed(0)}만`} />
          <YAxis type="category" dataKey="name" width={50} tick={{ fontSize: 12 }} />
          <Tooltip
            formatter={(v) => [`${fmt(v)}원`, '양도차익']}
            labelFormatter={(label, payload) => {
              const item = payload?.[0]?.payload
              return item?.fullName || label
            }}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.value >= 0 ? '#ef4444' : '#3b82f6'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
