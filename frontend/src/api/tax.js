import { apiFetch } from './client'

export function fetchTaxSummary(year) {
  return apiFetch(`/api/tax/summary?year=${year}`)
}

export function fetchTaxTransactions(year, side = '') {
  const params = new URLSearchParams({ year })
  if (side) params.set('side', side)
  return apiFetch(`/api/tax/transactions?${params}`)
}

export function syncTax(year) {
  return apiFetch(`/api/tax/sync?year=${year}`, { method: 'POST' })
}

export function recalculateTax(year) {
  return apiFetch(`/api/tax/recalculate?year=${year}`, { method: 'POST' })
}

export function fetchTaxCalculations(year, symbol = '') {
  const params = new URLSearchParams({ year })
  if (symbol) params.set('symbol', symbol)
  return apiFetch(`/api/tax/calculations?${params}`)
}

export function addTaxTransaction(body) {
  return apiFetch('/api/tax/transactions', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function deleteTaxTransaction(id) {
  return apiFetch(`/api/tax/transactions/${id}`, { method: 'DELETE' })
}
