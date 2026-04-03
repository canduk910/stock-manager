import { useCallback } from 'react'
import { useAsyncState } from './useAsyncState'
import { fetchDetailReport } from '../api/detail'

export function useDetailReport() {
  const { data, setData, loading, error, run } = useAsyncState()
  const load = useCallback((symbol, years = 10) => {
    setData(null)
    return run(() => fetchDetailReport(symbol, years)).catch(() => {})
  }, [run, setData])
  return { data, loading, error, load }
}
