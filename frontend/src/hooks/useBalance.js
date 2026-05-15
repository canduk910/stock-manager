import { useCallback } from 'react'
import { useAsyncState } from './useAsyncState'
import { fetchBalance } from '../api/balance'

/**
 * R9 (KIS 멀티 계좌): useBalance(accountLabel?) — null/undefined 시 합산 모드.
 * 기존 호출자는 인자 없이 호출 → 합산 모드 (백워드 호환).
 */
export function useBalance() {
  const { data, loading, error, run } = useAsyncState()
  const load = useCallback(
    (accountLabel = null) => run(() => fetchBalance(accountLabel)).catch(() => {}),
    [run],
  )
  return { data, loading, error, load }
}
