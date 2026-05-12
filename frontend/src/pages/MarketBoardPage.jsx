import { useEffect, useMemo, useState } from 'react'
import { useMarketBoard, useDisplayStocks, usePricePolling } from '../hooks/useMarketBoard'
import NewHighLowSection from '../components/market-board/NewHighLowSection'
import CustomStockSection from '../components/market-board/CustomStockSection'

export default function MarketBoardPage() {
  const { data, sparklines, ohlc, loading, error, load, loadSparklines } = useMarketBoard()
  const { watchlistStocks, customStocks, displayStocks, loadAll, addStock, removeStock, reorder } = useDisplayStocks()

  // 폴링 대상 코드: 신고가/신저가 + 관심종목 + 별도등록(중복 제거)
  // 시세판 표시 종목은 모두 KR 가정 (해외는 별도 처리 X — 기존 동작 유지)
  const polledCodes = useMemo(() => {
    const set = new Set()
    ;(data?.new_highs || []).forEach(s => set.add(s.code))
    ;(data?.new_lows  || []).forEach(s => set.add(s.code))
    displayStocks.forEach(s => {
      if (s.market === 'KR' || !s.market) set.add(s.code)
    })
    return Array.from(set)
  }, [data, displayStocks])

  const { prices, connected } = usePricePolling(polledCodes, 'KR')

  // 초기 데이터 로드
  useEffect(() => {
    load()
  }, [load])

  // 마운트 시: watchlist + custom stocks 병렬 로드 + sparkline 배치
  useEffect(() => {
    const init = async () => {
      const { watchlist: wl, custom } = await loadAll()
      const allItems = [
        ...wl,
        ...custom.filter(c => !wl.some(w => w.code === c.code && w.market === c.market)),
      ]
      if (allItems.length > 0) {
        loadSparklines(allItems.map(s => ({ code: s.code, market: s.market })))
      }
    }
    init()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // custom 종목 추가 — 스파크라인만 별도 로드 (가격은 다음 폴링 사이클에 자동 반영)
  const handleAddStock = async (item) => {
    try {
      await addStock(item)
      loadSparklines([{ code: item.code, market: item.market }])
    } catch (e) {
      // 중복(409) 등 에러는 무시
    }
  }

  // custom 종목 삭제 — 폴링 코드 셋이 useMemo로 자동 갱신되어 추가 액션 불필요
  const handleRemoveStock = async (code, market) => {
    await removeStock(code, market)
  }

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
          <span className="text-xs text-gray-500">{connected ? '폴링' : '연결 중'}</span>
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
              ohlc={ohlc}
            />
          </div>

          {/* 하단: 관심종목 + 별도 등록 종목 */}
          <div className="bg-gray-900 rounded-2xl p-5">
            <CustomStockSection
              stocks={displayStocks}
              onAdd={handleAddStock}
              onRemove={handleRemoveStock}
              onReorder={reorder}
              prices={prices}
              sparklines={sparklines}
              ohlc={ohlc}
            />
          </div>
        </>
      )}
    </div>
  )
}
