import { useState, useCallback } from 'react'
import {
  fetchWatchlist,
  addToWatchlist,
  removeFromWatchlist,
  updateMemo,
  fetchDashboard,
  fetchStockInfo,
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

/** 대시보드 데이터 */
export function useDashboard() {
  const [stocks, setStocks] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchDashboard()
      setStocks(data.stocks)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  return { stocks, loading, error, load }
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
