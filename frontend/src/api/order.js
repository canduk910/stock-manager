import { apiFetch } from './client'

// ── 주문 발송 ──────────────────────────────────────────────────────────────
export const placeOrder = (body) =>
  apiFetch('/api/order/place', {
    method: 'POST',
    body: JSON.stringify(body),
  })

// ── 매수가능 조회 ──────────────────────────────────────────────────────────
export const fetchBuyable = (symbol, market = 'KR', price = 0, orderType = '00') =>
  apiFetch(`/api/order/buyable?symbol=${encodeURIComponent(symbol)}&market=${market}&price=${price}&order_type=${orderType}`)

// ── 미체결 주문 목록 ───────────────────────────────────────────────────────
export const fetchOpenOrders = (market = 'KR') =>
  apiFetch(`/api/order/open?market=${market}`)

// ── 주문 정정 ──────────────────────────────────────────────────────────────
export const modifyOrder = (orderNo, body) =>
  apiFetch(`/api/order/${encodeURIComponent(orderNo)}/modify`, {
    method: 'POST',
    body: JSON.stringify(body),
  })

// ── 주문 취소 ──────────────────────────────────────────────────────────────
export const cancelOrder = (orderNo, body) =>
  apiFetch(`/api/order/${encodeURIComponent(orderNo)}/cancel`, {
    method: 'POST',
    body: JSON.stringify(body),
  })

// ── 당일 체결 내역 ─────────────────────────────────────────────────────────
export const fetchExecutions = (market = 'KR') =>
  apiFetch(`/api/order/executions?market=${market}`)

// ── 로컬 주문 이력 ─────────────────────────────────────────────────────────
export const fetchOrderHistory = ({ symbol, market, status, dateFrom, dateTo, limit = 100 } = {}) => {
  const params = new URLSearchParams()
  if (symbol) params.append('symbol', symbol)
  if (market) params.append('market', market)
  if (status) params.append('status', status)
  if (dateFrom) params.append('date_from', dateFrom)
  if (dateTo) params.append('date_to', dateTo)
  params.append('limit', limit)
  return apiFetch(`/api/order/history?${params.toString()}`)
}

// ── 대사/동기화 ────────────────────────────────────────────────────────────
export const syncOrders = () =>
  apiFetch('/api/order/sync', { method: 'POST' })

// ── 예약주문 등록 ──────────────────────────────────────────────────────────
export const createReservation = (body) =>
  apiFetch('/api/order/reserve', {
    method: 'POST',
    body: JSON.stringify(body),
  })

// ── 예약주문 목록 ──────────────────────────────────────────────────────────
export const fetchReservations = (status = null) => {
  const qs = status ? `?status=${status}` : ''
  return apiFetch(`/api/order/reserves${qs}`)
}

// ── 예약주문 삭제 ──────────────────────────────────────────────────────────
export const deleteReservation = (id) =>
  apiFetch(`/api/order/reserve/${id}`, { method: 'DELETE' })
