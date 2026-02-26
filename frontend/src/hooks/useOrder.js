import { useState, useCallback } from 'react'
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
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const place = useCallback(async (body) => {
    setLoading(true)
    setError(null)
    try {
      const data = await placeOrder(body)
      return data.order
    } catch (e) {
      setError(e.message)
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  return { loading, error, place }
}

/** 매수가능 조회 */
export function useBuyable() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async (symbol, market = 'KR', price = 0, orderType = '00') => {
    setLoading(true)
    setError(null)
    setData(null)
    try {
      const result = await fetchBuyable(symbol, market, price, orderType)
      setData(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  return { data, loading, error, load }
}

/** 미체결 주문 목록 */
export function useOpenOrders() {
  const [orders, setOrders] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async (market = 'KR') => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchOpenOrders(market)
      setOrders(data.orders)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const modify = useCallback(async (orderNo, body) => {
    await modifyOrder(orderNo, body)
  }, [])

  const cancel = useCallback(async (orderNo, body) => {
    await cancelOrder(orderNo, body)
  }, [])

  return { orders, loading, error, load, modify, cancel }
}

/** 당일 체결 내역 */
export function useExecutions() {
  const [executions, setExecutions] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async (market = 'KR') => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchExecutions(market)
      setExecutions(data.executions)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  return { executions, loading, error, load }
}

/** 로컬 주문 이력 */
export function useOrderHistory() {
  const [orders, setOrders] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async (filters = {}) => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchOrderHistory(filters)
      setOrders(data.orders)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  return { orders, loading, error, load }
}

/** 대사/동기화 */
export function useOrderSync() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const sync = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await syncOrders()
      setResult(data)
      return data
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  return { result, loading, error, sync }
}

/** 예약주문 */
export function useReservations() {
  const [reservations, setReservations] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async (status = null) => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchReservations(status)
      setReservations(data.reservations)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const create = useCallback(async (body) => {
    const data = await createReservation(body)
    setReservations((prev) => (prev ? [data.reservation, ...prev] : [data.reservation]))
    return data.reservation
  }, [])

  const remove = useCallback(async (id) => {
    await deleteReservation(id)
    setReservations((prev) => prev?.filter((r) => r.id !== id) ?? [])
  }, [])

  return { reservations, loading, error, load, create, remove }
}
