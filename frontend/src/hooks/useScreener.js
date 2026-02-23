import { useState, useCallback } from 'react'
import { fetchStocks } from '../api/screener'

export function useScreener() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const search = useCallback(async (params) => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchStocks(params)
      setData(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  return { data, loading, error, search }
}
