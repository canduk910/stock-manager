import { useCallback } from 'react'
import { useAsyncState } from './useAsyncState'
import { fetchDetailReport, fetchDetailBundle } from '../api/detail'

export function useDetailReport() {
  const { data, setData, loading, error, run } = useAsyncState()
  const load = useCallback((symbol, years = 10) => {
    setData(null)
    return run(() => fetchDetailReport(symbol, years)).catch(() => {})
  }, [run, setData])
  return { data, loading, error, load }
}

/**
 * DetailPage 마운트용 통합 훅 (2026-05-12).
 * 백엔드 ThreadPoolExecutor 병렬 수집 + 부분 실패 보존.
 * data shape는 useDetailReport와 호환 + partial_failure 추가.
 *
 * 기존 N+1 패턴(/financials + /valuation + /report)을 1회 호출로 축약.
 */
export function useDetailBundle() {
  const { data, setData, loading, error, run } = useAsyncState()
  const load = useCallback((symbol, market = 'auto', years = 10) => {
    setData(null)
    return run(() => fetchDetailBundle(symbol, market, years)).catch(() => {})
  }, [run, setData])
  return { data, loading, error, load }
}
