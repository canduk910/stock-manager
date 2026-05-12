import { apiFetch } from './client'

export const fetchWatchlist = () => apiFetch('/api/watchlist')

export const addToWatchlist = (code, memo = '', market = 'KR') =>
  apiFetch('/api/watchlist', {
    method: 'POST',
    body: JSON.stringify({ code, memo, market }),
  })

export const removeFromWatchlist = (code, market = 'KR') =>
  apiFetch(`/api/watchlist/${code}?market=${market}`, { method: 'DELETE' })

export const updateMemo = (code, memo, market = 'KR') =>
  apiFetch(`/api/watchlist/${code}?market=${market}`, {
    method: 'PATCH',
    body: JSON.stringify({ memo }),
  })

export const fetchDashboard = () => apiFetch('/api/watchlist/dashboard')

export const fetchStockInfo = (code, market = 'KR') =>
  apiFetch(`/api/watchlist/info/${code}?market=${market}`)

// 2026-05-12: 다중 종목 batch (관심종목 카드 hover 상세 등 N+1 제거용)
export const fetchWatchlistBatchDetails = (codes, market = 'auto') => {
  if (!codes || !codes.length) return Promise.resolve({ details: {}, errors: [] })
  const codesParam = Array.isArray(codes) ? codes.join(',') : String(codes)
  return apiFetch(`/api/watchlist/batch-details?codes=${encodeURIComponent(codesParam)}&market=${market}`)
}

// ── 종목 순서 ─────────────────────────────────────────────────────────────────

export const fetchWatchlistOrder = () => apiFetch('/api/watchlist/order')

export const saveWatchlistOrder = (items) =>
  apiFetch('/api/watchlist/order', {
    method: 'PUT',
    body: JSON.stringify({ items }),
  })
