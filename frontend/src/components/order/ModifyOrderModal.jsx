/**
 * 주문 정정 모달.
 */
import { useState } from 'react'

export default function ModifyOrderModal({ order, onClose, onModify }) {
  const [price, setPrice] = useState(order.price || '')
  const [quantity, setQuantity] = useState(order.remaining_qty || order.quantity || '')
  const [total, setTotal] = useState(true)

  const handleSubmit = (e) => {
    e.preventDefault()
    onModify(order.order_no, {
      org_no: order.org_no,
      market: order.market,
      order_type: order.order_type,
      price: Number(price),
      quantity: Number(quantity),
      total,
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4">주문 정정</h3>
        <div className="text-sm text-gray-600 mb-4">
          {order.symbol_name || order.symbol} ({order.symbol}) — {order.side_label}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">새 주문가격</label>
            <input
              type="number"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              min="0"
              step={order.market === 'US' ? '0.01' : '1'}
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">수량</label>
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              min="1"
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
              required
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="total_modify"
              checked={total}
              onChange={(e) => setTotal(e.target.checked)}
              className="rounded"
            />
            <label htmlFor="total_modify" className="text-sm text-gray-700">잔량 전부 정정</label>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 rounded border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              취소
            </button>
            <button
              type="submit"
              className="flex-1 py-2 rounded bg-gray-700 text-white text-sm font-semibold hover:bg-gray-800"
            >
              정정 발송
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
