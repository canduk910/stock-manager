import { apiFetch } from './client'

export function analyzePortfolio(balanceData, forceRefresh = false, userComment = null) {
  // userComment(2026-05-07): 빈/공백 trim 후 전달, null/empty면 필드 자체 미포함
  const cmt = (userComment || '').trim()
  const payload = { balance_data: balanceData, force_refresh: forceRefresh }
  if (cmt) payload.user_comment = cmt
  return apiFetch('/api/portfolio-advisor/analyze', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function fetchAdvisorHistory(limit = 20) {
  return apiFetch(`/api/portfolio-advisor/history?limit=${limit}`)
}

export function fetchAdvisorReport(reportId) {
  return apiFetch(`/api/portfolio-advisor/history/${reportId}`)
}
