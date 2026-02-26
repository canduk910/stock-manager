/**
 * 예약주문 등록 폼.
 */
import { useState } from 'react'

export default function ReservationForm({ onSubmit }) {
  const [market, setMarket] = useState('KR')
  const [symbol, setSymbol] = useState('')
  const [symbolName, setSymbolName] = useState('')
  const [side, setSide] = useState('buy')
  const [orderType, setOrderType] = useState('00')
  const [price, setPrice] = useState('')
  const [quantity, setQuantity] = useState('')
  const [conditionType, setConditionType] = useState('price_below')
  const [conditionValue, setConditionValue] = useState('')
  const [memo, setMemo] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({
      symbol: symbol.trim().toUpperCase(),
      symbol_name: symbolName.trim(),
      market,
      side,
      order_type: orderType,
      price: orderType === '01' ? 0 : Number(price) || 0,
      quantity: Number(quantity),
      condition_type: conditionType,
      condition_value: conditionValue,
      memo,
    })
    // 폼 초기화
    setSymbol('')
    setSymbolName('')
    setPrice('')
    setQuantity('')
    setConditionValue('')
    setMemo('')
  }

  const isScheduled = conditionType === 'scheduled'
  const isBuy = side === 'buy'

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* 시장/방향 */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">시장</label>
          <select
            value={market}
            onChange={(e) => setMarket(e.target.value)}
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
          >
            <option value="KR">국내 KRX</option>
            <option value="US">미국 NASDAQ·NYSE</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">매매 방향</label>
          <div className="flex rounded border border-gray-300 overflow-hidden">
            {[{ value: 'buy', label: '매수' }, { value: 'sell', label: '매도' }].map((o) => (
              <button
                key={o.value}
                type="button"
                onClick={() => setSide(o.value)}
                className={`flex-1 py-1.5 text-sm font-medium transition-colors ${
                  side === o.value
                    ? o.value === 'buy'
                      ? 'bg-red-600 text-white'
                      : 'bg-blue-600 text-white'
                    : 'text-gray-500 hover:bg-gray-50'
                }`}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 종목 */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">종목코드</label>
          <input
            type="text"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder={market === 'US' ? 'AAPL' : '005930'}
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
            required
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">종목명 (선택)</label>
          <input
            type="text"
            value={symbolName}
            onChange={(e) => setSymbolName(e.target.value)}
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
          />
        </div>
      </div>

      {/* 주문유형/가격/수량 */}
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">주문유형</label>
          <select
            value={orderType}
            onChange={(e) => setOrderType(e.target.value)}
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
          >
            <option value="00">지정가</option>
            <option value="01">시장가</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">주문가격</label>
          <input
            type="number"
            value={orderType === '01' ? '' : price}
            onChange={(e) => setPrice(e.target.value)}
            disabled={orderType === '01'}
            placeholder={orderType === '01' ? '시장가' : '가격'}
            min="0"
            step={market === 'US' ? '0.01' : '1'}
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm disabled:bg-gray-50"
            required={orderType !== '01'}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">수량</label>
          <input
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="주"
            min="1"
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
            required
          />
        </div>
      </div>

      {/* 조건 */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">발동 조건</label>
          <select
            value={conditionType}
            onChange={(e) => setConditionType(e.target.value)}
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
          >
            <option value="price_below">현재가 이하 (가격 조건 매수)</option>
            <option value="price_above">현재가 이상 (가격 조건 매도)</option>
            <option value="scheduled">지정 시각 발동</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            {isScheduled ? '발동 시각 (ISO 8601)' : '목표 가격'}
          </label>
          <input
            type={isScheduled ? 'datetime-local' : 'number'}
            value={conditionValue}
            onChange={(e) => setConditionValue(
              isScheduled ? e.target.value : e.target.value
            )}
            placeholder={isScheduled ? '' : market === 'KR' ? '원' : 'USD'}
            step={!isScheduled && market === 'US' ? '0.01' : !isScheduled ? '1' : undefined}
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
            required
          />
        </div>
      </div>

      {/* 메모 */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">메모</label>
        <input
          type="text"
          value={memo}
          onChange={(e) => setMemo(e.target.value)}
          placeholder="예약주문 메모"
          className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
        />
      </div>

      <button
        type="submit"
        className={`w-full py-2.5 rounded font-semibold text-sm text-white ${
          isBuy ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'
        }`}
      >
        예약주문 등록
      </button>
    </form>
  )
}
