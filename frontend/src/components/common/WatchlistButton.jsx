import { useState, useEffect } from 'react'
import { addToWatchlist } from '../../api/watchlist'

export default function WatchlistButton({ code, market = 'KR', alreadyAdded = false }) {
  const [status, setStatus] = useState(alreadyAdded ? 'exists' : 'idle')
  // idle | loading | done | error | exists

  // code/market/alreadyAdded 변경 시 상태 리셋
  useEffect(() => {
    setStatus(alreadyAdded ? 'exists' : 'idle')
  }, [code, market, alreadyAdded])

  const handleAdd = async () => {
    if ((status !== 'idle' && status !== 'error') || !code) return
    setStatus('loading')
    try {
      await addToWatchlist(code, '', market)
      setStatus('done')
    } catch {
      setStatus('error')
      setTimeout(() => setStatus('idle'), 2000)
    }
  }

  if (!code) return null

  if (status === 'exists' || status === 'done')
    return <span className="text-green-600 text-xs font-medium">★ 관심종목</span>
  if (status === 'loading')
    return <span className="text-gray-400 text-xs">추가 중...</span>

  return (
    <button
      onClick={handleAdd}
      className={`text-xs px-2 py-0.5 rounded border transition-colors ${
        status === 'error'
          ? 'border-red-300 text-red-500'
          : 'border-gray-300 text-gray-500 hover:border-blue-500 hover:text-blue-600 hover:bg-blue-50'
      }`}
    >
      {status === 'error' ? '실패' : '+ 관심'}
    </button>
  )
}
