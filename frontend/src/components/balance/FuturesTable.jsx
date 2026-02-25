import DataTable from '../common/DataTable'

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

function PositionBadge({ value }) {
  const isBuy = value && value.includes('매수')
  const isSell = value && value.includes('매도')
  const cls = isBuy
    ? 'bg-red-100 text-red-700'
    : isSell
    ? 'bg-blue-100 text-blue-700'
    : 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {value || '-'}
    </span>
  )
}

const COLUMNS = [
  { key: 'code', label: '종목코드', align: 'center' },
  { key: 'name', label: '종목명', align: 'left' },
  {
    key: 'trade_type',
    label: '포지션',
    align: 'center',
    render: (v) => <PositionBadge value={v} />,
  },
  { key: 'quantity', label: '미결제수량', align: 'right', render: fmtKRW },
  { key: 'avg_price', label: '평균단가', align: 'right', render: fmtKRW },
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
]

export default function FuturesTable({ positions }) {
  return <DataTable columns={COLUMNS} data={positions} />
}