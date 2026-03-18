import { useState } from 'react'
import SymbolSearchBar from '../order/SymbolSearchBar'

/**
 * 종목 추가 모달.
 * onAdd({ code, name, market }) → 호출자에서 추가 처리
 * onClose → 모달 닫기
 */
export default function MarketBoardSearchModal({ onAdd, onClose }) {
  const [market, setMarket] = useState('KR')
  const [selected, setSelected] = useState(null)

  const handleSelect = (item) => {
    setSelected(item)
  }

  const handleAdd = () => {
    if (!selected) return
    onAdd(selected)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-gray-900 rounded-2xl p-6 w-full max-w-md shadow-2xl border border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold text-white">종목 추가</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-xl leading-none">×</button>
        </div>

        <SymbolSearchBar
          market={market}
          onMarketChange={setMarket}
          symbol={selected?.code || ''}
          symbolName={selected?.name || ''}
          onSymbolSelect={handleSelect}
        />

        <div className="mt-4 flex gap-2">
          <button
            onClick={handleAdd}
            disabled={!selected}
            className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-40"
          >
            추가
          </button>
          <button
            onClick={onClose}
            className="flex-1 py-2 bg-gray-700 text-white rounded-lg text-sm hover:bg-gray-600"
          >
            취소
          </button>
        </div>
      </div>
    </div>
  )
}
