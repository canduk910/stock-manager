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

// ── Phase 4 단계 4: 사용자 관리 ────────────────────────────────
export const fetchUsers = ({ q = '', limit = 20, offset = 0 } = {}) => {
  const params = new URLSearchParams()
  if (q) params.set('q', q)
  params.set('limit', String(limit))
  params.set('offset', String(offset))
  return apiFetch(`/api/admin/users?${params.toString()}`)
}

export const fetchUserById = (userId) => apiFetch(`/api/admin/users/${userId}`)

export const patchUser = (userId, body) =>
  apiFetch(`/api/admin/users/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })

export const deleteUser = (userId) =>
  apiFetch(`/api/admin/users/${userId}`, { method: 'DELETE' })

// ── Phase 4 단계 5: 페이지뷰 통계 ──────────────────────────────
export const fetchPageStats = ({ from, to, top = 20 } = {}) => {
  const params = new URLSearchParams()
  if (from) params.set('from', from)
  if (to) params.set('to', to)
  params.set('top', String(top))
  return apiFetch(`/api/admin/page-stats?${params.toString()}`)
}
