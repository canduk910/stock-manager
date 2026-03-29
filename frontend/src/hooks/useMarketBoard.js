import { useState, useCallback } from 'react'
import { fetchNewHighsLows, fetchSparklines, fetchCustomStocks, addCustomStock, removeCustomStock } from '../api/marketBoard'
import { fetchWatchlist } from '../api/watchlist'

export function useMarketBoard() {
  const [data, setData] = useState(null)   // { new_highs, new_lows, updated_at }
  const [sparklines, setSparklines] = useState({})  // { code: [{date, close}] }
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchNewHighsLows(10)
      setData(result)

      // sparkline 배치 로드 (신고가 + 신저가 종목)
      const allItems = [
        ...(result.new_highs || []).map(s => ({ code: s.code, market: 'KR' })),
        ...(result.new_lows  || []).map(s => ({ code: s.code, market: 'KR' })),
      ]
      // 중복 제거
      const unique = allItems.filter((item, idx, arr) =>
        arr.findIndex(x => x.code === item.code) === idx
      )
      if (unique.length > 0) {
        const sl = await fetchSparklines(unique)
        setSparklines(prev => ({ ...prev, ...sl }))
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const loadSparklines = useCallback(async (items) => {
    if (!items || items.length === 0) return
    try {
      const sl = await fetchSparklines(items)
      setSparklines(prev => ({ ...prev, ...sl }))
    } catch (e) {
      // sparkline 로드 실패는 조용히 무시
    }
  }, [])

  return { data, sparklines, loading, error, load, loadSparklines }
}


/** 관심종목 + 시세판 별도 등록 종목 관리 */
export function useDisplayStocks() {
  const [watchlistStocks, setWatchlistStocks] = useState([])
  const [customStocks, setCustomStocks] = useState([])
  const [loaded, setLoaded] = useState(false)

  const loadAll = useCallback(async () => {
    try {
      const [{ items: wl = [] }, { items: custom = [] }] = await Promise.all([
        fetchWatchlist(),
        fetchCustomStocks(),
      ])
      setWatchlistStocks(wl)
      setCustomStocks(custom)
      setLoaded(true)
      return { watchlist: wl, custom }
    } catch {
      setLoaded(true)
      return { watchlist: [], custom: [] }
    }
  }, [])

  const addStock = useCallback(async (item) => {
    await addCustomStock(item.code, item.name, item.market)
    setCustomStocks(prev => {
      if (prev.find(s => s.code === item.code && s.market === item.market)) return prev
      return [...prev, item]
    })
  }, [])

  const removeStock = useCallback(async (code, market) => {
    try {
      await removeCustomStock(code, market)
    } catch {
      // 404 등 무시
    }
    setCustomStocks(prev => prev.filter(s => !(s.code === code && s.market === market)))
  }, [])

  return { watchlistStocks, customStocks, loaded, loadAll, addStock, removeStock }
}
