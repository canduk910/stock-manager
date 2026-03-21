import { useState, useCallback } from 'react'
import MarketBoardCard from './MarketBoardCard'
import AddStockSlot from './AddStockSlot'
import MarketBoardSearchModal from './MarketBoardSearchModal'

export const MAX_STOCKS = 30  // 별도 등록 종목 최대 수

/**
 * CustomStockSection
 * stocks: { code, market, name, _source: 'watchlist'|'custom' }[]
 *   - watchlist: ★ 배지, X 버튼 없음 (관심종목에서만 삭제 가능)
 *   - custom: X 버튼으로 DB 삭제 가능
 * onAdd(item): custom 종목 추가 (DB 저장)
 * onRemove(code, market): custom 종목 삭제 (DB 삭제)
 */
export default function CustomStockSection({ stocks = [], onAdd, onRemove, prices, sparklines }) {
  const [showModal, setShowModal] = useState(false)

  const handleAdd = useCallback((item) => {
    onAdd?.(item)
    setShowModal(false)
  }, [onAdd])

  const handleRemove = useCallback((code, market) => {
    onRemove?.(code, market)
  }, [onRemove])

  // custom 종목 수만 MAX_STOCKS 한도 체크
  const customCount = stocks.filter(s => s._source === 'custom').length

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <h2 className="text-base font-bold text-gray-300">내 관심 종목</h2>
        <span className="text-xs text-gray-500">
          ★ 관심종목 {stocks.filter(s => s._source === 'watchlist').length}
          {customCount > 0 && ` · 별도 추가 ${customCount}`}
        </span>
      </div>

      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-8 2xl:grid-cols-10 gap-2">
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

            {/* 관심종목 배지 */}
            {s._source === 'watchlist' && (
              <span className="absolute top-1 right-1 text-yellow-400 text-[10px] pointer-events-none">★</span>
            )}

            {/* custom 종목 삭제 버튼 */}
            {s._source === 'custom' && (
              <button
                onClick={(e) => { e.stopPropagation(); handleRemove(s.code, s.market) }}
                className="absolute top-1 right-1 w-4 h-4 rounded-full bg-gray-700 text-gray-400 hover:bg-red-700 hover:text-white text-[10px] leading-none hidden group-hover:flex items-center justify-center"
              >
                ×
              </button>
            )}
          </div>
        ))}

        {customCount < MAX_STOCKS && (
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
