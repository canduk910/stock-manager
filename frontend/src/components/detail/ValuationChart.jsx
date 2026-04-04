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

function fmtLargeNum(val) {
  if (val == null) return '-'
  if (val >= 1e16) return (val / 1e16).toFixed(1) + '경'
  if (val >= 1e12) return (val / 1e12).toFixed(1) + 'T'
  if (val >= 1e8) return (val / 1e8).toFixed(0) + '억'
  if (val >= 1e9) return (val / 1e9).toFixed(1) + 'B'
  if (val >= 1e6) return (val / 1e6).toFixed(1) + 'M'
  return val.toLocaleString()
}

function fmtShares(val) {
  if (val == null) return '-'
  if (val >= 1e8) return (val / 1e8).toFixed(2) + '억주'
  if (val >= 1e4) return (val / 1e4).toFixed(0) + '만주'
  return val.toLocaleString() + '주'
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold text-gray-700 mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {p.value != null
            ? p.dataKey === 'mktcap' ? fmtLargeNum(p.value)
            : p.dataKey === 'shares' ? fmtShares(p.value)
            : p.value.toFixed(2)
            : '-'}
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

export default function ValuationChart({ data, compact = false }) {
  if (!data) {
    return (
      <div className={compact ? "text-center text-gray-400 text-sm py-4" : "bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400 text-sm"}>
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
      <div className={compact ? "text-center text-gray-400 text-sm py-4" : "bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400 text-sm"}>
        조회된 밸류에이션 히스토리가 없습니다.
      </div>
    )
  }

  // 데이터 분리 (각각 별도 차트)
  const perData = history.filter((h) => h.per != null)
  const pbrData = history.filter((h) => h.pbr != null)
  const mktcapData = history.filter((h) => h.mktcap != null)
  const sharesData = history.filter((h) => h.shares != null)

  const chartWrap = compact ? '' : 'bg-white rounded-xl border border-gray-200 p-5'
  const chartHeight = compact ? 200 : 260

  return (
    <div className={compact ? "space-y-4" : "space-y-6"}>
      {/* 요약 카드 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="현재 PER" value={perData.at(-1)?.per?.toFixed(1)} sub="배" />
        <StatCard label={`${perData.length > 0 ? Math.floor(perData.length / 12) : ''}년 평균 PER`} value={avg_per} sub="배" />
        <StatCard label="현재 PBR" value={pbrData.at(-1)?.pbr?.toFixed(2)} sub="배" />
        <StatCard label={`${pbrData.length > 0 ? Math.floor(pbrData.length / 12) : ''}년 평균 PBR`} value={avg_pbr} sub="배" />
      </div>

      {/* PER 차트 */}
      {perData.length > 0 && (
        <div className={chartWrap}>
          <h3 className="text-sm font-semibold text-gray-700 mb-4">PER 추이</h3>
          <ResponsiveContainer width="100%" height={chartHeight}>
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
        <div className={chartWrap}>
          <h3 className="text-sm font-semibold text-gray-700 mb-4">PBR 추이</h3>
          <ResponsiveContainer width="100%" height={chartHeight}>
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

      {/* 시가총액 차트 */}
      {mktcapData.length > 0 && (
        <div className={chartWrap}>
          <h3 className="text-sm font-semibold text-gray-700 mb-4">시가총액 추이</h3>
          <ResponsiveContainer width="100%" height={chartHeight}>
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
                width={55}
                tickFormatter={fmtLargeNum}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line
                type="monotone"
                dataKey="mktcap"
                name="시가총액"
                stroke="#8b5cf6"
                strokeWidth={1.5}
                dot={false}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* 발행주식수 차트 */}
      {sharesData.length > 0 && (
        <div className={chartWrap}>
          <h3 className="text-sm font-semibold text-gray-700 mb-4">발행주식수 추이</h3>
          <ResponsiveContainer width="100%" height={chartHeight}>
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
                width={55}
                tickFormatter={fmtShares}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line
                type="monotone"
                dataKey="shares"
                name="발행주식수"
                stroke="#f59e0b"
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
