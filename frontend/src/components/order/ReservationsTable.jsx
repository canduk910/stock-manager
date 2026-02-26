/**
 * 예약주문 목록 테이블 + 취소 버튼.
 */

const STATUS_LABELS = {
  WAITING: '대기 중',
  TRIGGERED: '발동됨',
  EXECUTED: '실행완료',
  FAILED: '실패',
  CANCELLED: '취소',
}

const STATUS_COLORS = {
  WAITING: 'bg-yellow-100 text-yellow-700',
  TRIGGERED: 'bg-blue-100 text-blue-700',
  EXECUTED: 'bg-green-100 text-green-700',
  FAILED: 'bg-red-100 text-red-600',
  CANCELLED: 'bg-gray-100 text-gray-500',
}

const CONDITION_LABELS = {
  price_below: '가격 이하',
  price_above: '가격 이상',
  scheduled: '시간 예약',
}

function StatusBadge({ status }) {
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
      STATUS_COLORS[status] || 'bg-gray-100 text-gray-600'
    }`}>
      {STATUS_LABELS[status] || status}
    </span>
  )
}

export default function ReservationsTable({ reservations, onDelete }) {
  if (!reservations || reservations.length === 0) {
    return <div className="text-center py-8 text-gray-400 text-sm">등록된 예약주문이 없습니다.</div>
  }

  const handleDelete = (res) => {
    if (!confirm(`예약주문을 취소하시겠습니까?\n[${res.symbol_name || res.symbol}] ${res.side === 'buy' ? '매수' : '매도'}`)) return
    onDelete(res.id)
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50">
            {['ID', '시장', '종목', '매매', '주문유형', '주문가', '수량', '조건', '조건값', '상태', '등록일', ''].map((h) => (
              <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-gray-600 whitespace-nowrap">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {reservations.map((res) => (
            <tr key={res.id} className="hover:bg-gray-50">
              <td className="px-3 py-2 text-xs text-gray-400">{res.id}</td>
              <td className="px-3 py-2 text-xs text-gray-500">{res.market}</td>
              <td className="px-3 py-2">
                <div className="font-medium text-gray-900">{res.symbol_name || res.symbol}</div>
                <div className="text-xs text-gray-400">{res.symbol}</div>
              </td>
              <td className="px-3 py-2">
                <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-bold ${
                  res.side === 'buy' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'
                }`}>
                  {res.side === 'buy' ? '매수' : '매도'}
                </span>
              </td>
              <td className="px-3 py-2 text-xs text-gray-600">
                {res.order_type === '01' ? '시장가' : '지정가'}
              </td>
              <td className="px-3 py-2 text-right font-mono text-xs">
                {res.price > 0 ? Number(res.price).toLocaleString() : '시장가'}
              </td>
              <td className="px-3 py-2 text-right font-mono text-xs">{Number(res.quantity).toLocaleString()}</td>
              <td className="px-3 py-2 text-xs text-gray-600">
                {CONDITION_LABELS[res.condition_type] || res.condition_type}
              </td>
              <td className="px-3 py-2 font-mono text-xs text-gray-700">
                {res.condition_type === 'scheduled'
                  ? res.condition_value?.slice(0, 16)
                  : Number(res.condition_value).toLocaleString()}
              </td>
              <td className="px-3 py-2"><StatusBadge status={res.status} /></td>
              <td className="px-3 py-2 text-xs text-gray-400 whitespace-nowrap">
                {res.created_at?.slice(0, 16)}
              </td>
              <td className="px-3 py-2">
                {res.status === 'WAITING' && (
                  <button
                    onClick={() => handleDelete(res)}
                    className="px-2 py-1 text-xs rounded border border-red-300 text-red-600 hover:bg-red-50"
                  >
                    취소
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
