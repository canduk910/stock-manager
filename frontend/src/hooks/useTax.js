import { useCallback } from 'react'
import { useAsyncState } from './useAsyncState'
import {
  fetchTaxSummary,
  fetchTaxTransactions,
  fetchTaxCalculations,
  syncTax,
  recalculateTax,
  addTaxTransaction,
  deleteTaxTransaction,
} from '../api/tax'

export function useTaxSummary() {
  const state = useAsyncState(null)

  const load = useCallback(
    (year, method = 'FIFO') =>
      state.run(() => fetchTaxSummary(year, method)).catch(() => {}),
    [state.run],
  )

  return { ...state, load }
}

export function useTaxTransactions() {
  const state = useAsyncState({ transactions: [], count: 0 })

  const load = useCallback(
    (year, side = '') =>
      state.run(() => fetchTaxTransactions(year, side)).catch(() => {}),
    [state.run],
  )

  const sync = useCallback(
    (year) => syncTax(year),
    [],
  )

  const add = useCallback(
    (body) => addTaxTransaction(body),
    [],
  )

  const remove = useCallback(
    (id) => deleteTaxTransaction(id),
    [],
  )

  return { ...state, load, sync, add, remove }
}

export function useTaxCalculations() {
  const state = useAsyncState({ calculations: [], count: 0 })

  const load = useCallback(
    (year, method = 'FIFO', symbol = '') =>
      state.run(() => fetchTaxCalculations(year, method, symbol)).catch(() => {}),
    [state.run],
  )

  const recalc = useCallback(
    (year, method = 'FIFO') => recalculateTax(year, method),
    [],
  )

  return { ...state, load, recalc }
}
