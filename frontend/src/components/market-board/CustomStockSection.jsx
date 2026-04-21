import { useState, useCallback } from 'react'
import {
  DndContext,
  closestCenter,
  PointerSensor,
  TouchSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import {
  SortableContext,
  rectSortingStrategy,
  useSortable,
  arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import MarketBoardCard from './MarketBoardCard'
import AddStockSlot from './AddStockSlot'
import MarketBoardSearchModal from './MarketBoardSearchModal'

export const MAX_STOCKS = 30  // 별도 등록 종목 최대 수

function SortableCardWrapper({ id, stock, prices, sparklines, ohlc, onRemove }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 50 : 'auto',
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`relative group ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
      {...attributes}
      {...listeners}
    >
      <MarketBoardCard
        stock={{
          code: stock.code,
          name: stock.name,
          market_type: stock.market,
          price: prices?.[stock.code]?.price ?? null,
          change_pct: prices?.[stock.code]?.change_pct ?? null,
          mktcap: null,
          year_high: null,
          year_low: null,
        }}
        livePrice={prices?.[stock.code]}
        sparkline={sparklines?.[stock.code]}
        ohlc={ohlc?.[stock.code]}
      />

      {/* 관심종목 배지 */}
      {stock._source === 'watchlist' && (
        <span className="absolute top-1 right-1 text-yellow-400 text-[10px] pointer-events-none">★</span>
      )}

      {/* custom 종목 삭제 버튼 */}
      {stock._source === 'custom' && (
        <button
          onClick={(e) => { e.stopPropagation(); onRemove(stock.code, stock.market) }}
          onPointerDown={(e) => e.stopPropagation()}
          className="absolute top-1 right-1 w-4 h-4 rounded-full bg-gray-700 text-gray-400 hover:bg-red-700 hover:text-white text-[10px] leading-none hidden group-hover:flex items-center justify-center"
        >
          ×
        </button>
      )}
    </div>
  )
}

/**
 * CustomStockSection
 * stocks: { code, market, name, _source: 'watchlist'|'custom' }[]
 * onAdd(item): custom 종목 추가 (DB 저장)
 * onRemove(code, market): custom 종목 삭제 (DB 삭제)
 * onReorder(newOrderedStocks): 순서 변경 콜백
 */
export default function CustomStockSection({ stocks = [], onAdd, onRemove, onReorder, prices, sparklines, ohlc }) {
  const [showModal, setShowModal] = useState(false)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 5 },
    }),
    useSensor(TouchSensor, {
      activationConstraint: { delay: 200, tolerance: 5 },
    }),
  )

  const handleAdd = useCallback((item) => {
    onAdd?.(item)
    setShowModal(false)
  }, [onAdd])

  const handleRemove = useCallback((code, market) => {
    onRemove?.(code, market)
  }, [onRemove])

  const handleDragEnd = useCallback((event) => {
    const { active, over } = event
    if (!over || active.id === over.id) return

    const oldIndex = stocks.findIndex(s => `${s.code}:${s.market}` === active.id)
    const newIndex = stocks.findIndex(s => `${s.code}:${s.market}` === over.id)
    if (oldIndex === -1 || newIndex === -1) return

    const newOrder = arrayMove(stocks, oldIndex, newIndex)
    onReorder?.(newOrder)
  }, [stocks, onReorder])

  const sortableIds = stocks.map(s => `${s.code}:${s.market}`)
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

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={sortableIds} strategy={rectSortingStrategy}>
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-8 2xl:grid-cols-10 gap-2">
            {stocks.map(s => (
              <SortableCardWrapper
                key={`${s.code}-${s.market}`}
                id={`${s.code}:${s.market}`}
                stock={s}
                prices={prices}
                sparklines={sparklines}
                ohlc={ohlc}
                onRemove={handleRemove}
              />
            ))}

            {customCount < MAX_STOCKS && (
              <AddStockSlot onClick={() => setShowModal(true)} />
            )}
          </div>
        </SortableContext>
      </DndContext>

      {showModal && (
        <MarketBoardSearchModal
          onAdd={handleAdd}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  )
}
