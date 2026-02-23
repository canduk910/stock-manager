import { apiFetch } from './client'

export const fetchWatchlist = () => apiFetch('/api/watchlist')

export const addToWatchlist = (code, memo = '') =>
  apiFetch('/api/watchlist', {
    method: 'POST',
    body: JSON.stringify({ code, memo }),
  })

export const removeFromWatchlist = (code) =>
  apiFetch(`/api/watchlist/${code}`, { method: 'DELETE' })

export const updateMemo = (code, memo) =>
  apiFetch(`/api/watchlist/${code}`, {
    method: 'PATCH',
    body: JSON.stringify({ memo }),
  })

export const fetchDashboard = () => apiFetch('/api/watchlist/dashboard')

export const fetchStockInfo = (code) => apiFetch(`/api/watchlist/info/${code}`)
