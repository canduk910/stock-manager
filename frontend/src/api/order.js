import { apiFetch } from './client'

/**
 * R10 (KIS 멀티 계좌): 모든 호출에 accountLabel 옵션 지원.
 * accountLabel=null/undefined → default 계좌 폴백 (서버측).
 */

const _qs = (params) => {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v === null || v === undefined || v === '') return
    q.append(k, v)
  })
  const s = q.toString()
  return s ? `?${s}` : ''
}

// ── 주문 발송 ──────────────────────────────────────────────────────────────
export const placeOrder = (body) =>
  apiFetch('/api/order/place', {
    method: 'POST',
    body: JSON.stringify(body),
  })

// ── 매수가능 조회 ──────────────────────────────────────────────────────────
export const fetchBuyable = (
  symbol, market = 'KR', price = 0, orderType = '00', side = 'buy', accountLabel = null,
) => apiFetch(
  `/api/order/buyable${_qs({
    symbol, market, price, order_type: orderType, side, account_label: accountLabel,
  })}`,
)

// ── 선물옵션 시세 조회 ─────────────────────────────────────────────────────
export const fetchFnoPrice = (symbol, mrktDiv = 'F') =>
  apiFetch(`/api/order/fno-price?symbol=${encodeURIComponent(symbol)}&mrkt_div=${mrktDiv}`)

// ── 미체결 주문 목록 ───────────────────────────────────────────────────────
export const fetchOpenOrders = (market = 'KR', accountLabel = null) =>
  apiFetch(`/api/order/open${_qs({ market, account_label: accountLabel })}`)

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
export const fetchExecutions = (market = 'KR', accountLabel = null) =>
  apiFetch(`/api/order/executions${_qs({ market, account_label: accountLabel })}`)

// ── 로컬 주문 이력 ─────────────────────────────────────────────────────────
export const fetchOrderHistory = ({
  symbol, market, status, dateFrom, dateTo, limit = 100, accountLabel = null,
} = {}) => apiFetch(`/api/order/history${_qs({
  symbol, market, status, date_from: dateFrom, date_to: dateTo, limit, account_label: accountLabel,
})}`)

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
export const fetchReservations = (status = null, accountLabel = null) =>
  apiFetch(`/api/order/reserves${_qs({ status, account_label: accountLabel })}`)

// ── 예약주문 삭제 ──────────────────────────────────────────────────────────
export const deleteReservation = (id) =>
  apiFetch(`/api/order/reserve/${id}`, { method: 'DELETE' })
