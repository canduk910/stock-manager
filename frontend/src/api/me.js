/**
 * /api/me/kis — 사용자 본인 KIS 자격증명 등록/조회/삭제/재검증.
 */
import { apiFetch } from './client'

export const getMyKis = () => apiFetch('/api/me/kis')

export const saveMyKis = (payload) =>
  apiFetch('/api/me/kis', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const deleteMyKis = () =>
  apiFetch('/api/me/kis', { method: 'DELETE' })

export const validateMyKis = () =>
  apiFetch('/api/me/kis/validate', { method: 'POST' })
