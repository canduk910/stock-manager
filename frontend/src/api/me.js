/**
 * /api/me/kis — 사용자 본인 KIS 자격증명 등록/조회/삭제/재검증.
 *
 * R8 (KIS 멀티 계좌, 2026-05-15): 멀티 계좌 CRUD.
 * 백워드 호환: getMyKis/saveMyKis/deleteMyKis/validateMyKis 보존.
 */
import { apiFetch } from './client'

// ─── 신규 멀티 계좌 API ───────────────────────────────────────────────────
export const listAccounts = () => apiFetch('/api/me/kis')

export const getAccount = (label) =>
  apiFetch(`/api/me/kis/${encodeURIComponent(label)}`)

export const createAccount = (payload) =>
  apiFetch('/api/me/kis', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const updateAccount = (label, payload) =>
  apiFetch(`/api/me/kis/${encodeURIComponent(label)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })

export const deleteAccount = (label) =>
  apiFetch(`/api/me/kis/${encodeURIComponent(label)}`, { method: 'DELETE' })

export const setDefaultAccount = (label) =>
  apiFetch(`/api/me/kis/${encodeURIComponent(label)}/default`, { method: 'POST' })

export const validateAccount = (label) =>
  apiFetch(`/api/me/kis/${encodeURIComponent(label)}/validate`, { method: 'POST' })

// ─── 백워드 호환 (default 계좌 1개 기준) ───────────────────────────────────
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
