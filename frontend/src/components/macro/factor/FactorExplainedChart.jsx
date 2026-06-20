/**
 * 주성분 설명력(EVR) 추이 — 멀티라인 LineChart (pc0~pc4).
 *
 * 롤링 윈도우별 각 주성분이 설명하는 분산 비율의 시간 변화.
 * 축 의미 회전 감지(설명력 급변)에 유용.
 */
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts'

const PC_COLORS = ['#7c3aed', '#2563eb', '#059669', '#d97706', '#dc2626']

export default function FactorExplainedChart({ explainedHistory, pcLabels }) {
  const data = explainedHistory || []
  if (data.length === 0) {
    return (
      <div className="text-sm text-gray-500 text-center py-6">
        설명력 추이 데이터 없음
      </div>
    )
  }

  // pcN 키 자동 탐색 (pc0..pc4)
  const pcKeys = Object.keys(data[0] || {}).filter((k) => /^pc\d+$/.test(k))
  const labelOf = (key) => {
    const idx = Number(key.replace('pc', ''))
    return (pcLabels && pcLabels[idx]) || `PC${idx}`
  }

  // 날짜 라벨 — 분기 단위로 솎아서 가독성 (MM-DD → YY-MM)
  const fmtDate = (d) => (typeof d === 'string' ? d.slice(2, 7) : d)

  return (
    <div className="w-full h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="date"
            tickFormatter={fmtDate}
            tick={{ fontSize: 10, fill: '#9ca3af' }}
            minTickGap={32}
          />
          <YAxis
            tickFormatter={(v) => `${Math.round(v * 100)}%`}
            tick={{ fontSize: 10, fill: '#9ca3af' }}
            domain={[0, 'auto']}
          />
          <Tooltip
            formatter={(v, n) => [`${(v * 100).toFixed(1)}%`, labelOf(n)]}
            labelFormatter={(d) => d}
          />
          <Legend formatter={(v) => labelOf(v)} wrapperStyle={{ fontSize: 11 }} />
          {pcKeys.map((k, i) => (
            <Line
              key={k}
              type="monotone"
              dataKey={k}
              stroke={PC_COLORS[i % PC_COLORS.length]}
              dot={false}
              strokeWidth={1.6}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
