import { useEffect, useRef } from 'react'
import { useMarketBoard } from '../hooks/useMarketBoard'
import { useMarketBoardWS } from '../hooks/useMarketBoardWS'
import NewHighLowSection from '../components/market-board/NewHighLowSection'
import CustomStockSection from '../components/market-board/CustomStockSection'

export default function MarketBoardPage() {
  const { data, sparklines, loading, error, load, loadSparklines } = useMarketBoard()
  const { prices, connected, subscribe, unsubscribe } = useMarketBoardWS()
  const subscribedRef = useRef(new Set())

  // 초기 데이터 로드
  useEffect(() => {
    load()
  }, [load])

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

  // localStorage에 저장된 사용자 종목도 초기 구독
  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem('market-board-symbols') || '[]')
      const syms = stored.map(s => s.code).filter(s => !subscribedRef.current.has(s))
      if (syms.length > 0) {
        syms.forEach(s => subscribedRef.current.add(s))
        subscribe(syms)
        // sparkline도 로드
        const items = stored.map(s => ({ code: s.code, market: s.market }))
        loadSparklines(items)
      }
    } catch {}
  }, [subscribe, loadSparklines])

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

          {/* 하단: 사용자 선택 종목 */}
          <div className="bg-gray-900 rounded-2xl p-5">
            <CustomStockSection
              prices={prices}
              sparklines={sparklines}
              onNeedSparklines={loadSparklines}
              onSubscribe={subscribe}
              onUnsubscribe={unsubscribe}
            />
          </div>
        </>
      )}
    </div>
  )
}
