import { useCallback } from 'react'
import { useAsyncState } from './useAsyncState'
import {
  fetchMacroIndices,
  fetchMacroNews,
  fetchMacroSentiment,
  fetchMacroInvestorQuotes,
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
