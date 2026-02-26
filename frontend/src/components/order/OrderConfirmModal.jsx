/**
 * 주문 확인 모달.
 * 주문 실수 방지를 위해 종목/수량/가격을 재확인하고 최종 발송.
 */
export default function OrderConfirmModal({ order, onConfirm, onCancel, loading }) {
  if (!order) return null

  const isBuy = order.side === 'buy'
  const isMarket = order.order_type === '01'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4">주문 확인</h3>

        <div className="space-y-3 mb-6">
          <Row label="시장" value={order.market === 'KR' ? '국내 KRX' : '미국 NASDAQ·NYSE'} />
          <Row label="종목" value={`${order.symbol_name || order.symbol} (${order.symbol})`} />
          <Row
            label="매매방향"
            value={isBuy ? '매수' : '매도'}
            valueClass={isBuy ? 'text-red-600 font-bold' : 'text-blue-600 font-bold'}
          />
          <Row label="주문유형" value={isMarket ? '시장가' : '지정가'} />
          {!isMarket && (
            <Row
              label="주문가격"
              value={`${Number(order.price).toLocaleString()} ${order.market === 'KR' ? '원' : 'USD'}`}
            />
          )}
          <Row label="수량" value={`${Number(order.quantity).toLocaleString()}주`} />
          {!isMarket && (
            <Row
              label="주문금액"
              value={`≈ ${(Number(order.price) * Number(order.quantity)).toLocaleString()} ${order.market === 'KR' ? '원' : 'USD'}`}
              valueClass="font-semibold"
            />
          )}
          {order.memo && <Row label="메모" value={order.memo} />}
        </div>

        <div className="flex gap-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="flex-1 py-2.5 rounded border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            취소
          </button>
          <button
            onClick={() => onConfirm(order)}
            disabled={loading}
            className={`flex-1 py-2.5 rounded text-sm font-semibold text-white transition-colors disabled:opacity-50 ${
              isBuy ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {loading ? '처리 중...' : `${isBuy ? '매수' : '매도'} 주문 발송`}
          </button>
        </div>
      </div>
    </div>
  )
}

function Row({ label, value, valueClass = 'text-gray-900' }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-gray-500">{label}</span>
      <span className={valueClass}>{value}</span>
    </div>
  )
}
