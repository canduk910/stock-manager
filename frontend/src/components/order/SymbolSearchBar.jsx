/**
 * 주문 페이지 공용 종목 검색 바.
 * 시장 선택 + 종목 검색/자동완성 + 선택된 종목 표시.
 *
 * Props:
 *   market          - 'KR' | 'US' | 'FNO' (controlled)
 *   onMarketChange  - (market) => void
 *   symbol          - 선택된 종목코드 (controlled)
 *   symbolName      - 선택된 종목명 (controlled)
 *   onSymbolSelect  - ({ code, name, market }) => void  종목 확정 시 콜백
 *   defaultQuery    - 초기 검색어 (잔고 연계 등)
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { searchStocks } from '../../api/search'

const MARKET_OPTIONS = [
  { value: 'KR', label: '국내 KRX' },
  { value: 'US', label: '미국 NASDAQ·NYSE' },
  { value: 'FNO', label: '선물옵션' },
]

export default function SymbolSearchBar({
  market = 'KR',
  onMarketChange,
  symbol = '',
  symbolName = '',
  onSymbolSelect,
  defaultQuery = '',
  markets,
}) {
  const [searchQuery, setSearchQuery] = useState(defaultQuery || symbol || '')
  const [suggestions, setSuggestions] = useState([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [searching, setSearching] = useState(false)
  const [validating, setValidating] = useState(false)
  const [validResult, setValidResult] = useState(
    symbolName ? { name: symbolName } : null
  )

  const dropdownRef = useRef(null)
  const debounceTimer = useRef(null)
  const marketRef = useRef(market)
  useEffect(() => { marketRef.current = market }, [market])

  // KR/FNO: 자동완성 드롭다운. US: 티커 직접 입력
  const isAutoComplete = market === 'KR' || market === 'FNO'
  const isFNO = market === 'FNO'

  useEffect(() => {
    if (defaultQuery) setSearchQuery(defaultQuery)
  }, [defaultQuery])

  // 시장 변경 시 검색 상태 완전 초기화
  useEffect(() => {
    clearTimeout(debounceTimer.current)
    setSearchQuery('')
    setSuggestions([])
    setShowDropdown(false)
    setValidResult(null)
    setValidating(false)
    setSearching(false)
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

  // KR/FNO 자동완성 검색 즉시 실행
  const execAutoSearch = useCallback(async (q, mkt) => {
    if (!q || q.length < 2) {
      setSuggestions([])
      setShowDropdown(false)
      return
    }
    setSearching(true)
    const results = await searchStocks(q, mkt)
    setSearching(false)
    setSuggestions(results)
    setShowDropdown(true)
  }, [])

  // KR/FNO debounce 자동 검색
  const handleAutoSearch = useCallback((q, mkt) => {
    clearTimeout(debounceTimer.current)
    if (!q || q.length < 2) { setSuggestions([]); setShowDropdown(false); return }
    debounceTimer.current = setTimeout(() => execAutoSearch(q, mkt), 400)
  }, [execAutoSearch])

  // US 즉시 검증
  const execUSValidate = useCallback(async (ticker) => {
    if (!ticker) { setValidResult(null); return }
    setValidating(true)
    setValidResult(null)
    const results = await searchStocks(ticker, 'US')
    if (marketRef.current !== 'US') { setValidating(false); return }
    setValidating(false)
    if (results.length > 0) {
      const item = results[0]
      setValidResult({ name: item.name })
      onSymbolSelect?.({ code: item.code, name: item.name, market: 'US' })
    } else {
      setValidResult(false)
    }
  }, [onSymbolSelect])

  // 입력 변경
  const handleChange = (e) => {
    const q = e.target.value
    setSearchQuery(q)
    if (isAutoComplete) {
      handleAutoSearch(q, market)
    } else {
      clearTimeout(debounceTimer.current)
      debounceTimer.current = setTimeout(() => execUSValidate(q.toUpperCase()), 500)
    }
  }

  // 검색 버튼 / Enter 즉시 실행
  const handleSubmit = () => {
    clearTimeout(debounceTimer.current)
    if (isAutoComplete) {
      execAutoSearch(searchQuery, market)
    } else {
      execUSValidate(searchQuery.toUpperCase())
    }
  }

  // 자동완성 항목 선택
  const handleSelect = (item) => {
    setSearchQuery(`${item.name} (${item.code})`)
    setShowDropdown(false)
    setSuggestions([])
    onSymbolSelect?.({ code: item.code, name: item.name, market: market })
  }

  const isSelected = !!symbol

  return (
    <div className="bg-gray-50 rounded-xl border border-gray-200 p-4 space-y-3">
      <div className="flex gap-2 items-end">
        {/* 시장 드롭다운 */}
        <div className="shrink-0">
          <label className="block text-xs font-medium text-gray-500 mb-1">시장</label>
          <select
            value={market}
            onChange={(e) => onMarketChange?.(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1.5 text-sm bg-white"
          >
            {(markets ? MARKET_OPTIONS.filter((o) => markets.includes(o.value)) : MARKET_OPTIONS).map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        {/* 종목 검색 입력 */}
        <div className="flex-1 relative" ref={dropdownRef}>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            {isAutoComplete
              ? (isFNO ? '선물옵션 검색 (단축코드 또는 종목명)' : '종목 검색 (코드 또는 이름)')
              : '티커 코드'}
          </label>
          <div className="flex gap-1">
            <input
              type="text"
              value={searchQuery}
              onChange={handleChange}
              onFocus={() => isAutoComplete && suggestions.length > 0 && setShowDropdown(true)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') setShowDropdown(false)
                if (e.key === 'Enter') { e.preventDefault(); handleSubmit() }
              }}
              placeholder={
                isFNO ? '101W09, KOSPI200...' :
                market === 'KR' ? '삼성전자 또는 005930' : 'AAPL, NVDA, TSLA'
              }
              className="flex-1 border border-gray-300 rounded px-2 py-1.5 text-sm bg-white min-w-0"
            />
            <button
              type="button"
              onClick={handleSubmit}
              disabled={searching || validating || !searchQuery}
              className="px-3 py-1.5 bg-gray-700 text-white text-sm rounded hover:bg-gray-800 disabled:opacity-40 flex items-center gap-1 whitespace-nowrap shrink-0"
            >
              {(searching || validating)
                ? <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                : '🔍'}
              검색
            </button>
          </div>

          {/* KR/FNO 자동완성 드롭다운 */}
          {isAutoComplete && showDropdown && (
            <ul className="absolute z-50 w-full bg-white border border-gray-200 rounded shadow-lg mt-1 max-h-52 overflow-y-auto">
              {suggestions.length === 0 ? (
                <li className="px-3 py-2 text-xs text-gray-400">검색 결과 없음</li>
              ) : (
                suggestions.map((item) => (
                  <li
                    key={item.code}
                    onMouseDown={() => handleSelect(item)}
                    className="px-3 py-2 text-sm cursor-pointer hover:bg-blue-50 flex items-center justify-between"
                  >
                    <span className="font-medium">{item.name}</span>
                    <span className="text-xs text-gray-400 ml-2">
                      {item.code}
                      {isFNO && item.underlying_name
                        ? ` · ${item.underlying_name}`
                        : ` · ${item.market}`}
                    </span>
                  </li>
                ))
              )}
            </ul>
          )}
        </div>
      </div>

      {/* 선택 결과 표시 */}
      {isAutoComplete && isSelected && (
        <p className="text-xs text-green-600 font-medium">
          ✓ {symbolName} <span className="text-gray-400">({symbol})</span>
        </p>
      )}
      {!isAutoComplete && searchQuery && (
        <p className={`text-xs font-medium ${
          validating ? 'text-gray-400' :
          validResult ? 'text-green-600' : symbol ? 'text-green-600' : 'text-red-500'
        }`}>
          {validating ? '검증 중...' :
           validResult ? `✓ ${validResult.name}` :
           symbol ? `✓ ${symbolName || symbol}` : '✗ 종목 없음'}
        </p>
      )}
    </div>
  )
}
