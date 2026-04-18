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
  fetchSimulationHoldings,
  simulateTax,
} from '../api/tax'

export function useTaxSummary() {
  const state = useAsyncState(null)

  const load = useCallback(
    (year) =>
      state.run(() => fetchTaxSummary(year)).catch(() => {}),
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
    (year, symbol = '') =>
      state.run(() => fetchTaxCalculations(year, symbol)).catch(() => {}),
    [state.run],
  )

  const recalc = useCallback(
    (year) => recalculateTax(year),
    [],
  )

  return { ...state, load, recalc }
}

export function useTaxSimulation() {
  const holdingsState = useAsyncState([])
  const resultState = useAsyncState(null)

  const loadHoldings = useCallback(
    () => holdingsState.run(() => fetchSimulationHoldings()).catch(() => {}),
    [holdingsState.run],
  )

  const simulate = useCallback(
    (year, simulations) =>
      resultState.run(() => simulateTax(year, simulations)).catch(() => {}),
    [resultState.run],
  )

  return {
    holdings: holdingsState,
    result: resultState,
    loadHoldings,
    simulate,
  }
}
