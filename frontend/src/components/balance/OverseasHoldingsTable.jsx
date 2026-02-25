import DataTable from '../common/DataTable'

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
]

export default function OverseasHoldingsTable({ stocks }) {
  return <DataTable columns={COLUMNS} data={stocks} />
}