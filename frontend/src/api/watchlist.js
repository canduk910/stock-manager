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
