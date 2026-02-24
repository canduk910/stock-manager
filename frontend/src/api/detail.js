import { apiFetch } from './client'

export function fetchDetailFinancials(symbol, years = 10) {
  return apiFetch(`/api/detail/financials/${symbol}?years=${years}`)
}

export function fetchDetailValuation(symbol, years = 10) {
  return apiFetch(`/api/detail/valuation/${symbol}?years=${years}`)
}

export function fetchDetailReport(symbol, years = 10) {
  return apiFetch(`/api/detail/report/${symbol}?years=${years}`)
}
