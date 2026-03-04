/**
 * 기본적 분석 탭
 * 계량지표 카드 + 손익계산서 + 대차대조표 + 현금흐름표 + 사업별 매출비중
 */
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts'

const PIE_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

// ── 포맷 헬퍼 ──────────────────────────────────────────────────────────────
function fmtMoney(v, market) {
  if (v == null) return '-'
  if (market === 'KR') {
    const awk = v / 1e8
    if (Math.abs(awk) >= 10000) return (awk / 10000).toFixed(1) + '조'
    return Math.round(awk).toLocaleString() + '억'
  }
  // US: raw USD
  const m = v / 1e6
  if (Math.abs(m) >= 1000) return '$' + (m / 1000).toFixed(1) + 'B'
  return '$' + Math.round(m).toLocaleString() + 'M'
}

function fmtPct(v) {
  if (v == null) return '-'
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(1)}%`
}

function pctColor(v) {
  if (v == null) return 'text-gray-500'
  return v > 0 ? 'text-red-500' : v < 0 ? 'text-blue-500' : 'text-gray-500'
}

// ── 계량지표 카드 ─────────────────────────────────────────────────────────
function MetricCard({ label, value }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-3 text-center">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-base font-bold text-gray-800">
        {value == null ? '-' : typeof value === 'number' ? value.toFixed(1) : value}
      </div>
    </div>
  )
}

// ── 섹션 헤더 ─────────────────────────────────────────────────────────────
function SectionTitle({ children }) {
  return (
    <h3 className="text-sm font-semibold text-gray-700 mt-6 mb-2 border-b border-gray-200 pb-1">
      {children}
    </h3>
  )
}

// ── 테이블 셀 ─────────────────────────────────────────────────────────────
function Td({ children, right = false, bold = false }) {
  return (
    <td className={`px-3 py-2 text-xs whitespace-nowrap ${right ? 'text-right' : ''} ${bold ? 'font-semibold' : ''}`}>
      {children ?? '-'}
    </td>
  )
}

function Th({ children, right = false }) {
  return (
    <th className={`px-3 py-2 text-xs font-semibold text-gray-600 bg-gray-50 whitespace-nowrap ${right ? 'text-right' : 'text-left'}`}>
      {children}
    </th>
  )
}

// ── 손익계산서 테이블 ─────────────────────────────────────────────────────
function IncomeTable({ rows, market }) {
  if (!rows?.length) return <p className="text-xs text-gray-400 py-2">데이터 없음</p>
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-gray-700">
        <thead>
          <tr>
            <Th>항목</Th>
            {rows.map(r => <Th key={r.year} right>{r.year}</Th>)}
          </tr>
        </thead>
        <tbody>
          {[
            { label: '매출', field: 'revenue' },
            { label: '매출원가', field: 'cogs' },
            { label: '매출총이익', field: 'gross_profit' },
            { label: '영업이익', field: 'operating_income' },
            { label: '순이익', field: 'net_income' },
          ].map(({ label, field }) => (
            <tr key={field} className="border-t border-gray-100">
              <td className="px-3 py-2 text-xs font-medium text-gray-600 bg-gray-50 sticky left-0">{label}</td>
              {rows.map(r => (
                <Td key={r.year} right>{fmtMoney(r[field], market)}</Td>
              ))}
            </tr>
          ))}
          <tr className="border-t border-gray-200">
            <td className="px-3 py-2 text-xs font-medium text-gray-600 bg-gray-50 sticky left-0">영업이익률</td>
            {rows.map(r => (
              <td key={r.year} className={`px-3 py-2 text-xs text-right ${pctColor(r.oi_margin)}`}>
                {fmtPct(r.oi_margin)}
              </td>
            ))}
          </tr>
          <tr className="border-t border-gray-100">
            <td className="px-3 py-2 text-xs font-medium text-gray-600 bg-gray-50 sticky left-0">순이익률</td>
            {rows.map(r => (
              <td key={r.year} className={`px-3 py-2 text-xs text-right ${pctColor(r.net_margin)}`}>
                {fmtPct(r.net_margin)}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  )
}

// ── 매출/영업이익 막대차트 ────────────────────────────────────────────────
function IncomeChart({ rows, market }) {
  if (!rows?.length) return null
  const unit = market === 'KR' ? '억원' : 'M USD'
  const divisor = market === 'KR' ? 1e8 : 1e6
  const data = rows.map(r => ({
    year: String(r.year),
    매출: r.revenue != null ? Math.round(r.revenue / divisor) : null,
    영업이익: r.operating_income != null ? Math.round(r.operating_income / divisor) : null,
    순이익: r.net_income != null ? Math.round(r.net_income / divisor) : null,
  }))
  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <XAxis dataKey="year" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 10 }} tickFormatter={v => v.toLocaleString()} unit="" />
        <Tooltip formatter={(v) => v != null ? v.toLocaleString() + unit : '-'} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Bar dataKey="매출" fill="#3b82f6" radius={[2, 2, 0, 0]} />
        <Bar dataKey="영업이익" fill="#10b981" radius={[2, 2, 0, 0]} />
        <Bar dataKey="순이익" fill="#f59e0b" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── 대차대조표 테이블 ─────────────────────────────────────────────────────
function BalanceSheetTable({ rows, market }) {
  if (!rows?.length) return <p className="text-xs text-gray-400 py-2">데이터 없음</p>
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-gray-700">
        <thead>
          <tr>
            <Th>항목</Th>
            {rows.map(r => <Th key={r.year} right>{r.year}</Th>)}
          </tr>
        </thead>
        <tbody>
          {[
            { label: '자산총계', field: 'total_assets', bold: true },
            { label: '유동자산', field: 'current_assets' },
            { label: '비유동자산', field: 'non_current_assets' },
            { label: '부채총계', field: 'total_liabilities', bold: true },
            { label: '유동부채', field: 'current_liabilities' },
            { label: '비유동부채', field: 'non_current_liabilities' },
            { label: '자본총계', field: 'total_equity', bold: true },
            { label: '이익잉여금', field: 'retained_earnings' },
          ].map(({ label, field, bold }) => (
            <tr key={field} className="border-t border-gray-100">
              <td className={`px-3 py-2 text-xs bg-gray-50 sticky left-0 ${bold ? 'font-semibold text-gray-700' : 'font-medium text-gray-600'}`}>{label}</td>
              {rows.map(r => <Td key={r.year} right bold={bold}>{fmtMoney(r[field], market)}</Td>)}
            </tr>
          ))}
          <tr className="border-t border-gray-200">
            <td className="px-3 py-2 text-xs font-medium text-gray-600 bg-gray-50">부채비율</td>
            {rows.map(r => (
              <td key={r.year} className={`px-3 py-2 text-xs text-right ${pctColor(r.debt_ratio != null ? r.debt_ratio - 100 : null)}`}>
                {r.debt_ratio != null ? r.debt_ratio.toFixed(1) + '%' : '-'}
              </td>
            ))}
          </tr>
          <tr className="border-t border-gray-100">
            <td className="px-3 py-2 text-xs font-medium text-gray-600 bg-gray-50">유동비율</td>
            {rows.map(r => (
              <td key={r.year} className={`px-3 py-2 text-xs text-right ${pctColor(r.current_ratio != null ? r.current_ratio - 100 : null)}`}>
                {r.current_ratio != null ? r.current_ratio.toFixed(1) + '%' : '-'}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  )
}

// ── 현금흐름표 테이블 ─────────────────────────────────────────────────────
function CashflowTable({ rows, market }) {
  if (!rows?.length) return <p className="text-xs text-gray-400 py-2">데이터 없음</p>
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-gray-700">
        <thead>
          <tr>
            <Th>항목</Th>
            {rows.map(r => <Th key={r.year} right>{r.year}</Th>)}
          </tr>
        </thead>
        <tbody>
          {[
            { label: '영업활동CF', field: 'operating_cf', bold: true },
            { label: '투자활동CF', field: 'investing_cf' },
            { label: '재무활동CF', field: 'financing_cf' },
            { label: 'CAPEX', field: 'capex' },
            { label: '잉여현금흐름(FCF)', field: 'free_cf', bold: true },
          ].map(({ label, field, bold }) => (
            <tr key={field} className="border-t border-gray-100">
              <td className={`px-3 py-2 text-xs bg-gray-50 sticky left-0 ${bold ? 'font-semibold text-gray-700' : 'font-medium text-gray-600'}`}>{label}</td>
              {rows.map(r => (
                <td key={r.year} className={`px-3 py-2 text-xs text-right ${r[field] != null && r[field] < 0 ? 'text-blue-500' : ''} ${bold ? 'font-semibold' : ''}`}>
                  {fmtMoney(r[field], market)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── 현금흐름 차트 ─────────────────────────────────────────────────────────
function CashflowChart({ rows, market }) {
  if (!rows?.length) return null
  const divisor = market === 'KR' ? 1e8 : 1e6
  const unit = market === 'KR' ? '억원' : 'M USD'
  const data = rows.map(r => ({
    year: String(r.year),
    영업CF: r.operating_cf != null ? Math.round(r.operating_cf / divisor) : null,
    FCF: r.free_cf != null ? Math.round(r.free_cf / divisor) : null,
  }))
  return (
    <ResponsiveContainer width="100%" height={150}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <XAxis dataKey="year" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 10 }} tickFormatter={v => v.toLocaleString()} />
        <Tooltip formatter={v => v != null ? v.toLocaleString() + unit : '-'} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Bar dataKey="영업CF" fill="#3b82f6" radius={[2, 2, 0, 0]} />
        <Bar dataKey="FCF" fill="#10b981" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── 사업별 매출비중 파이차트 ──────────────────────────────────────────────
function SegmentsChart({ segments }) {
  if (!segments?.length) return <p className="text-xs text-gray-400 py-2">데이터 없음</p>
  const isAiEstimate = segments.some(s => s.note === 'AI추정')
  return (
    <div>
      {isAiEstimate && (
        <span className="inline-block text-xs bg-yellow-100 text-yellow-700 border border-yellow-300 rounded px-2 py-0.5 mb-2">
          AI 추정 (참고용)
        </span>
      )}
      <div className="flex items-center gap-4">
        <ResponsiveContainer width={160} height={160}>
          <PieChart>
            <Pie
              data={segments}
              dataKey="revenue_pct"
              nameKey="segment"
              cx="50%"
              cy="50%"
              outerRadius={70}
              label={({ revenue_pct }) => `${revenue_pct.toFixed(0)}%`}
              labelLine={false}
            >
              {segments.map((_, i) => (
                <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(v) => v.toFixed(1) + '%'} />
          </PieChart>
        </ResponsiveContainer>
        <ul className="text-xs space-y-1.5">
          {segments.map((s, i) => (
            <li key={i} className="flex items-center gap-2">
              <span className="inline-block w-3 h-3 rounded-sm" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
              <span className="text-gray-700">{s.segment}</span>
              <span className="text-gray-500">{s.revenue_pct.toFixed(1)}%</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

// ── 메인 컴포넌트 ─────────────────────────────────────────────────────────
export default function FundamentalPanel({ data, market }) {
  const fundamental = data?.fundamental || {}
  const metrics = fundamental.metrics || {}
  const incomeStmt = fundamental.income_stmt || []
  const balanceSheet = fundamental.balance_sheet || []
  const cashflow = fundamental.cashflow || []
  const segments = fundamental.segments || []

  return (
    <div className="space-y-2">
      {/* 계량지표 */}
      <SectionTitle>계량지표</SectionTitle>
      <div className="grid grid-cols-4 gap-2 sm:grid-cols-4 lg:grid-cols-8">
        <MetricCard label="PER" value={metrics.per} />
        <MetricCard label="PBR" value={metrics.pbr} />
        <MetricCard label="PSR" value={metrics.psr} />
        <MetricCard label="EV/EBITDA" value={metrics.ev_ebitda} />
        <MetricCard label="ROE (%)" value={metrics.roe} />
        <MetricCard label="ROA (%)" value={metrics.roa} />
        <MetricCard label="부채/자본" value={metrics.debt_to_equity} />
        <MetricCard label="유동비율" value={metrics.current_ratio} />
      </div>

      {/* 손익계산서 */}
      <SectionTitle>손익계산서</SectionTitle>
      <IncomeTable rows={incomeStmt} market={market} />
      <IncomeChart rows={incomeStmt} market={market} />

      {/* 대차대조표 */}
      <SectionTitle>대차대조표</SectionTitle>
      <BalanceSheetTable rows={balanceSheet} market={market} />

      {/* 현금흐름표 */}
      <SectionTitle>현금흐름표</SectionTitle>
      <CashflowTable rows={cashflow} market={market} />
      <CashflowChart rows={cashflow} market={market} />

      {/* 사업별 매출비중 */}
      <SectionTitle>사업별 매출비중</SectionTitle>
      <SegmentsChart segments={segments} />
    </div>
  )
}
