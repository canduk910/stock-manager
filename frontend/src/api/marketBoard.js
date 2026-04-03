import { apiFetch } from './client'

const BASE = '/api/market-board'

export async function fetchNewHighsLows(top = 10) {
  return apiFetch(`${BASE}/new-highs-lows?top=${top}`)
}

export async function fetchSparklines(items) {
  // items: [{ code, market }, ...]
  return apiFetch(`${BASE}/sparklines`, {
    method: 'POST',
    body: JSON.stringify({ items }),
  })
}

// ── 시세판 별도 등록 종목 CRUD ────────────────────────────────────────────────

export async function fetchCustomStocks() {
  return apiFetch(`${BASE}/custom-stocks`)
}

export async function addCustomStock(code, name, market = 'KR') {
  return apiFetch(`${BASE}/custom-stocks`, {
    method: 'POST',
    body: JSON.stringify({ code, name, market }),
  })
}

export async function removeCustomStock(code, market = 'KR') {
  try {
    await apiFetch(`${BASE}/custom-stocks/${code}?market=${market}`, {
      method: 'DELETE',
    })
  } catch (e) {
    if (e.status !== 404) throw e
  }
}

// ── 종목 순서 ─────────────────────────────────────────────────────────────────

export async function fetchBoardOrder() {
  return apiFetch(`${BASE}/order`)
}

export async function saveBoardOrder(items) {
  // items: [{code, market}, ...]
  return apiFetch(`${BASE}/order`, {
    method: 'PUT',
    body: JSON.stringify({ items }),
  })
}
