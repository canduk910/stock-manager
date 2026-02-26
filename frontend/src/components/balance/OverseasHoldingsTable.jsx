import DataTable from '../common/DataTable'
import { useNavigate } from 'react-router-dom'

const EXCHANGE_LABELS = {
  NASD: '나스닥',
  NYSE: '뉴욕',
  AMEX: '아멕스',
  SEHK: '홍콩',
  SHAA: '상해',
  SZAA: '심천',
  TKSE: '도쿄',
  HASE: '하노이',
  VNSE: '호치민',
}

function fmtForeign(val) {
  const n = Number(val)
  if (isNaN(n)) return val || '-'
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
}

function fmtKRW(val) {
  const n = Number(val)
  if (isNaN(n) || val === '' || val === '0') return '-'
  return n.toLocaleString('ko-KR')
}

function fmtMktcapUSD(v) {
  if (v == null) return '-'
  const abs = Math.abs(v)
  if (abs >= 1e12) return `$${(v / 1e12).toFixed(1)}T`
  if (abs >= 1e9) return `$${(v / 1e9).toFixed(1)}B`
  if (abs >= 1e6) return `$${(v / 1e6).toFixed(0)}M`
  return `$${v.toLocaleString()}`
}

function WeightCell({ value }) {
  if (value == null) return <span className="text-gray-400">-</span>
  return <span className="text-gray-700 font-medium">{value.toFixed(1)}%</span>
}

function ForeignProfitCell({ value, currency }) {
  const n = Number(value)
  if (isNaN(n)) return <span>{value || '-'}</span>
  const cls = n > 0 ? 'text-red-600' : n < 0 ? 'text-blue-600' : 'text-gray-600'
  const sign = n > 0 ? '+' : ''
  return (
    <span className={`font-medium ${cls}`}>
      {sign}{n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
      {currency ? <span className="text-xs text-gray-400 ml-1">{currency}</span> : null}
    </span>
  )
}

function KRWProfitCell({ value }) {
  const n = Number(value)
  if (isNaN(n) || value === '' || value === '0') return <span className="text-gray-400">-</span>
  const cls = n > 0 ? 'text-red-600' : n < 0 ? 'text-blue-600' : 'text-gray-600'
  const sign = n > 0 ? '+' : ''
  return <span className={`font-medium ${cls}`}>{sign}{n.toLocaleString('ko-KR')}</span>
}

function RateCell({ value }) {
  const n = parseFloat(value)
  if (isNaN(n)) return <span>{value || '-'}</span>
  const cls = n > 0 ? 'text-red-600' : n < 0 ? 'text-blue-600' : 'text-gray-600'
  const sign = n > 0 ? '+' : ''
  return <span className={`font-medium ${cls}`}>{sign}{n.toFixed(2)}%</span>
}

function RoeCell({ value }) {
  if (value == null) return <span className="text-gray-400">-</span>
  const n = Number(value)
  if (isNaN(n)) return <span className="text-gray-400">-</span>
  const cls = n > 0 ? 'text-red-600' : n < 0 ? 'text-blue-600' : 'text-gray-600'
  return <span className={cls}>{n.toFixed(1)}%</span>
}

function OrderButtons({ row, navigate }) {
  const sellParams = new URLSearchParams({
    symbol: row.code,
    symbol_name: row.name || '',
    market: 'US',
    side: 'sell',
    quantity: row.quantity || '',
  })
  return (
    <div className="flex gap-1">
      <button
        onClick={() => navigate(`/order?${sellParams.toString()}`)}
        className="px-2 py-0.5 text-xs rounded border border-blue-300 text-blue-700 hover:bg-blue-50"
      >
        매도
      </button>
      <button
        onClick={() => {
          const buyParams = new URLSearchParams({ symbol: row.code, symbol_name: row.name || '', market: 'US', side: 'buy' })
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
    render: (v) => EXCHANGE_LABELS[v] || v,
  },
  { key: 'code', label: '종목코드', align: 'center' },
  { key: 'name', label: '종목명', align: 'left' },
  {
    key: '_weight',
    label: '투자비중',
    align: 'right',
    render: (v) => <WeightCell value={v} />,
  },
  {
    key: 'currency',
    label: '통화',
    align: 'center',
    render: (v) => <span className="text-xs font-medium text-gray-500">{v}</span>,
  },
  {
    key: 'quantity',
    label: '보유수량',
    align: 'right',
    render: (v) => Number(v).toLocaleString(),
  },
  {
    key: 'eval_amount',
    label: '평가금액',
    align: 'right',
    render: (v, row) => {
      const n = Number(v)
      if (isNaN(n)) return '-'
      return (
        <span>
          {n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          <span className="text-xs text-gray-400 ml-1">{row.currency}</span>
        </span>
      )
    },
  },
  {
    key: 'avg_price',
    label: '매입단가',
    align: 'right',
    render: (v) => {
      const n = Number(v)
      if (isNaN(n)) return v || '-'
      return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    },
  },
  {
    key: 'current_price',
    label: '현재가',
    align: 'right',
    render: (v) => fmtForeign(v),
  },
  {
    key: 'profit_loss',
    label: '평가손익(외화)',
    align: 'right',
    render: (v, row) => <ForeignProfitCell value={v} currency={row.currency} />,
  },
  {
    key: 'profit_loss_krw',
    label: '평가손익(원화)',
    align: 'right',
    render: (v) => <KRWProfitCell value={v} />,
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
    render: (v) => fmtMktcapUSD(v),
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

export default function OverseasHoldingsTable({ stocks }) {
  const navigate = useNavigate()
  // 투자비중: KRW 환산 평가금액 기준
  const totalEvalKRW = stocks.reduce((sum, s) => sum + (Number(s.eval_amount_krw) || 0), 0)
  const enriched = stocks.map((s) => ({
    ...s,
    _weight: totalEvalKRW > 0 ? (Number(s.eval_amount_krw) || 0) / totalEvalKRW * 100 : null,
  }))
  return <DataTable columns={COLUMNS} data={enriched} renderContext={{ navigate }} />
}
