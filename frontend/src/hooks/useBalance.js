import { useCallback } from 'react'
import { useAsyncState } from './useAsyncState'
import { fetchBalance } from '../api/balance'

export function useBalance() {
  const { data, loading, error, run } = useAsyncState()
  const load = useCallback(() => run(() => fetchBalance()).catch(() => {}), [run])
  return { data, loading, error, load }
}
