import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { fetchWatchlist } from '../../api/watchlist'
import DataTable from '../common/DataTable'
import WatchlistButton from '../common/WatchlistButton'

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

function GuruScoreBadge({ scores }) {
  if (!scores) return <span className="text-gray-300">-</span>
  const { normalized_score, formulas_available } = scores
  const color = normalized_score >= 75 ? 'bg-green-100 text-green-700'
    : normalized_score >= 50 ? 'bg-yellow-100 text-yellow-700'
    : 'bg-red-100 text-red-700'
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-bold ${color}`}>
      {Math.round(normalized_score)} ({formulas_available}/{scores.max_possible / 4})
    </span>
  )
}

function FormulaScore({ score, maxScore = 4 }) {
  if (score == null) return <span className="text-gray-300">N/A</span>
  return (
    <div className="flex gap-0.5 justify-center">
      {Array(maxScore).fill(0).map((_, i) => (
        <span key={i} className={`w-2 h-2 rounded-full ${i < score ? 'bg-blue-500' : 'bg-gray-200'}`} />
      ))}
    </div>
  )
}

function ValueTrapIcon({ warnings }) {
  if (!warnings || warnings.length === 0) return null
  return (
    <span className="relative group cursor-pointer" title={warnings.join('\n')}>
      <span className="text-amber-500 text-base">!</span>
      <div className="absolute z-50 hidden group-hover:block bg-gray-900 text-white text-xs rounded-lg p-2 w-48 -left-20 top-6 shadow-lg">
        {warnings.map((w, i) => <p key={i} className="mb-1 last:mb-0">{w}</p>)}
      </div>
    </span>
  )
}

function makeColumns(watchlistSet, hasGuru) {
  const cols = [
    { key: '_watchlist', label: '', align: 'center', sortable: false,
      render: (_, row) => <WatchlistButton code={row.code} alreadyAdded={watchlistSet.has(row.code)} /> },
    { key: '_rank', label: '#', align: 'right' },
    { key: 'name', label: '종목명', align: 'left',
      render: (v, row) => (
        <Link to={`/detail/${row.code}`} className="hover:text-blue-600">
          <span>{v}</span>
          <span className="text-gray-400 text-xs ml-1">{row.code}</span>
        </Link>
      )},
    { key: 'current_price', label: '현재가', align: 'right', render: fmtPrice },
    { key: 'change_pct', label: '당일', align: 'right', render: fmtPct },
    { key: 'return_1y', label: '1Y', align: 'right', render: fmtPct },
    { key: 'per', label: 'PER', align: 'right', render: fmtFloat },
    { key: 'pbr', label: 'PBR', align: 'right', render: fmtFloat },
    { key: 'roe', label: 'ROE', align: 'right', render: fmtFloat },
    { key: 'dividend_yield', label: '배당', align: 'right', render: fmtDivYield },
    { key: 'seo_return', label: '기대수익률', align: 'right',
      render: (v) => v != null ? `${fmtFloat(v)}%` : '-' },
    { key: 'mktcap', label: '시총', align: 'right', render: fmtMktcap },
  ]

  if (hasGuru) {
    cols.push(
      { key: '_guru', label: '구루', align: 'center', sortable: false,
        render: (_, row) => <GuruScoreBadge scores={row.guru_scores} /> },
      { key: '_gb', label: 'GB', align: 'center', sortable: false,
        render: (_, row) => {
          const gb = row.guru_scores?.greenblatt
          if (!gb?.calculable) return <span className="text-gray-300">-</span>
          return <FormulaScore score={Math.min(4, Math.round(gb.total_score / 2))} />
        }},
      { key: '_nf', label: 'NF', align: 'center', sortable: false,
        render: (_, row) => {
          const nf = row.guru_scores?.neff
          return <FormulaScore score={nf?.calculable ? nf.neff_score : null} />
        }},
      { key: '_vt', label: '', align: 'center', sortable: false,
        render: (_, row) => <ValueTrapIcon warnings={row.value_trap_warnings} /> },
    )
  }

  return cols
}

export default function StockTable({ stocks, hasGuru }) {
  const [watchlistSet, setWatchlistSet] = useState(new Set())

  useEffect(() => {
    fetchWatchlist()
      .then(data => {
        const s = new Set((data.items || []).filter(i => i.market === 'KR').map(i => i.code))
        setWatchlistSet(s)
      })
      .catch(() => {})
  }, [])

  if (!stocks || stocks.length === 0) return null

  const enriched = stocks.map((s, i) => ({ ...s, _rank: i + 1 }))

  return <DataTable columns={makeColumns(watchlistSet, hasGuru)} data={enriched} rowKey="code" />
}
