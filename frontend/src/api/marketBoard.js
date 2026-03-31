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

// ── 시세판 별도 등록 종목 CRUD ────────────────────────────────────────────────

export async function fetchCustomStocks() {
  const res = await fetch(`${BASE}/custom-stocks`)
  if (!res.ok) throw new Error('시세판 종목 조회 실패')
  return res.json()  // { items: [{code, market, name, added_date}] }
}

export async function addCustomStock(code, name, market = 'KR') {
  const res = await fetch(`${BASE}/custom-stocks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, name, market }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || '종목 추가 실패')
  }
  return res.json()
}

export async function removeCustomStock(code, market = 'KR') {
  const res = await fetch(`${BASE}/custom-stocks/${code}?market=${market}`, {
    method: 'DELETE',
  })
  if (!res.ok && res.status !== 404) throw new Error('종목 삭제 실패')
}

// ── 종목 순서 ─────────────────────────────────────────────────────────────────

export async function fetchBoardOrder() {
  const res = await fetch(`${BASE}/order`)
  if (!res.ok) throw new Error('순서 조회 실패')
  return res.json()  // { items: [{code, market, position}] }
}

export async function saveBoardOrder(items) {
  // items: [{code, market}, ...]
  const res = await fetch(`${BASE}/order`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items }),
  })
  if (!res.ok) throw new Error('순서 저장 실패')
  return res.json()
}
