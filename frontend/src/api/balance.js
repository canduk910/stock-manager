import { apiFetch } from './client'

/**
 * 잔고 조회. R9 (KIS 멀티 계좌):
 * - accountLabel=null/undefined → 전체 계좌 합산 모드
 * - accountLabel='주식' → 단독 계좌 조회 (동일 합산 shape)
 */
export function fetchBalance(accountLabel = null) {
  const qs = accountLabel ? `?account_label=${encodeURIComponent(accountLabel)}` : ''
  return apiFetch(`/api/balance${qs}`)
}
