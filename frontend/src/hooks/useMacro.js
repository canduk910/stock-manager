import { useCallback } from 'react'
import { useAsyncState } from './useAsyncState'
import {
  fetchMacroIndices,
  fetchMacroNews,
  fetchMacroSentiment,
  fetchMacroInvestorQuotes,
  fetchYieldCurve,
  fetchCreditSpread,
  fetchCurrencies,
  fetchCommodities,
  fetchSectorHeatmap,
  fetchMacroCycle,
} from '../api/macro'

export function useMacroIndices() {
  const { data, loading, error, run } = useAsyncState()
  const load = useCallback(() => run(() => fetchMacroIndices()).catch(() => {}), [run])
  return { data, loading, error, load }
}

export function useMacroNews() {
  const { data, loading, error, run } = useAsyncState()
  const load = useCallback(() => run(() => fetchMacroNews()).catch(() => {}), [run])
  return { data, loading, error, load }
}

export function useMacroSentiment() {
  const { data, loading, error, run } = useAsyncState()
  const load = useCallback(() => run(() => fetchMacroSentiment()).catch(() => {}), [run])
  return { data, loading, error, load }
}

export function useMacroInvestorQuotes() {
  const { data, loading, error, run } = useAsyncState()
  const load = useCallback(() => run(() => fetchMacroInvestorQuotes()).catch(() => {}), [run])
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

export function useSectorHeatmap() {
  const { data, loading, error, run } = useAsyncState()
  const load = useCallback(() => run(() => fetchSectorHeatmap()).catch(() => {}), [run])
  return { data, loading, error, load }
}

export function useMacroCycle() {
  const { data, loading, error, run } = useAsyncState()
  const load = useCallback(() => run(() => fetchMacroCycle()).catch(() => {}), [run])
  return { data, loading, error, load }
}
