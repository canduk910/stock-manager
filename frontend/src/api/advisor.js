import { apiFetch } from './client'

export function analyzePortfolio(balanceData, forceRefresh = false) {
  return apiFetch('/api/portfolio-advisor/analyze', {
    method: 'POST',
    body: JSON.stringify({ balance_data: balanceData, force_refresh: forceRefresh }),
  })
}

export function fetchAdvisorHistory(limit = 20) {
  return apiFetch(`/api/portfolio-advisor/history?limit=${limit}`)
}

export function fetchAdvisorReport(reportId) {
  return apiFetch(`/api/portfolio-advisor/history/${reportId}`)
}
