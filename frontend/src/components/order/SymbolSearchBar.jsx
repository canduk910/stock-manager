/**
 * 주문 페이지 공용 종목 검색 바.
 * 시장 선택 + 종목 검색/자동완성 + 선택된 종목 표시.
 *
 * Props:
 *   market          - 'KR' | 'US' (controlled)
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
]

export default function SymbolSearchBar({
  market = 'KR',
  onMarketChange,
  symbol = '',
  symbolName = '',
  onSymbolSelect,
  defaultQuery = '',
}) {
  const [searchQuery, setSearchQuery] = useState(defaultQuery || symbol || '')
  const [suggestions, setSuggestions] = useState([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [searching, setSearching] = useState(false)
  const [validating, setValidating] = useState(false)
  const [validResult, setValidResult] = useState(
    // 잔고 연계로 symbol/name이 이미 있으면 초기 검증 완료 상태
    symbolName ? { name: symbolName } : null
  )

  const dropdownRef = useRef(null)
  const debounceTimer = useRef(null)
  // 현재 market을 ref로 추적 — async 완료 시점에 market이 바뀌었는지 판단
  const marketRef = useRef(market)
  useEffect(() => { marketRef.current = market }, [market])

  // defaultQuery 변경 시 반영 (잔고 연계)
  useEffect(() => {
    if (defaultQuery) setSearchQuery(defaultQuery)
  }, [defaultQuery])

  // 시장 변경 시 검색 상태 완전 초기화 (대기 중 debounce도 취소)
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

  // KR 검색 즉시 실행
  const execKRSearch = useCallback(async (q) => {
    if (!q || q.length < 2) {
      setSuggestions([])
      setShowDropdown(false)
      return
    }
    setSearching(true)
    const results = await searchStocks(q, 'KR')
    setSearching(false)
    setSuggestions(results)
    setShowDropdown(true)
  }, [])

  // KR debounce 자동 검색
  const handleKRSearch = useCallback((q) => {
    clearTimeout(debounceTimer.current)
    if (!q || q.length < 2) { setSuggestions([]); setShowDropdown(false); return }
    debounceTimer.current = setTimeout(() => execKRSearch(q), 400)
  }, [execKRSearch])

  // US 즉시 검증
  const execUSValidate = useCallback(async (ticker) => {
    if (!ticker) { setValidResult(null); return }
    setValidating(true)
    setValidResult(null)
    const results = await searchStocks(ticker, 'US')
    // 응답 도중 시장이 바뀌었으면 결과 무시 (시장 강제 복귀 방지)
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
    if (market === 'KR') {
      handleKRSearch(q)
    } else {
      clearTimeout(debounceTimer.current)
      debounceTimer.current = setTimeout(() => execUSValidate(q.toUpperCase()), 500)
    }
  }

  // 검색 버튼 / Enter 즉시 실행
  const handleSubmit = () => {
    clearTimeout(debounceTimer.current)
    if (market === 'KR') {
      execKRSearch(searchQuery)
    } else {
      execUSValidate(searchQuery.toUpperCase())
    }
  }

  // KR 자동완성 항목 선택
  const handleSelect = (item) => {
    setSearchQuery(`${item.name} (${item.code})`)
    setShowDropdown(false)
    setSuggestions([])
    onSymbolSelect?.({ code: item.code, name: item.name, market: market })
  }

  const isSelected = !!symbol
  const isKR = market === 'KR'

  return (
    <div className="bg-gray-50 rounded-xl border border-gray-200 p-4 space-y-3">
      {/* 시장 선택 + 검색 입력 */}
      <div className="flex gap-2 items-end">
        {/* 시장 드롭다운 */}
        <div className="shrink-0">
          <label className="block text-xs font-medium text-gray-500 mb-1">시장</label>
          <select
            value={market}
            onChange={(e) => onMarketChange?.(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1.5 text-sm bg-white"
          >
            {MARKET_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        {/* 종목 검색 입력 */}
        <div className="flex-1 relative" ref={dropdownRef}>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            {isKR ? '종목 검색 (코드 또는 이름)' : '티커 코드'}
          </label>
          <div className="flex gap-1">
            <input
              type="text"
              value={searchQuery}
              onChange={handleChange}
              onFocus={() => isKR && suggestions.length > 0 && setShowDropdown(true)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') setShowDropdown(false)
                if (e.key === 'Enter') { e.preventDefault(); handleSubmit() }
              }}
              placeholder={isKR ? '삼성전자 또는 005930' : 'AAPL, NVDA, TSLA'}
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

          {/* KR 자동완성 드롭다운 */}
          {isKR && showDropdown && (
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
                      {item.code} · {item.market}
                    </span>
                  </li>
                ))
              )}
            </ul>
          )}
        </div>
      </div>

      {/* 선택 결과 표시 */}
      {isKR && isSelected && (
        <p className="text-xs text-green-600 font-medium">
          ✓ {symbolName} <span className="text-gray-400">({symbol})</span>
        </p>
      )}
      {!isKR && searchQuery && (
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
