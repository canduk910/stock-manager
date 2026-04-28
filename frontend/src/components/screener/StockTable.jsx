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
      {Math.round(normalized_score)} ({formulas_available}/6)
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

function HeaderWithTooltip({ label, tooltip }) {
  return (
    <span className="relative group cursor-help">
      <span className="border-b border-dashed border-gray-400">{label}</span>
      <div className="absolute z-50 hidden group-hover:block bg-gray-900 text-white text-xs font-normal leading-relaxed rounded-lg p-3 w-56 left-1/2 -translate-x-1/2 top-full mt-1.5 shadow-xl text-left whitespace-normal">
        <div className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-gray-900 rotate-45" />
        {tooltip}
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
    { key: 'sector', label: '섹터', align: 'left',
      render: (v) => v ? <span className="text-xs text-gray-600 truncate max-w-24 inline-block">{v}</span> : <span className="text-gray-300">-</span> },
    { key: 'current_price', label: '현재가', align: 'right', render: fmtPrice },
    { key: 'change_pct', label: '당일', align: 'right', render: fmtPct },
    { key: 'return_1y', label: '1Y', align: 'right', render: fmtPct },
    { key: 'drop_from_high', label: '52H대비', align: 'right', render: fmtPct },
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
      { key: '_guru', label: <HeaderWithTooltip label="구루" tooltip="6개 구루 공식의 종합 점수 (0~100). 괄호 안은 계산 가능한 공식 수 / 전체 6개. 75점 이상 우수, 50점 이상 보통." />, align: 'center', sortable: false,
        render: (_, row) => <GuruScoreBadge scores={row.guru_scores} /> },
      { key: '_gb', label: <HeaderWithTooltip label="GB" tooltip={<><span className="font-semibold">그린블라트 마법공식</span><br/>ROIC(투하자본수익률)와 EY(이익수익률) 순위를 합산. 점 4개가 만점. 두 지표 모두 높은 종목이 상위.</>} />, align: 'center', sortable: false,
        render: (_, row) => {
          const gb = row.guru_scores?.greenblatt
          if (!gb?.calculable) return <span className="text-gray-300">-</span>
          return <FormulaScore score={Math.min(4, Math.round(gb.total_score / 2))} />
        }},
      { key: '_nf', label: <HeaderWithTooltip label="NF" tooltip={<><span className="font-semibold">존 네프 총수익</span><br/>(EPS 성장률 + 배당수익률) / PER. 점 4개가 만점. 성장+배당 대비 PER이 낮을수록 매력적.</>} />, align: 'center', sortable: false,
        render: (_, row) => {
          const nf = row.guru_scores?.neff
          return <FormulaScore score={nf?.calculable ? nf.neff_score : null} />
        }},
      { key: '_vt', label: <HeaderWithTooltip label="주의" tooltip={<><span className="font-semibold">가치 함정(Value Trap) 경고</span><br/>숫자가 싸 보이지만 실제로는 위험한 종목을 식별합니다. ! 표시가 있으면 마우스를 올려 구체적 경고 내용을 확인하세요.</>} />, align: 'center', sortable: false,
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
