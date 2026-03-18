import { useState, useCallback } from 'react'
import MarketBoardCard from './MarketBoardCard'
import AddStockSlot from './AddStockSlot'
import MarketBoardSearchModal from './MarketBoardSearchModal'

const STORAGE_KEY = 'market-board-symbols'
const MAX_STOCKS = 12  // 최대 슬롯 수

function loadStored() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveStored(items) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
}

/**
 * CustomStockSection
 * prices: { [symbol]: { price, change_pct, sign } } (WS 실시간)
 * sparklines: { [code]: [{date, close}] }
 * onNeedSparklines: (items) => void  추가 시 sparkline 요청
 * onSubscribe: (symbols) => void     WS 구독 요청
 * onUnsubscribe: (symbols) => void   WS 구독 해제
 */
export default function CustomStockSection({ prices, sparklines, onNeedSparklines, onSubscribe, onUnsubscribe }) {
  const [stocks, setStocks] = useState(() => loadStored())
  const [showModal, setShowModal] = useState(false)

  const handleAdd = useCallback((item) => {
    setStocks(prev => {
      if (prev.find(s => s.code === item.code && s.market === item.market)) return prev
      const next = [...prev, item]
      saveStored(next)
      onNeedSparklines?.([{ code: item.code, market: item.market }])
      onSubscribe?.([item.code])
      return next
    })
  }, [onNeedSparklines, onSubscribe])

  const handleRemove = useCallback((code, market) => {
    setStocks(prev => {
      const next = prev.filter(s => !(s.code === code && s.market === market))
      saveStored(next)
      onUnsubscribe?.([code])
      return next
    })
  }, [onUnsubscribe])

  return (
    <div>
      <h2 className="text-base font-bold text-gray-300 mb-3">내 관심 종목</h2>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-3">
        {stocks.map(s => (
          <div key={`${s.code}-${s.market}`} className="relative group">
            <MarketBoardCard
              stock={{
                code: s.code,
                name: s.name,
                market_type: s.market,
                price: prices?.[s.code]?.price ?? null,
                change_pct: prices?.[s.code]?.change_pct ?? null,
                mktcap: null,
                year_high: null,
                year_low: null,
              }}
              livePrice={prices?.[s.code]}
              sparkline={sparklines?.[s.code]}
            />
            {/* 삭제 버튼 */}
            <button
              onClick={(e) => { e.stopPropagation(); handleRemove(s.code, s.market) }}
              className="absolute top-1.5 right-1.5 w-5 h-5 rounded-full bg-gray-700 text-gray-400 hover:bg-red-700 hover:text-white text-xs leading-none hidden group-hover:flex items-center justify-center"
            >
              ×
            </button>
          </div>
        ))}

        {stocks.length < MAX_STOCKS && (
          <AddStockSlot onClick={() => setShowModal(true)} />
        )}
      </div>

      {showModal && (
        <MarketBoardSearchModal
          onAdd={handleAdd}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  )
}
