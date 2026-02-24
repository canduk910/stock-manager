import { apiFetch } from './client'

export function fetchFilings(startDate, endDate) {
  const params = new URLSearchParams()
  if (startDate) params.set('start_date', startDate)
  if (endDate) params.set('end_date', endDate)
  const qs = params.toString() ? `?${params.toString()}` : ''
  return apiFetch(`/api/earnings/filings${qs}`)
}
