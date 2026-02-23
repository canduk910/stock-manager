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

  const add = useCallback(async (code, memo) => {
    const data = await addToWatchlist(code, memo)
    setItems((prev) => (prev ? [...prev, data.item] : [data.item]))
    return data.item
  }, [])

  const remove = useCallback(async (code) => {
    await removeFromWatchlist(code)
    setItems((prev) => prev?.filter((i) => i.code !== code) ?? [])
  }, [])

  const memo = useCallback(async (code, text) => {
    const data = await updateMemo(code, text)
    setItems((prev) =>
      prev?.map((i) => (i.code === code ? data.item : i)) ?? []
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

  const load = useCallback(async (code) => {
    setLoading(true)
    setError(null)
    setData(null)
    try {
      const result = await fetchStockInfo(code)
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
