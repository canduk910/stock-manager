import { useState, useCallback } from 'react'
import { fetchDetailReport } from '../api/detail'

export function useDetailReport() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async (symbol, years = 10) => {
    setLoading(true)
    setError(null)
    setData(null)
    try {
      const result = await fetchDetailReport(symbol, years)
      setData(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  return { data, loading, error, load }
}
