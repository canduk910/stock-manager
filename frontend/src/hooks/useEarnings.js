import { useCallback } from 'react'
import { useAsyncState } from './useAsyncState'
import { fetchFilings } from '../api/earnings'

export function useEarnings() {
  const { data, loading, error, run } = useAsyncState()
  const load = useCallback(
    (startDate, endDate, market = 'KR') => run(() => fetchFilings(startDate, endDate, market)).catch(() => {}),
    [run]
  )
  return { data, loading, error, load }
}
