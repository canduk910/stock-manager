import { useCallback } from 'react'
import { useAsyncState } from './useAsyncState'
import * as api from '../api/report'

export function useReports() {
  const { data, loading, error, run } = useAsyncState({ items: [], total: 0 })

  const load = useCallback(
    (market, limit = 30, offset = 0) =>
      run(() => api.fetchReports(market, limit, offset)).catch(() => {}),
    [run]
  )

  return { data, loading, error, load }
}

export function useReportDetail() {
  const { data, loading, error, run } = useAsyncState(null)

  const load = useCallback(
    (id) => run(() => api.fetchReport(id)).catch(() => {}),
    [run]
  )

  return { data, loading, error, load }
}

export function useRecommendations() {
  const { data, loading, error, run } = useAsyncState({ items: [], total: 0 })

  const load = useCallback(
    (market, status, limit = 50, offset = 0) =>
      run(() => api.fetchRecommendations(market, status, limit, offset)).catch(() => {}),
    [run]
  )

  return { data, loading, error, load }
}

export function usePerformance() {
  const { data, loading, error, run } = useAsyncState(null)

  const load = useCallback(
    (market) => run(() => api.fetchPerformance(market)).catch(() => {}),
    [run]
  )

  return { data, loading, error, load }
}

export function useRegimes() {
  const { data, loading, error, run } = useAsyncState([])

  const load = useCallback(
    (limit = 90) => run(() => api.fetchRegimes(limit)).catch(() => {}),
    [run]
  )

  return { data, loading, error, load }
}
