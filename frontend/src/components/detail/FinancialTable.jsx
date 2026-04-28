function fmtAwk(v) {
  if (v == null) return '-'
  if (Math.abs(v) >= 10000) return (v / 10000).toFixed(1) + '조'
  return v.toLocaleString()
}

// M USD 기준 → B/T 단위로 변환
function fmtUsdM(v) {
  if (v == null) return '-'
  const abs = Math.abs(v)
  if (abs >= 1000000) return '$' + (v / 1000000).toFixed(1) + 'T'
  if (abs >= 1000) return '$' + (v / 1000).toFixed(1) + 'B'
  return '$' + v.toLocaleString() + 'M'
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

function DataRow({ label, rows, field, yoyField, currency }) {
  return (
    <tr className="border-t border-gray-100">
      <td className="px-4 py-2.5 text-sm font-medium text-gray-700 whitespace-nowrap bg-gray-50 sticky left-0">
        {label}
      </td>
      {rows.map((r) => (
        <td key={r.year} className="px-4 py-2.5 text-right min-w-[80px]">
          <div className="text-sm font-medium text-gray-800">
            {currency === 'USD' ? fmtUsdM(r[field]) : fmtAwk(r[field])}
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

function MetricCard({ label, value, sub }) {
  return (
    <div className="bg-gray-50 rounded-lg px-4 py-3 flex flex-col gap-0.5">
      <span className="text-xs text-gray-500">{label}</span>
      <span className="text-sm font-semibold text-gray-800">{value ?? '-'}</span>
      {sub && <span className="text-xs text-gray-400">{sub}</span>}
    </div>
  )
}

const REC_MAP = {
  strong_buy: { label: '적극매수', cls: 'bg-red-100 text-red-700 border-red-300' },
  buy:        { label: '매수',     cls: 'bg-red-50  text-red-600 border-red-200' },
  hold:       { label: '중립',     cls: 'bg-gray-100 text-gray-600 border-gray-300' },
  sell:       { label: '매도',     cls: 'bg-blue-50 text-blue-600 border-blue-200' },
  strong_sell:{ label: '적극매도', cls: 'bg-blue-100 text-blue-700 border-blue-300' },
}

function ForwardSection({ forward, currency }) {
  if (!forward) return null
  const {
    eps_current_year, eps_forward, forward_pe,
    revenue_current, target_mean_price, target_high_price, target_low_price,
    num_analysts, recommendation, current_fiscal_year_end,
  } = forward

  // 의미있는 값이 하나도 없으면 섹션 숨김
  const hasAny = [eps_current_year, eps_forward, forward_pe, target_mean_price, revenue_current].some(v => v != null)
  if (!hasAny) return null

  const rec = REC_MAP[recommendation] || null
  const fyLabel = current_fiscal_year_end ? `FY${current_fiscal_year_end.slice(0, 4)}E` : '추정치'

  const fmtEps = (v) => {
    if (v == null) return null
    if (currency === 'USD') return `$${v.toFixed(2)}`
    return `${Math.round(v).toLocaleString()}원`
  }

  const fmtPrice = (v) => {
    if (v == null) return null
    if (currency === 'USD') return `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
    return `${Math.round(v).toLocaleString()}원`
  }

  const fmtRev = (v) => {
    if (v == null) return null
    if (currency === 'USD') {
      const m = v / 1_000_000
      if (m >= 1000) return `$${(m / 1000).toFixed(1)}B`
      return `$${m.toFixed(0)}M`
    }
    const awk = v / 1_0000_0000
    if (awk >= 10000) return `${(awk / 10000).toFixed(1)}조`
    return `${Math.round(awk).toLocaleString()}억`
  }

  return (
    <div className="border border-indigo-100 rounded-xl bg-indigo-50/40 overflow-hidden">
      <div className="px-4 py-2.5 border-b border-indigo-100 flex items-center justify-between">
        <span className="text-sm font-semibold text-indigo-700">
          📊 애널리스트 컨센서스 ({fyLabel})
        </span>
        {num_analysts != null && (
          <span className="text-xs text-indigo-400">{num_analysts}명 추정</span>
        )}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-0 divide-x divide-indigo-100">
        {forward_pe != null && (
          <div className="px-4 py-3">
            <div className="text-xs text-gray-500 mb-0.5">포워드 PER</div>
            <div className="text-sm font-semibold text-gray-800">{forward_pe.toFixed(1)}x</div>
          </div>
        )}
        {eps_current_year != null && (
          <div className="px-4 py-3">
            <div className="text-xs text-gray-500 mb-0.5">추정 EPS ({fyLabel})</div>
            <div className="text-sm font-semibold text-gray-800">{fmtEps(eps_current_year)}</div>
            {eps_forward != null && (
              <div className="text-xs text-gray-400 mt-0.5">차기: {fmtEps(eps_forward)}</div>
            )}
          </div>
        )}
        {revenue_current != null && (
          <div className="px-4 py-3">
            <div className="text-xs text-gray-500 mb-0.5">매출 추정</div>
            <div className="text-sm font-semibold text-gray-800">{fmtRev(revenue_current)}</div>
          </div>
        )}
        {target_mean_price != null && (
          <div className="px-4 py-3">
            <div className="text-xs text-gray-500 mb-0.5">목표주가 (평균)</div>
            <div className="text-sm font-semibold text-gray-800">{fmtPrice(target_mean_price)}</div>
            {(target_high_price != null || target_low_price != null) && (
              <div className="text-xs text-gray-400 mt-0.5">
                {fmtPrice(target_low_price)} ~ {fmtPrice(target_high_price)}
              </div>
            )}
          </div>
        )}
        {rec && (
          <div className="px-4 py-3">
            <div className="text-xs text-gray-500 mb-1">투자의견</div>
            <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-bold border ${rec.cls}`}>
              {rec.label}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

export default function FinancialTable({ data, basic, forward }) {
  const currency = data?.currency || 'KRW'
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

  const roe = basic?.roe
  const divYield = basic?.dividend_yield
  const dps = basic?.dividend_per_share
  const showMetrics = roe != null || divYield != null || dps != null

  return (
    <div className="space-y-3">
      {/* 포워드 가이던스 / 애널리스트 컨센서스 */}
      <ForwardSection forward={forward} currency={currency} />

      {/* 현재 주요 지표 카드 */}
      {showMetrics && (
        <div className="grid grid-cols-3 gap-3">
          <MetricCard
            label="ROE (자기자본이익률)"
            value={roe != null ? `${roe.toFixed(1)}%` : null}
          />
          <MetricCard
            label="배당수익률"
            value={divYield != null ? `${divYield.toFixed(2)}%` : null}
          />
          <MetricCard
            label="주당배당금 (DPS)"
            value={dps != null
              ? (currency === 'USD' ? `$${dps.toFixed(2)}` : `${dps.toLocaleString()}원`)
              : null}
            sub={currency === 'USD' ? '연간 (USD)' : '연간 (KRW)'}
          />
        </div>
      )}

    <div className="bg-white rounded-xl border border-gray-200">
      <div className="px-5 py-3 border-b border-gray-100">
        <h2 className="text-sm font-semibold text-gray-700">
          연간 재무 요약
          {currency === 'USD'
            ? <span className="ml-2 text-xs font-normal text-gray-400">단위: M USD (1,000M 이상은 B/T · yfinance 기준)</span>
            : <span className="ml-2 text-xs font-normal text-gray-400">단위: 억원 (1조 이상은 조원)</span>
          }
        </h2>
      </div>
      <div className="overflow-x-auto">
        {(() => {
          // 추정 열 데이터 준비
          const fwRevCur  = forward?.revenue_current
          const fwNetCur  = forward?.net_income_estimate
          const fwRevFwd  = forward?.revenue_forward
          const fwNetFwd  = forward?.net_income_forward
          const fyEnd     = forward?.current_fiscal_year_end  // "2025-12"
          const fyYear    = fyEnd ? parseInt(fyEnd.slice(0, 4)) : null
          const hasCurEst = fwRevCur != null || fwNetCur != null
          const hasFwdEst = fwRevFwd != null || fwNetFwd != null

          // 억원 / M USD 변환 헬퍼
          const fmtEst = (v) => {
            if (v == null) return <span className="text-gray-300">-</span>
            return currency === 'USD' ? fmtUsdM(v / 1e6) : fmtAwk(v / 1e8)
          }

          const estThCls = "px-4 py-2.5 text-right text-xs min-w-[80px] bg-indigo-50 border-l border-dashed border-indigo-200"
          const estTdCls = "px-4 py-2.5 text-right bg-indigo-50/40 border-l border-dashed border-indigo-200"

          return (
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
                  {hasCurEst && fyYear && (
                    <th className={estThCls}>
                      <span className="font-semibold text-indigo-600">{fyYear}E</span>
                      <span className="ml-1 text-[10px] bg-indigo-100 text-indigo-500 px-1 rounded">추정</span>
                    </th>
                  )}
                  {hasFwdEst && fyYear && (
                    <th className={estThCls}>
                      <span className="font-semibold text-indigo-400">{fyYear + 1}E</span>
                      <span className="ml-1 text-[10px] bg-indigo-100 text-indigo-400 px-1 rounded">추정</span>
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {/* 매출액 */}
                <tr className="border-t border-gray-100">
                  <td className="px-4 py-2.5 text-sm font-medium text-gray-700 whitespace-nowrap bg-gray-50 sticky left-0">매출액</td>
                  {rows.map((r) => (
                    <td key={r.year} className="px-4 py-2.5 text-right min-w-[80px]">
                      <div className="text-sm font-medium text-gray-800">
                        {currency === 'USD' ? fmtUsdM(r.revenue) : fmtAwk(r.revenue)}
                      </div>
                      {r.yoy_revenue != null && (
                        <div className={`text-xs ${growthColor(r.yoy_revenue)}`}>{fmtPct(r.yoy_revenue)}</div>
                      )}
                    </td>
                  ))}
                  {hasCurEst && fyYear && <td className={estTdCls}><div className="text-sm font-medium text-indigo-700 italic">{fmtEst(fwRevCur)}</div></td>}
                  {hasFwdEst && fyYear && <td className={estTdCls}><div className="text-sm font-medium text-indigo-400 italic">{fmtEst(fwRevFwd)}</div></td>}
                </tr>

                {/* 영업이익 */}
                <tr className="border-t border-gray-100">
                  <td className="px-4 py-2.5 text-sm font-medium text-gray-700 whitespace-nowrap bg-gray-50 sticky left-0">영업이익</td>
                  {rows.map((r) => (
                    <td key={r.year} className="px-4 py-2.5 text-right min-w-[80px]">
                      <div className="text-sm font-medium text-gray-800">
                        {currency === 'USD' ? fmtUsdM(r.operating_profit) : fmtAwk(r.operating_profit)}
                      </div>
                      {r.yoy_op != null && (
                        <div className={`text-xs ${growthColor(r.yoy_op)}`}>{fmtPct(r.yoy_op)}</div>
                      )}
                    </td>
                  ))}
                  {hasCurEst && fyYear && <td className={estTdCls}><span className="text-gray-300 text-sm">-</span></td>}
                  {hasFwdEst && fyYear && <td className={estTdCls}><span className="text-gray-300 text-sm">-</span></td>}
                </tr>

                {/* 영업이익률 */}
                <tr className="border-t border-gray-100">
                  <td className="px-4 py-2.5 text-sm font-medium text-gray-700 bg-gray-50 sticky left-0">영업이익률</td>
                  {rows.map((r) => (
                    <td key={r.year} className="px-4 py-2.5 text-right text-sm">
                      {r.oi_margin != null ? (
                        <span className={r.oi_margin > 0 ? 'text-red-600' : 'text-blue-600'}>
                          {r.oi_margin.toFixed(1)}%
                        </span>
                      ) : '-'}
                    </td>
                  ))}
                  {hasCurEst && fyYear && <td className={estTdCls}><span className="text-gray-300 text-sm">-</span></td>}
                  {hasFwdEst && fyYear && <td className={estTdCls}><span className="text-gray-300 text-sm">-</span></td>}
                </tr>

                {/* 당기순이익 */}
                <tr className="border-t border-gray-100">
                  <td className="px-4 py-2.5 text-sm font-medium text-gray-700 whitespace-nowrap bg-gray-50 sticky left-0">당기순이익</td>
                  {rows.map((r) => (
                    <td key={r.year} className="px-4 py-2.5 text-right min-w-[80px]">
                      <div className="text-sm font-medium text-gray-800">
                        {currency === 'USD' ? fmtUsdM(r.net_income) : fmtAwk(r.net_income)}
                      </div>
                    </td>
                  ))}
                  {hasCurEst && fyYear && <td className={estTdCls}><div className="text-sm font-medium text-indigo-700 italic">{fmtEst(fwNetCur)}</div></td>}
                  {hasFwdEst && fyYear && <td className={estTdCls}><div className="text-sm font-medium text-indigo-400 italic">{fmtEst(fwNetFwd)}</div></td>}
                </tr>
              </tbody>
            </table>
          )
        })()}
      </div>
      <p className="px-5 py-2 text-xs text-gray-400 border-t border-gray-100">
        {currency === 'USD'
          ? '* YoY는 전년도 대비 증감률입니다. E열은 애널리스트 컨센서스 추정치입니다.'
          : '* 연도 클릭 시 DART 사업보고서로 이동합니다. E열은 애널리스트 컨센서스 추정치입니다.'
        }
      </p>
    </div>
    </div>
  )
}
