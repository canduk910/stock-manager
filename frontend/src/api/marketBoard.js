const BASE = '/api/market-board'

export async function fetchNewHighsLows(top = 10) {
  const res = await fetch(`${BASE}/new-highs-lows?top=${top}`)
  if (!res.ok) throw new Error('신고가/신저가 조회 실패')
  return res.json()
}

export async function fetchSparklines(items) {
  // items: [{ code, market }, ...]
  const res = await fetch(`${BASE}/sparklines`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items }),
  })
  if (!res.ok) throw new Error('sparkline 조회 실패')
  return res.json()
}
