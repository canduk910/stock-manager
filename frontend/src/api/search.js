import { apiFetch } from './client'

export async function searchStocks(q, market = 'KR') {
  try {
    return await apiFetch(`/api/search?q=${encodeURIComponent(q)}&market=${market}`)
  } catch {
    return []
  }
}
