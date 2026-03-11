import { useState } from 'react'
import { addToWatchlist } from '../../api/watchlist'
import DataTable from '../common/DataTable'

function WatchlistButton({ code }) {
  const [status, setStatus] = useState('idle') // idle | loading | done | error

  const handleAdd = async () => {
    if (status === 'loading' || status === 'done' || !code) return
    setStatus('loading')
    try {
      await addToWatchlist(code, '', 'KR')
      setStatus('done')
    } catch {
      setStatus('error')
      setTimeout(() => setStatus('idle'), 2000)
    }
  }

  if (status === 'done')
    return <span className="text-green-600 text-xs font-medium">✓ 추가됨</span>
  if (status === 'loading')
    return <span className="text-gray-400 text-xs">추가 중...</span>

  return (
    <button
      onClick={handleAdd}
      className={`text-xs px-2 py-0.5 rounded border transition-colors ${
        status === 'error'
          ? 'border-red-300 text-red-500'
          : 'border-gray-300 text-gray-500 hover:border-blue-500 hover:text-blue-600 hover:bg-blue-50'
      }`}
    >
      {status === 'error' ? '실패' : '+ 관심'}
    </button>
  )
}

/** 시가총액 억/조 포맷팅 */
function fmtMktcap(val) {
  if (!val || val === 0) return '-'
  const eok = val / 1_0000_0000
  if (eok >= 10000) return `${(eok / 10000).toLocaleString('ko-KR', { maximumFractionDigits: 1 })}조`
  return `${Math.round(eok).toLocaleString('ko-KR')}억`
}

function fmtFloat(val) {
  if (val === null || val === undefined) return '-'
  return val.toLocaleString('ko-KR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function fmtPrice(val) {
  if (val === null || val === undefined) return '-'
  return Math.floor(val).toLocaleString('ko-KR')
}

/** 등락률/수익률 컬러 셀 (한국 관례: 상승=빨강, 하락=파랑) */
function fmtPct(val) {
  if (val === null || val === undefined) return <span className="text-gray-400">-</span>
  const color = val > 0 ? 'text-red-600' : val < 0 ? 'text-blue-600' : 'text-gray-600'
  const sign = val > 0 ? '+' : ''
  return (
    <span className={color}>
      {sign}{val.toLocaleString('ko-KR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%
    </span>
  )
}

function fmtDivYield(val) {
  if (val === null || val === undefined) return '-'
  return `${val.toLocaleString('ko-KR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`
}

const COLUMNS = [
  { key: '_watchlist', label: '', align: 'center', sortable: false,
    render: (_, row) => <WatchlistButton code={row.code} /> },
  { key: '_rank', label: '순위', align: 'right' },
  { key: 'code', label: '종목코드', align: 'center' },
  { key: 'name', label: '종목명', align: 'left' },
  { key: 'market', label: '시장', align: 'center',
    render: (v) => (
      <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${v === 'KOSPI' ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'}`}>
        {v}
      </span>
    )
  },
  { key: 'prev_close', label: '전일종가', align: 'right', render: fmtPrice },
  { key: 'current_price', label: '현재가', align: 'right', render: fmtPrice },
  { key: 'change_pct', label: '당일(%)', align: 'right', render: fmtPct },
  { key: 'return_3m', label: '3개월(%)', align: 'right', render: fmtPct },
  { key: 'return_6m', label: '6개월(%)', align: 'right', render: fmtPct },
  { key: 'return_1y', label: '1년(%)', align: 'right', render: fmtPct },
  { key: 'dividend_yield', label: '배당수익률', align: 'right', render: fmtDivYield },
  { key: 'per', label: 'PER', align: 'right', render: fmtFloat },
  { key: 'pbr', label: 'PBR', align: 'right', render: fmtFloat },
  { key: 'roe', label: 'ROE(%)', align: 'right', render: fmtFloat },
  { key: 'mktcap', label: '시가총액', align: 'right', render: fmtMktcap },
]

export default function StockTable({ stocks }) {
  if (!stocks || stocks.length === 0) return null

  const enriched = stocks.map((s, i) => ({ ...s, _rank: i + 1 }))

  return <DataTable columns={COLUMNS} data={enriched} rowKey="code" />
}
