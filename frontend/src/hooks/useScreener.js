import { useCallback } from 'react'
import { useAsyncState } from './useAsyncState'
import { fetchStocks } from '../api/screener'

export function useScreener() {
  const { data, loading, error, run } = useAsyncState()
  const search = useCallback((params) => run(() => fetchStocks(params)).catch(() => {}), [run])
  return { data, loading, error, search }
}
