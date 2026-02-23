import { useState, useCallback } from 'react'
import { fetchBalance } from '../api/balance'

export function useBalance() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchBalance()
      setData(result)
    } catch (e) {
      setError(e.message)
      // 503은 키 미설정으로 표기 (throw하지 않음)
    } finally {
      setLoading(false)
    }
  }, [])

  return { data, loading, error, load }
}
