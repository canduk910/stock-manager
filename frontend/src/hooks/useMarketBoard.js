import { useState, useCallback, useMemo } from 'react'
import { fetchNewHighsLows, fetchSparklines, fetchCustomStocks, addCustomStock, removeCustomStock, fetchBoardOrder, saveBoardOrder } from '../api/marketBoard'
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


/** 관심종목 + 시세판 별도 등록 종목 관리 + 순서 */
export function useDisplayStocks() {
  const [watchlistStocks, setWatchlistStocks] = useState([])
  const [customStocks, setCustomStocks] = useState([])
  const [orderMap, setOrderMap] = useState(null)  // Map<"code:market", position>
  const [loaded, setLoaded] = useState(false)

  const loadAll = useCallback(async () => {
    try {
      const [{ items: wl = [] }, { items: custom = [] }, { items: order = [] }] = await Promise.all([
        fetchWatchlist(),
        fetchCustomStocks(),
        fetchBoardOrder(),
      ])
      setWatchlistStocks(wl)
      setCustomStocks(custom)
      const map = new Map()
      order.forEach(o => map.set(`${o.code}:${o.market}`, o.position))
      setOrderMap(map)
      setLoaded(true)
      return { watchlist: wl, custom }
    } catch {
      setLoaded(true)
      return { watchlist: [], custom: [] }
    }
  }, [])

  // watchlist + custom 병합 + 순서 적용
  const displayStocks = useMemo(() => {
    const wlKeys = new Set(watchlistStocks.map(s => `${s.code}:${s.market}`))
    const merged = [
      ...watchlistStocks.map(s => ({ ...s, _source: 'watchlist' })),
      ...customStocks
        .filter(s => !wlKeys.has(`${s.code}:${s.market}`))
        .map(s => ({ ...s, _source: 'custom' })),
    ]
    if (!orderMap || orderMap.size === 0) return merged

    return [...merged].sort((a, b) => {
      const posA = orderMap.get(`${a.code}:${a.market}`) ?? Number.MAX_SAFE_INTEGER
      const posB = orderMap.get(`${b.code}:${b.market}`) ?? Number.MAX_SAFE_INTEGER
      return posA - posB
    })
  }, [watchlistStocks, customStocks, orderMap])

  // 드래그앤드롭 순서 변경 (낙관적 업데이트 + 비동기 저장)
  const reorder = useCallback(async (newOrderedStocks) => {
    const map = new Map()
    newOrderedStocks.forEach((s, idx) => map.set(`${s.code}:${s.market}`, idx))
    setOrderMap(map)
    try {
      await saveBoardOrder(newOrderedStocks.map(s => ({ code: s.code, market: s.market })))
    } catch (e) {
      console.error('순서 저장 실패:', e)
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

  return { watchlistStocks, customStocks, displayStocks, loaded, loadAll, addStock, removeStock, reorder }
}
