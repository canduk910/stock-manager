import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold text-gray-700 mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {p.value != null ? p.value.toFixed(2) : '-'}
        </p>
      ))}
    </div>
  )
}

function StatCard({ label, value, sub }) {
  return (
    <div className="bg-gray-50 rounded-lg px-4 py-3 text-center">
      <p className="text-xs text-gray-400 mb-0.5">{label}</p>
      <p className="text-lg font-bold text-gray-800">{value ?? '-'}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  )
}

export default function ValuationChart({ data }) {
  if (!data) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400 text-sm">
        밸류에이션 데이터가 없습니다.
      </div>
    )
  }

  const { history = [], avg_per, avg_pbr } = data

  // X축 레이블: 연도 바뀔 때만 표시
  const tickFormatter = (val) => {
    const parts = val.split('-')
    return parts[1] === '01' ? parts[0] : ''
  }

  if (history.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400 text-sm">
        조회된 밸류에이션 히스토리가 없습니다.
      </div>
    )
  }

  // PER / PBR 데이터 분리 (각각 별도 차트)
  const perData = history.filter((h) => h.per != null)
  const pbrData = history.filter((h) => h.pbr != null)

  return (
    <div className="space-y-6">
      {/* 요약 카드 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="현재 PER" value={perData.at(-1)?.per?.toFixed(1)} sub="배" />
        <StatCard label={`${perData.length > 0 ? Math.floor(perData.length / 12) : ''}년 평균 PER`} value={avg_per} sub="배" />
        <StatCard label="현재 PBR" value={pbrData.at(-1)?.pbr?.toFixed(2)} sub="배" />
        <StatCard label={`${pbrData.length > 0 ? Math.floor(pbrData.length / 12) : ''}년 평균 PBR`} value={avg_pbr} sub="배" />
      </div>

      {/* PER 차트 */}
      {perData.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">PER 추이</h3>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={history} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="date"
                tickFormatter={tickFormatter}
                tick={{ fontSize: 11, fill: '#9ca3af' }}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={['auto', 'auto']}
                tick={{ fontSize: 11, fill: '#9ca3af' }}
                width={40}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {avg_per != null && (
                <ReferenceLine
                  y={avg_per}
                  stroke="#94a3b8"
                  strokeDasharray="4 3"
                  label={{ value: `평균 ${avg_per}`, position: 'right', fontSize: 10, fill: '#94a3b8' }}
                />
              )}
              <Line
                type="monotone"
                dataKey="per"
                name="PER"
                stroke="#3b82f6"
                strokeWidth={1.5}
                dot={false}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* PBR 차트 */}
      {pbrData.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">PBR 추이</h3>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={history} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="date"
                tickFormatter={tickFormatter}
                tick={{ fontSize: 11, fill: '#9ca3af' }}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={['auto', 'auto']}
                tick={{ fontSize: 11, fill: '#9ca3af' }}
                width={40}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {avg_pbr != null && (
                <ReferenceLine
                  y={avg_pbr}
                  stroke="#94a3b8"
                  strokeDasharray="4 3"
                  label={{ value: `평균 ${avg_pbr}`, position: 'right', fontSize: 10, fill: '#94a3b8' }}
                />
              )}
              <Line
                type="monotone"
                dataKey="pbr"
                name="PBR"
                stroke="#10b981"
                strokeWidth={1.5}
                dot={false}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
