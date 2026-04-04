import { useState, useRef, useEffect, useCallback } from 'react'
import { searchStocks } from '../../api/search'

export default function AddStockForm({ onAdd }) {
  const [searchQuery, setSearchQuery] = useState('')
  const [memo, setMemo] = useState('')
  const [market, setMarket] = useState('KR')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // 자동완성 상태
  const [suggestions, setSuggestions] = useState([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [searching, setSearching] = useState(false)
  const [selectedStock, setSelectedStock] = useState(null)
  const debounceRef = useRef(null)
  const dropdownRef = useRef(null)

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // 시장 변경 시 초기화
  useEffect(() => {
    clearTimeout(debounceRef.current)
    setSearchQuery('')
    setSuggestions([])
    setShowDropdown(false)
    setSelectedStock(null)
  }, [market])

  // 자동완성 검색 실행
  const execSearch = useCallback(async (q, mkt) => {
    if (!q || q.length < 2) return
    setSearching(true)
    try {
      const results = await searchStocks(q, mkt)
      setSuggestions(results)
      setShowDropdown(results.length > 0)
    } catch {
      setSuggestions([])
      setShowDropdown(false)
    } finally {
      setSearching(false)
    }
  }, [])

  const handleInputChange = (e) => {
    const q = e.target.value
    setSearchQuery(q)
    setSelectedStock(null)

    clearTimeout(debounceRef.current)
    if (market === 'US' || q.length < 2) {
      setSuggestions([])
      setShowDropdown(false)
      return
    }
    debounceRef.current = setTimeout(() => execSearch(q, market), 400)
  }

  const handleSelect = (item) => {
    setSelectedStock(item)
    setSearchQuery(`${item.name} (${item.code})`)
    setSuggestions([])
    setShowDropdown(false)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const code = selectedStock?.code || searchQuery.trim()
    if (!code) return
    setLoading(true)
    setError(null)
    try {
      await onAdd(code, memo.trim(), market)
      setSearchQuery('')
      setMemo('')
      setSelectedStock(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const placeholder = market === 'KR' ? '종목명 또는 코드 검색' : 'AAPL, NVDA, TSLA'

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-4">
      <h2 className="text-sm font-semibold text-gray-700 mb-3">종목 추가</h2>
      <div className="flex flex-wrap gap-2 items-end">
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-500">시장</span>
          <select
            value={market}
            onChange={(e) => setMarket(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 bg-white"
          >
            <option value="KR">국내 (KRX)</option>
            <option value="US">미국 (NASDAQ·NYSE)</option>
          </select>
        </label>
        <div className="relative flex flex-col gap-1" ref={dropdownRef}>
          <span className="text-xs text-gray-500">
            {market === 'KR' ? '종목 검색' : '티커 코드'}
          </span>
          <input
            type="text"
            value={searchQuery}
            onChange={handleInputChange}
            onFocus={() => suggestions.length > 0 && setShowDropdown(true)}
            placeholder={placeholder}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-60 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          {searching && (
            <span className="absolute right-2 top-7 text-xs text-gray-400">검색중...</span>
          )}
          {showDropdown && suggestions.length > 0 && (
            <ul className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto z-50">
              {suggestions.map((item, i) => (
                <li
                  key={`${item.code}-${i}`}
                  onMouseDown={() => handleSelect(item)}
                  className="px-3 py-2 hover:bg-blue-50 cursor-pointer flex justify-between items-center text-sm"
                >
                  <span className="font-medium">{item.name}</span>
                  <span className="text-xs text-gray-400">{item.code} · {item.market}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-500">메모 (선택)</span>
          <input
            type="text"
            value={memo}
            onChange={(e) => setMemo(e.target.value)}
            placeholder="투자 메모"
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </label>
        <button
          type="submit"
          disabled={loading || !searchQuery.trim()}
          className="px-5 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold rounded-lg text-sm transition-colors"
        >
          {loading ? '추가 중...' : '추가'}
        </button>
      </div>
      {market === 'US' && (
        <p className="mt-2 text-xs text-gray-400">
          미국 주식은 티커 코드를 직접 입력하세요 (예: AAPL, NVDA, TSLA). 시세는 15분 지연됩니다.
        </p>
      )}
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </form>
  )
}
