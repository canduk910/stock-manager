import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { useMarketBoard } from '../hooks/useMarketBoard'
import { useMarketBoardWS } from '../hooks/useMarketBoardWS'
import { fetchWatchlist } from '../api/watchlist'
import { fetchCustomStocks, addCustomStock, removeCustomStock } from '../api/marketBoard'
import NewHighLowSection from '../components/market-board/NewHighLowSection'
import CustomStockSection from '../components/market-board/CustomStockSection'

export default function MarketBoardPage() {
  const { data, sparklines, loading, error, load, loadSparklines } = useMarketBoard()
  const { prices, connected, subscribe, unsubscribe } = useMarketBoardWS()
  const subscribedRef = useRef(new Set())

  // 관심종목 + 별도 시세 종목
  const [watchlistStocks, setWatchlistStocks] = useState([])
  const [customStocks, setCustomStocks] = useState([])

  // 표시 목록: watchlist(★) + custom(X), 중복 제거
  const displayStocks = useMemo(() => {
    const wlKeys = new Set(watchlistStocks.map(s => `${s.code}:${s.market}`))
    return [
      ...watchlistStocks.map(s => ({ ...s, _source: 'watchlist' })),
      ...customStocks
        .filter(s => !wlKeys.has(`${s.code}:${s.market}`))
        .map(s => ({ ...s, _source: 'custom' })),
    ]
  }, [watchlistStocks, customStocks])

  // 초기 데이터 로드
  useEffect(() => {
    load()
  }, [load])

  // 마운트 시: watchlist + custom stocks 병렬 로드 → WS 구독 + sparkline
  useEffect(() => {
    const init = async () => {
      try {
        const [{ items: wl = [] }, { items: custom = [] }] = await Promise.all([
          fetchWatchlist(),
          fetchCustomStocks(),
        ])
        setWatchlistStocks(wl)
        setCustomStocks(custom)

        // 전체 종목 WS 구독 + sparkline
        const allItems = [
          ...wl,
          ...custom.filter(c => !wl.some(w => w.code === c.code && w.market === c.market)),
        ]
        const newSyms = allItems.map(s => s.code).filter(c => !subscribedRef.current.has(c))
        if (newSyms.length > 0) {
          newSyms.forEach(c => subscribedRef.current.add(c))
          subscribe(newSyms)
        }
        if (allItems.length > 0) {
          loadSparklines(allItems.map(s => ({ code: s.code, market: s.market })))
        }
      } catch {
        // 조회 실패 시 빈 목록 유지
      }
    }
    init()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 신고가/신저가 종목 WS 구독
  useEffect(() => {
    if (!data) return
    const symbols = [
      ...(data.new_highs || []).map(s => s.code),
      ...(data.new_lows  || []).map(s => s.code),
    ]
    if (symbols.length === 0) return
    const newSyms = symbols.filter(s => !subscribedRef.current.has(s))
    if (newSyms.length === 0) return
    newSyms.forEach(s => subscribedRef.current.add(s))
    subscribe(newSyms)
  }, [data, subscribe])

  // custom 종목 추가
  const handleAddStock = useCallback(async (item) => {
    try {
      await addCustomStock(item.code, item.name, item.market)
      setCustomStocks(prev => {
        if (prev.find(s => s.code === item.code && s.market === item.market)) return prev
        return [...prev, item]
      })
      if (!subscribedRef.current.has(item.code)) {
        subscribedRef.current.add(item.code)
        subscribe([item.code])
      }
      loadSparklines([{ code: item.code, market: item.market }])
    } catch (e) {
      // 중복(409) 등 에러는 무시 (이미 있으면 표시만)
    }
  }, [subscribe, loadSparklines])

  // custom 종목 삭제
  const handleRemoveStock = useCallback(async (code, market) => {
    try {
      await removeCustomStock(code, market)
    } catch {
      // 404 등 무시
    }
    setCustomStocks(prev => prev.filter(s => !(s.code === code && s.market === market)))
    // watchlist에도 없으면 WS unsubscribe
    const inWatchlist = watchlistStocks.some(s => s.code === code && s.market === market)
    const inHighLow = [
      ...(data?.new_highs || []),
      ...(data?.new_lows  || []),
    ].some(s => s.code === code)
    if (!inWatchlist && !inHighLow) {
      subscribedRef.current.delete(code)
      unsubscribe([code])
    }
  }, [watchlistStocks, data, unsubscribe])

  return (
    <div className="space-y-8">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">시세판</h1>
          {data?.updated_at && (
            <p className="text-xs text-gray-400 mt-0.5">
              기준: {new Date(data.updated_at).toLocaleTimeString('ko-KR')}
              {' '}· 스캔 {data.scanned}종목
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400' : 'bg-gray-400'}`} />
          <span className="text-xs text-gray-500">{connected ? '실시간' : '연결 중'}</span>
          <button
            onClick={load}
            disabled={loading}
            className="ml-2 px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg disabled:opacity-40"
          >
            {loading ? '조회 중...' : '새로고침'}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {loading && !data ? (
        <div className="py-20 text-center text-gray-500">
          <div className="w-8 h-8 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm">신고가/신저가 종목 스캔 중...</p>
          <p className="text-xs text-gray-400 mt-1">최초 조회 시 수십 초 소요될 수 있습니다</p>
        </div>
      ) : (
        <>
          {/* 상단: 신고가/신저가 */}
          <div className="bg-gray-900 rounded-2xl p-5">
            <NewHighLowSection
              data={data}
              sparklines={sparklines}
              prices={prices}
            />
          </div>

          {/* 하단: 관심종목 + 별도 등록 종목 */}
          <div className="bg-gray-900 rounded-2xl p-5">
            <CustomStockSection
              stocks={displayStocks}
              onAdd={handleAddStock}
              onRemove={handleRemoveStock}
              prices={prices}
              sparklines={sparklines}
            />
          </div>
        </>
      )}
    </div>
  )
}
