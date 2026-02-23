import DataTable from '../common/DataTable'

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

const COLUMNS = [
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
