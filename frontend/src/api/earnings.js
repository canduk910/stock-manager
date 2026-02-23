import { apiFetch } from './client'

export function fetchFilings(date) {
  const qs = date ? `?date=${date}` : ''
  return apiFetch(`/api/earnings/filings${qs}`)
}
