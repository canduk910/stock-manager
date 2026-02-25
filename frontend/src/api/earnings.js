import { apiFetch } from './client'

export function fetchFilings(startDate, endDate, market = 'KR') {
  const params = new URLSearchParams()
  if (startDate) params.set('start_date', startDate)
  if (endDate) params.set('end_date', endDate)
  if (market) params.set('market', market)
  const qs = params.toString() ? `?${params.toString()}` : ''
  return apiFetch(`/api/earnings/filings${qs}`)
}
