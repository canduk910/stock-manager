function fmtAwk(v) {
  if (v == null) return '-'
  if (Math.abs(v) >= 10000) return (v / 10000).toFixed(1) + '조'
  return v.toLocaleString()
}

function fmtPct(v, digits = 1) {
  if (v == null) return null
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(digits)}%`
}

function growthColor(v) {
  if (v == null) return 'text-gray-300'
  return v > 0 ? 'text-red-500' : v < 0 ? 'text-blue-500' : 'text-gray-400'
}

function YearHeader({ year, dartUrl }) {
  if (dartUrl) {
    return (
      <a
        href={dartUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="text-blue-600 hover:text-blue-800 hover:underline font-semibold"
        title="DART 사업보고서 열기"
      >
        {year}
      </a>
    )
  }
  return <span className="font-semibold text-gray-700">{year}</span>
}

function DataRow({ label, rows, field, yoyField }) {
  return (
    <tr className="border-t border-gray-100">
      <td className="px-4 py-2.5 text-sm font-medium text-gray-700 whitespace-nowrap bg-gray-50 sticky left-0">
        {label}
      </td>
      {rows.map((r) => (
        <td key={r.year} className="px-4 py-2.5 text-right min-w-[80px]">
          <div className="text-sm font-medium text-gray-800">
            {fmtAwk(r[field])}
          </div>
          {yoyField && r[yoyField] != null && (
            <div className={`text-xs ${growthColor(r[yoyField])}`}>
              {fmtPct(r[yoyField])}
            </div>
          )}
        </td>
      ))}
    </tr>
  )
}

export default function FinancialTable({ data }) {
  if (!data) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400 text-sm">
        재무 데이터가 없습니다.
      </div>
    )
  }

  const rows = data.rows || []

  if (rows.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400 text-sm">
        조회된 재무 데이터가 없습니다.
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200">
      <div className="px-5 py-3 border-b border-gray-100">
        <h2 className="text-sm font-semibold text-gray-700">
          연간 재무 요약
          <span className="ml-2 text-xs font-normal text-gray-400">단위: 억원 (1조 이상은 조원)</span>
        </h2>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 whitespace-nowrap sticky left-0 bg-gray-50">
                항목
              </th>
              {rows.map((r) => (
                <th key={r.year} className="px-4 py-2.5 text-right text-xs text-gray-500 min-w-[80px]">
                  <YearHeader year={r.year} dartUrl={r.dart_url} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <DataRow label="매출액" rows={rows} field="revenue" yoyField="yoy_revenue" />
            <DataRow label="영업이익" rows={rows} field="operating_profit" yoyField="yoy_op" />
            <tr className="border-t border-gray-100">
              <td className="px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-50 sticky left-0">
                영업이익률
              </td>
              {rows.map((r) => (
                <td key={r.year} className="px-4 py-2.5 text-right text-sm">
                  {r.oi_margin != null ? (
                    <span className={r.oi_margin > 0 ? 'text-red-600' : 'text-blue-600'}>
                      {r.oi_margin.toFixed(1)}%
                    </span>
                  ) : '-'}
                </td>
              ))}
            </tr>
            <DataRow label="당기순이익" rows={rows} field="net_income" />
          </tbody>
        </table>
      </div>
      <p className="px-5 py-2 text-xs text-gray-400 border-t border-gray-100">
        * 연도 클릭 시 DART 사업보고서로 이동합니다. YoY는 전년도 대비 증감률입니다.
      </p>
    </div>
  )
}
