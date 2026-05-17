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

  // 전체 보유 종목 표시 (이전: slice(0,15)로 손실 종목이 잘리던 결함)
  // 수익률 내림차순 정렬 — 위쪽 이익 / 아래쪽 손실로 시각적 구분
  const data = [...holdings]
    .sort((a, b) => b.profitRate - a.profitRate)
    .map(h => ({
      name: h.name || '',
      fullName: h.name,
      profitRate: h.profitRate,
    }))

  // Y축 너비 동적 — 가장 긴 종목명에 맞춰 자동 (한글 1자 ≈ 11px, 최소 80 / 최대 200)
  const maxNameLen = data.reduce((m, d) => Math.max(m, (d.name || '').length), 0)
  const yAxisWidth = Math.min(200, Math.max(80, maxNameLen * 11 + 12))

  // 종목 수에 따른 동적 height — 종목당 26px + 여백 (최소 260px)
  const chartHeight = Math.max(260, data.length * 26 + 20)

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">
        종목별 수익률 <span className="text-xs text-gray-400 ml-1">({data.length}종목)</span>
      </h3>
      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart data={data} layout="vertical" margin={{ left: 0, right: 20, top: 0, bottom: 0 }}>
          <XAxis type="number" tickFormatter={v => `${v}%`} fontSize={11} />
          <YAxis type="category" dataKey="name" width={yAxisWidth} fontSize={11} interval={0} />
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
