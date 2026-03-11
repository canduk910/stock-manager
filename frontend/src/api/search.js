export async function searchStocks(q, market = 'KR') {
  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(q)}&market=${market}`)
    if (!res.ok) return []
    return res.json()
  } catch {
    return []
  }
}
