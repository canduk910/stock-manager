function CagrCard({ label, value }) {
  if (value == null) return null
  const pos = value > 0
  const neg = value < 0
  const color = pos ? 'text-red-600' : neg ? 'text-blue-600' : 'text-gray-600'
  const sign = pos ? '+' : ''
  return (
    <div className="bg-gray-50 rounded-lg px-4 py-4 text-center">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className={`text-xl font-bold ${color}`}>
        {sign}{value.toFixed(1)}%
      </p>
      <p className="text-xs text-gray-400 mt-0.5">연평균 성장률(CAGR)</p>
    </div>
  )
}

function ValCard({ label, current, avg, vsAvg }) {
  const discounted = vsAvg != null && vsAvg < -10
  const expensive = vsAvg != null && vsAvg > 10
  const statusColor = discounted
    ? 'text-blue-600'
    : expensive
    ? 'text-red-600'
    : 'text-gray-600'
  const statusText = discounted ? '저평가' : expensive ? '고평가' : '적정'

  return (
    <div className="bg-gray-50 rounded-lg px-4 py-4">
      <p className="text-xs text-gray-400 mb-2">{label}</p>
      <div className="flex items-end gap-3">
        <span className="text-xl font-bold text-gray-800">
          {current != null ? `${current}배` : '-'}
        </span>
        {avg != null && (
          <span className="text-sm text-gray-400 mb-0.5">평균 {avg}배</span>
        )}
      </div>
      {vsAvg != null && (
        <p className={`text-sm font-semibold mt-1 ${statusColor}`}>
          {statusText} (평균 대비 {vsAvg > 0 ? '+' : ''}{vsAvg}%)
        </p>
      )}
    </div>
  )
}

export default function ReportSummary({ data }) {
  if (!data) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400 text-sm">
        리포트 데이터가 없습니다.
      </div>
    )
  }

  const { summary = {}, financials = {} } = data
  const {
    rev_cagr, op_cagr, net_cagr,
    current_per, current_pbr,
    avg_per, avg_pbr,
    per_vs_avg, pbr_vs_avg,
    year_start, year_end,
  } = summary

  const rows = financials.rows || []
  const hasCagr = rev_cagr != null || op_cagr != null || net_cagr != null

  return (
    <div className="space-y-6">
      {/* 성장성 */}
      {hasCagr && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            성장성 분석
            {year_start && year_end && (
              <span className="ml-2 text-xs font-normal text-gray-400">
                ({year_start}~{year_end}, {(year_end - year_start)}년간)
              </span>
            )}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <CagrCard label="매출액 CAGR" value={rev_cagr} />
            <CagrCard label="영업이익 CAGR" value={op_cagr} />
            <CagrCard label="순이익 CAGR" value={net_cagr} />
          </div>
        </div>
      )}

      {/* 밸류에이션 진단 */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">
          밸류에이션 진단
          {avg_per && (
            <span className="ml-2 text-xs font-normal text-gray-400">
              (과거 평균 대비)
            </span>
          )}
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <ValCard
            label="PER (주가수익비율)"
            current={current_per}
            avg={avg_per}
            vsAvg={per_vs_avg}
          />
          <ValCard
            label="PBR (주가순자산비율)"
            current={current_pbr}
            avg={avg_pbr}
            vsAvg={pbr_vs_avg}
          />
        </div>
      </div>

      {/* 최근 실적 요약 */}
      {rows.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            최근 실적 ({rows.at(-1)?.year}년)
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: '매출액', value: rows.at(-1)?.revenue, yoy: rows.at(-1)?.yoy_revenue },
              { label: '영업이익', value: rows.at(-1)?.operating_profit, yoy: rows.at(-1)?.yoy_op },
              { label: '영업이익률', value: rows.at(-1)?.oi_margin, unit: '%', noYoy: true },
              { label: '당기순이익', value: rows.at(-1)?.net_income },
            ].map(({ label, value, yoy, unit = '억', noYoy }) => (
              <div key={label} className="bg-gray-50 rounded-lg px-3 py-3">
                <p className="text-xs text-gray-400 mb-0.5">{label}</p>
                <p className="text-sm font-bold text-gray-800">
                  {value != null
                    ? unit === '%'
                      ? `${value.toFixed(1)}%`
                      : `${value.toLocaleString()}억`
                    : '-'}
                </p>
                {!noYoy && yoy != null && (
                  <p className={`text-xs ${yoy > 0 ? 'text-red-500' : yoy < 0 ? 'text-blue-500' : 'text-gray-400'}`}>
                    {yoy > 0 ? '+' : ''}{yoy.toFixed(1)}% YoY
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
