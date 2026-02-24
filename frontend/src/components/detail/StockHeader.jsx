function fmtPrice(v) {
  return v != null ? v.toLocaleString() + '원' : '-'
}

function ChangeCell({ change, changePct }) {
  if (changePct == null) return <span className="text-gray-400">-</span>
  const up = changePct > 0
  const down = changePct < 0
  const color = up ? 'text-red-600' : down ? 'text-blue-600' : 'text-gray-600'
  const sign = up ? '+' : ''
  const arrow = up ? '▲' : down ? '▼' : ''
  return (
    <span className={`font-semibold ${color}`}>
      {arrow} {sign}{change?.toLocaleString()}원 ({sign}{changePct?.toFixed(2)}%)
    </span>
  )
}

function ValBadge({ label, value, avg, vsAvg }) {
  if (value == null) return null
  const isLow = vsAvg != null && vsAvg < -10
  const isHigh = vsAvg != null && vsAvg > 10
  const badgeColor = isLow
    ? 'bg-blue-50 border-blue-200 text-blue-700'
    : isHigh
    ? 'bg-red-50 border-red-200 text-red-700'
    : 'bg-gray-50 border-gray-200 text-gray-700'

  return (
    <div className={`px-3 py-2 rounded-lg border text-center ${badgeColor}`}>
      <p className="text-xs text-gray-400 mb-0.5">{label}</p>
      <p className="text-sm font-bold">{value}배</p>
      {avg != null && (
        <p className="text-xs mt-0.5">
          평균 {avg}배
          {vsAvg != null && (
            <span className={vsAvg < 0 ? 'text-blue-600 ml-1' : 'text-red-600 ml-1'}>
              ({vsAvg > 0 ? '+' : ''}{vsAvg}%)
            </span>
          )}
        </p>
      )}
    </div>
  )
}

export default function StockHeader({ symbol, name, basic, summary }) {
  const avgPer = summary?.avg_per
  const avgPbr = summary?.avg_pbr
  const perVsAvg = summary?.per_vs_avg
  const pbrVsAvg = summary?.pbr_vs_avg

  return (
    <div className="bg-white rounded-xl border border-gray-200 px-6 py-5">
      <div className="flex flex-wrap items-start gap-6">
        {/* 종목 기본 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap">
            <h1 className="text-2xl font-bold text-gray-900 truncate">
              {name || symbol}
            </h1>
            <span className="text-sm text-gray-400 font-mono">{symbol}</span>
          </div>
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            <span className="text-2xl font-bold text-gray-900">
              {fmtPrice(basic?.price)}
            </span>
            <ChangeCell change={basic?.change} changePct={basic?.change_pct} />
          </div>
          <div className="flex gap-2 mt-2 flex-wrap text-xs text-gray-500">
            {basic?.market && <span className="bg-gray-100 px-2 py-0.5 rounded">{basic.market}</span>}
            {basic?.sector && <span className="bg-gray-100 px-2 py-0.5 rounded">{basic.sector}</span>}
            {basic?.market_cap != null && (
              <span className="text-gray-400">시총 {basic.market_cap.toLocaleString()}억</span>
            )}
          </div>
        </div>

        {/* 밸류에이션 배지 */}
        <div className="flex gap-3 flex-wrap">
          <ValBadge
            label="PER"
            value={basic?.per}
            avg={avgPer}
            vsAvg={perVsAvg}
          />
          <ValBadge
            label="PBR"
            value={basic?.pbr}
            avg={avgPbr}
            vsAvg={pbrVsAvg}
          />
        </div>
      </div>
    </div>
  )
}
