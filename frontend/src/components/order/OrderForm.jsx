/**
 * 주문 발송 폼.
 * 시장/종목/매매방향/주문유형/가격/수량 입력.
 * defaultValues prop으로 잔고 페이지에서 종목 자동 입력 가능.
 */
import { useState, useEffect } from 'react'
import { useBuyable } from '../../hooks/useOrder'

const MARKET_OPTIONS = [
  { value: 'KR', label: '국내 KRX' },
  { value: 'US', label: '미국 NASDAQ·NYSE' },
]

const SIDE_OPTIONS = [
  { value: 'buy', label: '매수' },
  { value: 'sell', label: '매도' },
]

const ORDER_TYPE_OPTIONS = [
  { value: '00', label: '지정가' },
  { value: '01', label: '시장가' },
]

export default function OrderForm({ defaultValues = {}, onConfirm }) {
  const [market, setMarket] = useState(defaultValues.market || 'KR')
  const [symbol, setSymbol] = useState(defaultValues.symbol || '')
  const [symbolName, setSymbolName] = useState(defaultValues.symbol_name || '')
  const [side, setSide] = useState(defaultValues.side || 'buy')
  const [orderType, setOrderType] = useState('00')
  const [price, setPrice] = useState(defaultValues.price || '')
  const [quantity, setQuantity] = useState(defaultValues.quantity || '')
  const [memo, setMemo] = useState('')

  const { data: buyable, loading: buyableLoading, load: loadBuyable } = useBuyable()

  // defaultValues 변경 시 반영 (잔고 연계)
  useEffect(() => {
    if (defaultValues.symbol) setSymbol(defaultValues.symbol)
    if (defaultValues.symbol_name) setSymbolName(defaultValues.symbol_name)
    if (defaultValues.market) setMarket(defaultValues.market)
    if (defaultValues.side) setSide(defaultValues.side)
    if (defaultValues.price) setPrice(String(defaultValues.price))
    if (defaultValues.quantity) setQuantity(String(defaultValues.quantity))
  }, [
    defaultValues.symbol,
    defaultValues.symbol_name,
    defaultValues.market,
    defaultValues.side,
    defaultValues.price,
    defaultValues.quantity,
  ])

  const handleBuyableCheck = () => {
    if (!symbol) return
    loadBuyable(symbol, market, price || 0, orderType)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!symbol || !quantity) return

    const body = {
      symbol: symbol.trim().toUpperCase(),
      symbol_name: symbolName.trim(),
      market,
      side,
      order_type: orderType,
      price: orderType === '01' ? 0 : Number(price) || 0,
      quantity: Number(quantity),
      memo,
    }
    onConfirm(body)
  }

  const isMarketOrder = orderType === '01'
  const isBuy = side === 'buy'

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* 시장 선택 */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">시장</label>
          <select
            value={market}
            onChange={(e) => setMarket(e.target.value)}
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
          >
            {MARKET_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">매매 방향</label>
          <div className="flex rounded border border-gray-300 overflow-hidden">
            {SIDE_OPTIONS.map((o) => (
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

      {/* 종목코드 / 종목명 */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            종목코드 {market === 'US' ? '(티커)' : '(6자리)'}
          </label>
          <input
            type="text"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder={market === 'US' ? 'AAPL, NVDA, TSLA' : '005930'}
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
            placeholder="자동 입력 또는 직접 입력"
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
          />
        </div>
      </div>

      {/* 주문 유형 */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">주문 유형</label>
        <div className="flex rounded border border-gray-300 overflow-hidden">
          {ORDER_TYPE_OPTIONS.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => setOrderType(o.value)}
              className={`flex-1 py-1.5 text-sm font-medium transition-colors ${
                orderType === o.value
                  ? 'bg-gray-700 text-white'
                  : 'text-gray-500 hover:bg-gray-50'
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      {/* 가격 / 수량 */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            주문가격 {isMarketOrder && <span className="text-gray-400">(시장가 자동)</span>}
          </label>
          <input
            type="number"
            value={isMarketOrder ? '' : price}
            onChange={(e) => setPrice(e.target.value)}
            disabled={isMarketOrder}
            placeholder={isMarketOrder ? '시장가' : market === 'KR' ? '원' : 'USD'}
            min="0"
            step={market === 'US' ? '0.01' : '1'}
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm disabled:bg-gray-50 disabled:text-gray-400"
            required={!isMarketOrder}
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
            step="1"
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
            required
          />
        </div>
      </div>

      {/* 매수가능 조회 */}
      {isBuy && (
        <div className="bg-gray-50 rounded p-3 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-600">매수가능 조회</span>
            <button
              type="button"
              onClick={handleBuyableCheck}
              disabled={buyableLoading || !symbol}
              className="text-xs text-blue-600 hover:text-blue-800 disabled:text-gray-400"
            >
              {buyableLoading ? '조회 중...' : '조회'}
            </button>
          </div>
          {buyable && (
            <div className="text-xs text-gray-700 space-y-0.5">
              <div>
                가능금액: <span className="font-medium">
                  {Number(buyable.buyable_amount).toLocaleString()} {buyable.currency}
                </span>
              </div>
              <div>
                가능수량: <span className="font-medium">
                  {Number(buyable.buyable_quantity).toLocaleString()}주
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 메모 */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">메모 (선택)</label>
        <input
          type="text"
          value={memo}
          onChange={(e) => setMemo(e.target.value)}
          placeholder="주문 메모"
          className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
        />
      </div>

      {/* 주문 버튼 */}
      <button
        type="submit"
        className={`w-full py-2.5 rounded font-semibold text-sm text-white transition-colors ${
          isBuy
            ? 'bg-red-600 hover:bg-red-700'
            : 'bg-blue-600 hover:bg-blue-700'
        }`}
      >
        {isBuy ? '매수 주문' : '매도 주문'} 확인
      </button>
    </form>
  )
}
