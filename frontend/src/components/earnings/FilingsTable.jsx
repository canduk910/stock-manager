import { useState, useEffect } from 'react'
import { fetchWatchlist } from '../../api/watchlist'
import DataTable from '../common/DataTable'
import WatchlistButton from '../common/WatchlistButton'

function fmtDate(s) {
  if (!s || s.length !== 8) return s || '-'
  return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`
}

function fmtAmt(v) {
  if (v === null || v === undefined) return null
  const oku = Math.round(v / 100_000_000)
  if (Math.abs(oku) >= 10000) return `${(oku / 10000).toFixed(1)}조`
  return `${oku.toLocaleString()}억`
}

function yoy(cur, prev) {
  if (cur == null || prev == null || prev === 0) return null
  return Math.round((cur - prev) / Math.abs(prev) * 10) / 10
}

function FinCell({ value, prevValue }) {
  const formatted = fmtAmt(value)
  if (!formatted) return <span className="text-gray-400 text-xs">-</span>
  const change = yoy(value, prevValue)
  return (
    <div className="text-right leading-tight">
      <div className="text-xs font-medium text-gray-800">{formatted}</div>
      {change !== null && (
        <div className={`text-xs ${change > 0 ? 'text-red-500' : change < 0 ? 'text-blue-500' : 'text-gray-500'}`}>
          {change > 0 ? '▲' : change < 0 ? '▼' : '─'}{Math.abs(change).toFixed(1)}%
        </div>
      )}
    </div>
  )
}

function ReturnCell({ value }) {
  if (value === null || value === undefined)
    return <span className="text-gray-400 text-xs">-</span>
  const cls = value > 0 ? 'text-red-600' : value < 0 ? 'text-blue-600' : 'text-gray-600'
  return (
    <span className={`text-xs font-medium ${cls}`}>
      {value > 0 ? '+' : ''}{value.toFixed(1)}%
    </span>
  )
}

const REPORT_TYPE_COLORS_KR = {
  '사업보고서': 'bg-purple-100 text-purple-700',
  '반기보고서': 'bg-blue-100 text-blue-700',
  '분기보고서': 'bg-teal-100 text-teal-700',
}

const REPORT_TYPE_COLORS_US = {
  '10-K': 'bg-purple-100 text-purple-700',
  '10-Q': 'bg-teal-100 text-teal-700',
}

function makeColumns(market, watchlistSet) {
  const isUS = market === 'US'
  return [
    {
      key: '_watchlist',
      label: '',
      align: 'center',
      sortable: false,
      render: (_, row) => (
        <WatchlistButton
          code={row.stock_code}
          market={market}
          alreadyAdded={watchlistSet.has(`${row.stock_code}:${market}`)}
        />
      ),
    },
    { key: 'stock_code', label: isUS ? '티커' : '종목코드', align: 'center' },
    { key: 'corp_name', label: '종목명', align: 'left' },
    { key: 'change_pct', label: '당일',   align: 'right', render: (v) => <ReturnCell value={v} /> },
    { key: 'return_3m',  label: '3개월', align: 'right', render: (v) => <ReturnCell value={v} /> },
    { key: 'return_6m',  label: '6개월', align: 'right', render: (v) => <ReturnCell value={v} /> },
    { key: 'return_1y',  label: '1년',   align: 'right', render: (v) => <ReturnCell value={v} /> },
    ...(!isUS ? [
      { key: 'revenue',          label: '매출액',  align: 'right', render: (v, row) => <FinCell value={v} prevValue={row.revenue_prev} /> },
      { key: 'operating_income', label: '영업이익', align: 'right', render: (v, row) => <FinCell value={v} prevValue={row.operating_income_prev} /> },
    ] : []),
    {
      key: isUS ? 'report_code' : 'report_type',
      label: '보고서 종류',
      align: 'center',
      render: (v) => {
        const colors = isUS ? REPORT_TYPE_COLORS_US : REPORT_TYPE_COLORS_KR
        const cls = colors[v] || 'bg-gray-100 text-gray-700'
        return <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${cls}`}>{v}</span>
      },
    },
    {
      key: 'report_name',
      label: '보고서명',
      align: 'left',
      render: (v, row) => {
        const url = row.link || row.dart_url
        return url ? (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-800 hover:underline"
          >
            {v}
          </a>
        ) : (
          v
        )
      },
    },
    { key: 'rcept_dt', label: '제출일', align: 'center', render: fmtDate },
    ...(!isUS ? [{ key: 'flr_nm', label: '제출인', align: 'left' }] : []),
  ]
}

export default function FilingsTable({ filings, market = 'KR' }) {
  const [watchlistSet, setWatchlistSet] = useState(new Set())

  useEffect(() => {
    fetchWatchlist()
      .then(data => {
        const s = new Set((data.items || []).map(item => `${item.code}:${item.market}`))
        setWatchlistSet(s)
      })
      .catch(() => {})
  }, [])

  const columns = makeColumns(market, watchlistSet)
  // US는 rcept_no가 없을 수 있으므로 인덱스 기반 key 사용 (DataTable은 rowKey 미전달 시 index 사용)
  const rowKey = market === 'US' ? undefined : 'stock_code'
  return <DataTable columns={columns} data={filings} rowKey={rowKey} />
}
