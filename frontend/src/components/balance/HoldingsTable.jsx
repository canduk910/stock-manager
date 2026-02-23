import DataTable from '../common/DataTable'

function fmtKRW(val) {
  const n = Number(val)
  if (isNaN(n)) return val || '-'
  return n.toLocaleString('ko-KR')
}

/** 한국 관례: 수익 = 빨간색, 손실 = 파란색 */
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

const COLUMNS = [
  { key: 'code', label: '종목코드', align: 'center' },
  { key: 'name', label: '종목명', align: 'left' },
  { key: 'quantity', label: '보유수량', align: 'right', render: fmtKRW },
  { key: 'avg_price', label: '매입단가', align: 'right', render: fmtKRW },
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

export default function HoldingsTable({ stocks }) {
  return <DataTable columns={COLUMNS} data={stocks} rowKey="code" />
}
