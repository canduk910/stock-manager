import DataTable from '../common/DataTable'
import { useNavigate } from 'react-router-dom'

function fmtKRW(val) {
  const n = Number(val)
  if (isNaN(n)) return val || '-'
  return n.toLocaleString('ko-KR')
}

function ProfitCell({ value }) {
  const n = Number(value)
  if (isNaN(n)) return <span>{value || '-'}</span>
  const cls = n > 0 ? 'text-red-600' : n < 0 ? 'text-blue-600' : 'text-gray-600'
  return <span className={`font-medium ${cls}`}>{n.toLocaleString('ko-KR')}</span>
}

function RateCell({ value }) {
  const n = parseFloat(value)
  if (isNaN(n)) return <span>{value || '-'}</span>
  const cls = n > 0 ? 'text-red-600' : n < 0 ? 'text-blue-600' : 'text-gray-600'
  const sign = n > 0 ? '+' : ''
  return <span className={`font-medium ${cls}`}>{sign}{n.toFixed(2)}%</span>
}

function WeightCell({ value }) {
  if (value == null) return <span className="text-gray-400">-</span>
  return (
    <span className="text-gray-700 font-medium">{value.toFixed(1)}%</span>
  )
}

function fmtMktcapKRW(v) {
  if (v == null) return '-'
  const awk = v / 100000000
  if (awk >= 10000) return (awk / 10000).toFixed(1) + '조'
  return Math.floor(awk).toLocaleString() + '억'
}

function RoeCell({ value }) {
  if (value == null) return <span className="text-gray-400">-</span>
  const n = Number(value)
  if (isNaN(n)) return <span className="text-gray-400">-</span>
  const cls = n > 0 ? 'text-red-600' : n < 0 ? 'text-blue-600' : 'text-gray-600'
  return <span className={cls}>{n.toFixed(1)}%</span>
}

function OrderButtons({ row, navigate }) {
  const params = new URLSearchParams({
    symbol: row.code,
    symbol_name: row.name || '',
    market: 'KR',
    side: 'sell',
    quantity: row.quantity || '',
  })
  return (
    <div className="flex gap-1">
      <button
        onClick={() => navigate(`/order?${params.toString()}`)}
        className="px-2 py-0.5 text-xs rounded border border-blue-300 text-blue-700 hover:bg-blue-50"
      >
        매도
      </button>
      <button
        onClick={() => {
          const buyParams = new URLSearchParams({ symbol: row.code, symbol_name: row.name || '', market: 'KR', side: 'buy' })
          navigate(`/order?${buyParams.toString()}`)
        }}
        className="px-2 py-0.5 text-xs rounded border border-red-300 text-red-700 hover:bg-red-50"
      >
        매수
      </button>
    </div>
  )
}

const COLUMNS = [
  {
    key: 'exchange',
    label: '거래소',
    align: 'center',
    render: (v) => v || '-',
  },
  { key: 'code', label: '종목코드', align: 'center' },
  { key: 'name', label: '종목명', align: 'left' },
  {
    key: '_weight',
    label: '투자비중',
    align: 'right',
    render: (v) => <WeightCell value={v} />,
  },
  { key: 'quantity', label: '보유수량', align: 'right', render: fmtKRW },
  { key: 'eval_amount', label: '평가금액', align: 'right', render: fmtKRW },
  { key: 'avg_price', label: '매입단가', align: 'right', render: (v) => Math.floor(Number(v)).toLocaleString('ko-KR') },
  { key: 'current_price', label: '현재가', align: 'right', render: fmtKRW },
  {
    key: 'profit_loss',
    label: '평가손익',
    align: 'right',
    render: (v) => <ProfitCell value={v} />,
  },
  {
    key: 'profit_rate',
    label: '수익률',
    align: 'right',
    render: (v) => <RateCell value={v} />,
  },
  {
    key: 'mktcap',
    label: '시가총액',
    align: 'right',
    render: (v) => fmtMktcapKRW(v),
  },
  {
    key: 'per',
    label: 'PER',
    align: 'right',
    render: (v) => v != null ? Math.floor(v) + '배' : '-',
  },
  {
    key: 'roe',
    label: 'ROE',
    align: 'right',
    render: (v) => <RoeCell value={v} />,
  },
  {
    key: 'pbr',
    label: 'PBR',
    align: 'right',
    render: (v) => v != null ? Number(v).toFixed(2) + '배' : '-',
  },
  {
    key: '_actions',
    label: '주문',
    align: 'center',
    sortable: false,
    render: (_, row, { navigate }) => <OrderButtons row={row} navigate={navigate} />,
  },
]

export default function HoldingsTable({ stocks }) {
  const navigate = useNavigate()
  const totalEval = stocks.reduce((sum, s) => sum + (Number(s.eval_amount) || 0), 0)
  const enriched = stocks.map((s) => ({
    ...s,
    _weight: totalEval > 0 ? (Number(s.eval_amount) || 0) / totalEval * 100 : null,
  }))
  return <DataTable columns={COLUMNS} data={enriched} rowKey="code" renderContext={{ navigate }} />
}
