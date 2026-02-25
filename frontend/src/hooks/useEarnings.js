import { useState, useCallback } from 'react'
import { fetchFilings } from '../api/earnings'

export function useEarnings() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async (startDate, endDate, market = 'KR') => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchFilings(startDate, endDate, market)
      setData(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  return { data, loading, error, load }
}
