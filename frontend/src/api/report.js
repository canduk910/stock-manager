import { apiFetch } from './client'

// 일일 보고서
export const fetchReports = (market, limit = 30, offset = 0) => {
  const params = new URLSearchParams()
  if (market) params.set('market', market)
  params.set('limit', limit)
  params.set('offset', offset)
  return apiFetch(`/api/reports?${params}`)
}

export const fetchReport = (id) => apiFetch(`/api/reports/${id}`)

export const fetchReportByDate = (date, market = 'KR') =>
  apiFetch(`/api/reports/by-date?date=${date}&market=${market}`)

// 추천 이력
export const fetchRecommendations = (market, status, limit = 50, offset = 0) => {
  const params = new URLSearchParams()
  if (market) params.set('market', market)
  if (status) params.set('status', status)
  params.set('limit', limit)
  params.set('offset', offset)
  return apiFetch(`/api/reports/recommendations?${params}`)
}

export const fetchRecommendation = (id) => apiFetch(`/api/reports/recommendations/${id}`)

// 성과
export const fetchPerformance = (market) => {
  const params = market ? `?market=${market}` : ''
  return apiFetch(`/api/reports/performance${params}`)
}

// 매크로 체제 이력
export const fetchRegimes = (limit = 90) => apiFetch(`/api/reports/regimes?limit=${limit}`)
export const fetchLatestRegime = () => apiFetch(`/api/reports/regimes/latest`)
