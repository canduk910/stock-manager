import { useCallback } from 'react'
import { useAsyncState } from './useAsyncState'
import {
  placeOrder,
  fetchBuyable,
  fetchOpenOrders,
  modifyOrder,
  cancelOrder,
  fetchExecutions,
  fetchOrderHistory,
  syncOrders,
  createReservation,
  fetchReservations,
  deleteReservation,
} from '../api/order'

/** 주문 발송 */
export function useOrderPlace() {
  const { loading, error, run } = useAsyncState()
  const place = useCallback(async (body) => {
    const data = await run(() => placeOrder(body))
    return { order: data.order, balance_stale: data.balance_stale }
  }, [run])
  return { loading, error, place }
}

/** 매수가능 조회 */
export function useBuyable() {
  const { data, setData, loading, error, run } = useAsyncState()
  const load = useCallback((symbol, market = 'KR', price = 0, orderType = '00', side = 'buy') => {
    setData(null)
    return run(() => fetchBuyable(symbol, market, price, orderType, side)).catch(() => {})
  }, [run, setData])
  return { data, loading, error, load }
}

/** 미체결 주문 목록 */
export function useOpenOrders() {
  const { data: orders, loading, error, run } = useAsyncState()

  const load = useCallback(
    (market = 'KR') => run(() => fetchOpenOrders(market).then(d => d.orders)).catch(() => {}),
    [run]
  )

  const modify = useCallback(async (orderNo, body, market = 'KR') => {
    const result = await modifyOrder(orderNo, body)
    await load(market)
    return result
  }, [load])

  const cancel = useCallback(async (orderNo, body, market = 'KR') => {
    const result = await cancelOrder(orderNo, body)
    await load(market)
    return result
  }, [load])

  return { orders, loading, error, load, modify, cancel }
}

/** 당일 체결 내역 */
export function useExecutions() {
  const { data: executions, loading, error, run } = useAsyncState()
  const load = useCallback(
    (market = 'KR') => run(() => fetchExecutions(market).then(d => d.executions)).catch(() => {}),
    [run]
  )
  return { executions, loading, error, load }
}

/** 로컬 주문 이력 */
export function useOrderHistory() {
  const { data: orders, loading, error, run } = useAsyncState()
  const load = useCallback(
    (filters = {}) => run(() => fetchOrderHistory(filters).then(d => d.orders)).catch(() => {}),
    [run]
  )
  return { orders, loading, error, load }
}

/** 대사/동기화 */
export function useOrderSync() {
  const { data: result, loading, error, run } = useAsyncState()
  const sync = useCallback(() => run(() => syncOrders()).catch(() => {}), [run])
  return { result, loading, error, sync }
}

/** 예약주문 */
export function useReservations() {
  const { data: reservations, setData: setReservations, loading, error, run } = useAsyncState()

  const load = useCallback(
    (status = null) => run(() => fetchReservations(status).then(d => d.reservations)).catch(() => {}),
    [run]
  )

  const create = useCallback(async (body) => {
    const data = await createReservation(body)
    setReservations((prev) => (prev ? [data.reservation, ...prev] : [data.reservation]))
    return data.reservation
  }, [setReservations])

  const remove = useCallback(async (id) => {
    await deleteReservation(id)
    setReservations((prev) => prev?.filter((r) => r.id !== id) ?? [])
  }, [setReservations])

  return { reservations, loading, error, load, create, remove }
}
