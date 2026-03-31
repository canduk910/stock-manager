import { useState, useCallback, useMemo } from 'react'
import {
  fetchWatchlist,
  addToWatchlist,
  removeFromWatchlist,
  updateMemo,
  fetchDashboard,
  fetchStockInfo,
  fetchWatchlistOrder,
  saveWatchlistOrder,
} from '../api/watchlist'

/** 관심종목 목록 CRUD */
export function useWatchlist() {
  const [items, setItems] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchWatchlist()
      setItems(data.items)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const add = useCallback(async (code, memo, market = 'KR') => {
    const data = await addToWatchlist(code, memo, market)
    setItems((prev) => (prev ? [...prev, data.item] : [data.item]))
    return data.item
  }, [])

  const remove = useCallback(async (code, market = 'KR') => {
    await removeFromWatchlist(code, market)
    setItems((prev) => prev?.filter((i) => !(i.code === code && i.market === market)) ?? [])
  }, [])

  const memo = useCallback(async (code, text, market = 'KR') => {
    const data = await updateMemo(code, text, market)
    setItems((prev) =>
      prev?.map((i) => (i.code === code && i.market === market ? data.item : i)) ?? []
    )
    return data.item
  }, [])

  return { items, loading, error, load, add, remove, memo }
}

/** 대시보드 데이터 + 순서 관리 */
export function useDashboard() {
  const [rawStocks, setRawStocks] = useState(null)
  const [orderMap, setOrderMap] = useState(null)  // Map<"code:market", position>
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [data, { items: order = [] }] = await Promise.all([
        fetchDashboard(),
        fetchWatchlistOrder(),
      ])
      setRawStocks(data.stocks)
      const map = new Map()
      order.forEach(o => map.set(`${o.code}:${o.market}`, o.position))
      setOrderMap(map)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  // 순서 적용
  const stocks = useMemo(() => {
    if (!rawStocks) return null
    if (!orderMap || orderMap.size === 0) return rawStocks
    return [...rawStocks].sort((a, b) => {
      const mktA = a.market || 'KR'
      const mktB = b.market || 'KR'
      const posA = orderMap.get(`${a.code}:${mktA}`) ?? Number.MAX_SAFE_INTEGER
      const posB = orderMap.get(`${b.code}:${mktB}`) ?? Number.MAX_SAFE_INTEGER
      return posA - posB
    })
  }, [rawStocks, orderMap])

  // 드래그앤드롭 순서 변경
  const reorder = useCallback(async (newOrderedStocks) => {
    const map = new Map()
    newOrderedStocks.forEach((s, idx) => map.set(`${s.code}:${s.market || 'KR'}`, idx))
    setOrderMap(map)
    try {
      await saveWatchlistOrder(newOrderedStocks.map(s => ({ code: s.code, market: s.market || 'KR' })))
    } catch (e) {
      console.error('관심종목 순서 저장 실패:', e)
    }
  }, [])

  return { stocks, loading, error, load, reorder }
}

/** 단일 종목 상세 */
export function useStockInfo() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async (code, market = 'KR') => {
    setLoading(true)
    setError(null)
    setData(null)
    try {
      const result = await fetchStockInfo(code, market)
      setData(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    setData(null)
    setError(null)
  }, [])

  return { data, loading, error, load, reset }
}
