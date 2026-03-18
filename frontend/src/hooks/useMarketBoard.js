import { useState, useCallback } from 'react'
import { fetchNewHighsLows, fetchSparklines } from '../api/marketBoard'

export function useMarketBoard() {
  const [data, setData] = useState(null)   // { new_highs, new_lows, updated_at }
  const [sparklines, setSparklines] = useState({})  // { code: [{date, close}] }
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchNewHighsLows(10)
      setData(result)

      // sparkline 배치 로드 (신고가 + 신저가 종목)
      const allItems = [
        ...(result.new_highs || []).map(s => ({ code: s.code, market: 'KR' })),
        ...(result.new_lows  || []).map(s => ({ code: s.code, market: 'KR' })),
      ]
      // 중복 제거
      const unique = allItems.filter((item, idx, arr) =>
        arr.findIndex(x => x.code === item.code) === idx
      )
      if (unique.length > 0) {
        const sl = await fetchSparklines(unique)
        setSparklines(prev => ({ ...prev, ...sl }))
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const loadSparklines = useCallback(async (items) => {
    if (!items || items.length === 0) return
    try {
      const sl = await fetchSparklines(items)
      setSparklines(prev => ({ ...prev, ...sl }))
    } catch (e) {
      // sparkline 로드 실패는 조용히 무시
    }
  }, [])

  return { data, sparklines, loading, error, load, loadSparklines }
}
