import { useCallback } from 'react'
import { useAsyncState } from './useAsyncState'
import {
  fetchMacroCycle,
  fetchYieldCurve,
  fetchCreditSpread,
  fetchCurrencies,
  fetchCommodities,
} from '../api/macro'

export function useMacroCycle() {
  const { data, loading, error, run } = useAsyncState()
  const load = useCallback(() => run(() => fetchMacroCycle()).catch(() => {}), [run])
  return { data, loading, error, load }
}

export function useYieldCurve() {
  const { data, loading, error, run } = useAsyncState()
  const load = useCallback(() => run(() => fetchYieldCurve()).catch(() => {}), [run])
  return { data, loading, error, load }
}

export function useCreditSpread() {
  const { data, loading, error, run } = useAsyncState()
  const load = useCallback(() => run(() => fetchCreditSpread()).catch(() => {}), [run])
  return { data, loading, error, load }
}

export function useCurrencies() {
  const { data, loading, error, run } = useAsyncState()
  const load = useCallback(() => run(() => fetchCurrencies()).catch(() => {}), [run])
  return { data, loading, error, load }
}

export function useCommodities() {
  const { data, loading, error, run } = useAsyncState()
  const load = useCallback(() => run(() => fetchCommodities()).catch(() => {}), [run])
  return { data, loading, error, load }
}
