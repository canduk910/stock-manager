import { useState } from 'react'
import { placeOrder } from '../../api/order'

function Row({ label, value, valueClass = 'text-gray-900' }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-gray-500">{label}</span>
      <span className={valueClass}>{value}</span>
    </div>
  )
}

export default function TradeConfirmModal({ trade, onClose, notify }) {
  const [loading, setLoading] = useState(false)

  if (!trade) return null

  const isBuy = trade.action === 'buy'
  const marketLabel = trade.market === 'KR' ? '국내 KRX' : '미국 NASDAQ·NYSE'

  const handleConfirm = async () => {
    setLoading(true)
    try {
      await placeOrder({
        symbol: trade.stock_code,
        symbol_name: trade.stock_name,
        market: trade.market || 'KR',
        side: trade.action,
        order_type: '00',  // 지정가
        price: trade.target_price,
        quantity: trade.qty,
        memo: `[AI자문] ${trade.reason?.slice(0, 50) || ''}`,
      })
      notify?.('주문이 발송되었습니다.', 'success')
      onClose()
    } catch (e) {
      notify?.(`주문 실패: ${e.message}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-3">AI 추천 주문 확인</h3>

        {/* 경고 */}
        <div className="mb-4 p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
          AI 추천 기반 주문입니다. 실제 체결되며, 투자 판단의 책임은 본인에게 있습니다.
        </div>

        <div className="space-y-3 mb-4">
          <Row label="시장" value={marketLabel} />
          <Row label="종목" value={`${trade.stock_name} (${trade.stock_code})`} />
          <Row
            label="매매방향"
            value={isBuy ? '매수' : '매도'}
            valueClass={isBuy ? 'text-red-600 font-bold' : 'text-blue-600 font-bold'}
          />
          <Row label="주문유형" value="지정가" />
          <Row
            label="목표가"
            value={`${Number(trade.target_price).toLocaleString()} ${trade.market === 'KR' ? '원' : 'USD'}`}
          />
          <Row label="수량" value={`${Number(trade.qty).toLocaleString()}주`} />
          <Row
            label="주문금액"
            value={`≈ ${(Number(trade.target_price) * Number(trade.qty)).toLocaleString()} ${trade.market === 'KR' ? '원' : 'USD'}`}
            valueClass="font-semibold"
          />
        </div>

        {/* AI 근거 */}
        {trade.reason && (
          <div className="mb-4 p-2.5 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-xs font-medium text-blue-700 mb-0.5">AI 분석 근거</p>
            <p className="text-xs text-blue-600">{trade.reason}</p>
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={onClose}
            disabled={loading}
            className="flex-1 py-2.5 rounded border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            취소
          </button>
          <button
            onClick={handleConfirm}
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
