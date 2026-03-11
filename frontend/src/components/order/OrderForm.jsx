/**
 * 주문 발송 폼.
 * 시장/종목/매매방향/주문유형/가격/수량 입력.
 * defaultValues prop으로 잔고 페이지에서 종목 자동 입력 가능.
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useBuyable } from '../../hooks/useOrder'
import { searchStocks } from '../../api/search'

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

export default function OrderForm({ defaultValues = {}, onConfirm, externalPrice = null, onSymbolChange }) {
  const [market, setMarket] = useState(defaultValues.market || 'KR')
  const [symbol, setSymbol] = useState(defaultValues.symbol || '')
  const [symbolName, setSymbolName] = useState(defaultValues.symbol_name || '')
  const [side, setSide] = useState(defaultValues.side || 'buy')
  const [orderType, setOrderType] = useState('00')
  const [price, setPrice] = useState(defaultValues.price || '')
  const [quantity, setQuantity] = useState(defaultValues.quantity || '')
  const [memo, setMemo] = useState('')

  // 검색 관련 상태
  const [searchQuery, setSearchQuery] = useState(defaultValues.symbol || '')
  const [suggestions, setSuggestions] = useState([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [validating, setValidating] = useState(false)
  const [validResult, setValidResult] = useState(null) // null | false | { name }

  const dropdownRef = useRef(null)
  const debounceTimer = useRef(null)

  const { data: buyable, loading: buyableLoading, load: loadBuyable } = useBuyable()

  // defaultValues 변경 시 반영 (잔고 연계)
  useEffect(() => {
    if (defaultValues.symbol) {
      setSymbol(defaultValues.symbol)
      setSearchQuery(defaultValues.symbol)
    }
    if (defaultValues.symbol_name) {
      setSymbolName(defaultValues.symbol_name)
      if (defaultValues.market === 'US') {
        setValidResult({ name: defaultValues.symbol_name })
      }
    }
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

  // 호가창 가격 클릭 → 지정가 자동 세팅 (시장가일 때는 무시)
  useEffect(() => {
    if (externalPrice != null && orderType !== '01') {
      setPrice(String(externalPrice))
    }
  }, [externalPrice])

  // 시장 변경 시 검색 상태 초기화
  useEffect(() => {
    setSuggestions([])
    setShowDropdown(false)
    setValidResult(null)
  }, [market])

  // 드롭다운 외부 클릭 닫기
  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // KR 검색 debounce
  const handleKRSearch = useCallback((q) => {
    clearTimeout(debounceTimer.current)
    if (!q || q.length < 2) {
      setSuggestions([])
      setShowDropdown(false)
      return
    }
    debounceTimer.current = setTimeout(async () => {
      const results = await searchStocks(q, 'KR')
      setSuggestions(results)
      setShowDropdown(results.length > 0)
    }, 300)
  }, [])

  // US 검증 debounce
  const handleUSValidate = useCallback((q) => {
    clearTimeout(debounceTimer.current)
    if (!q) {
      setValidResult(null)
      return
    }
    setValidating(true)
    setValidResult(null)
    debounceTimer.current = setTimeout(async () => {
      const results = await searchStocks(q.toUpperCase(), 'US')
      setValidating(false)
      if (results.length > 0) {
        setValidResult({ name: results[0].name })
        setSymbolName(results[0].name)
      } else {
        setValidResult(false)
        setSymbolName('')
      }
    }, 500)
  }, [])

  const handleSearchChange = (e) => {
    const q = e.target.value
    setSearchQuery(q)

    if (market === 'KR') {
      // 6자리 숫자 입력 시 symbol만 업데이트, 드롭다운은 검색어로 처리
      setSymbol(q)
      onSymbolChange?.(q)
      handleKRSearch(q)
    } else {
      const ticker = q.toUpperCase()
      setSymbol(ticker)
      onSymbolChange?.(ticker)
      handleUSValidate(ticker)
    }
  }

  const handleSelectSuggestion = (item) => {
    setSymbol(item.code)
    setSymbolName(item.name)
    setSearchQuery(`${item.name} (${item.code})`)
    setShowDropdown(false)
    setSuggestions([])
    onSymbolChange?.(item.code)
  }

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

      {/* 종목 검색 입력 */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">
          {market === 'KR' ? '종목 검색 (코드 또는 이름)' : '티커 코드'}
        </label>
        <div className="relative" ref={dropdownRef}>
          <input
            type="text"
            value={searchQuery}
            onChange={handleSearchChange}
            onFocus={() => market === 'KR' && suggestions.length > 0 && setShowDropdown(true)}
            onKeyDown={(e) => e.key === 'Escape' && setShowDropdown(false)}
            placeholder={market === 'KR' ? '삼성전자 또는 005930' : 'AAPL, NVDA, TSLA'}
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm pr-24"
            required
          />

          {/* US 검증 상태 표시 */}
          {market === 'US' && searchQuery && (
            <span className={`absolute right-2 top-1/2 -translate-y-1/2 text-xs whitespace-nowrap ${
              validating ? 'text-gray-400' :
              validResult ? 'text-green-600' : 'text-red-500'
            }`}>
              {validating ? '검증 중...' :
               validResult ? `✓ ${validResult.name}` : searchQuery ? '✗ 종목 없음' : ''}
            </span>
          )}

          {/* KR 자동완성 드롭다운 */}
          {market === 'KR' && showDropdown && (
            <ul className="absolute z-50 w-full bg-white border border-gray-200 rounded shadow-lg mt-1 max-h-52 overflow-y-auto">
              {suggestions.length === 0 ? (
                <li className="px-3 py-2 text-xs text-gray-400">검색 결과 없음</li>
              ) : (
                suggestions.map((item) => (
                  <li
                    key={item.code}
                    onMouseDown={() => handleSelectSuggestion(item)}
                    className="px-3 py-2 text-sm cursor-pointer hover:bg-blue-50 flex items-center justify-between"
                  >
                    <span className="font-medium">{item.name}</span>
                    <span className="text-xs text-gray-400 ml-2">
                      {item.code} <span className="text-gray-300">·</span> {item.market}
                    </span>
                  </li>
                ))
              )}
            </ul>
          )}
        </div>

        {/* KR: 선택된 종목명 표시 */}
        {market === 'KR' && symbolName && !showDropdown && (
          <p className="text-xs text-green-600 mt-1">✓ {symbolName} ({symbol})</p>
        )}
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
