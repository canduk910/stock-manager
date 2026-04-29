import { apiFetch } from './client'

// AI 사용량
export const fetchAiUsage = (date) => {
  const params = date ? `?date=${date}` : ''
  return apiFetch(`/api/admin/ai-usage${params}`)
}

export const fetchMyAiUsage = () => apiFetch('/api/admin/ai-usage/me')

// AI 한도
export const fetchAiLimits = () => apiFetch('/api/admin/ai-limits')

export const setAiLimit = (userId, dailyLimit) =>
  apiFetch('/api/admin/ai-limits', {
    method: 'PUT',
    body: JSON.stringify({ user_id: userId, daily_limit: dailyLimit }),
  })

export const deleteAiLimit = (userId) =>
  apiFetch(`/api/admin/ai-limits/${userId}`, { method: 'DELETE' })

// 감사 로그
export const fetchAuditLog = (limit = 100, offset = 0) =>
  apiFetch(`/api/admin/audit-log?limit=${limit}&offset=${offset}`)
