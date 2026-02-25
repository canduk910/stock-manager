import { useState } from 'react'

export default function AddStockForm({ onAdd }) {
  const [code, setCode] = useState('')
  const [memo, setMemo] = useState('')
  const [market, setMarket] = useState('KR')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!code.trim()) return
    setLoading(true)
    setError(null)
    try {
      await onAdd(code.trim(), memo.trim(), market)
      setCode('')
      setMemo('')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const placeholder = market === 'KR' ? '005930 또는 삼성전자' : 'AAPL, NVDA, TSLA'

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
        <label className="flex flex-col gap-1">
          <span className="text-xs text-gray-500">
            {market === 'KR' ? '종목코드 또는 종목명' : '티커 코드'}
          </span>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder={placeholder}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-52 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </label>
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
          disabled={loading || !code.trim()}
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
