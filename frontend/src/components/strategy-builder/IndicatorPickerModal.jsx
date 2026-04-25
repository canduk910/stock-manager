/**
 * 지표 선택 모달.
 *
 * 카테고리별 아코디언 + 검색 필터.
 * INDICATOR_CATALOG에서 지표를 선택하면 onSelect 콜백 호출 후 모달을 닫는다.
 */
import { useState, useMemo } from 'react'
import { INDICATOR_CATALOG, INDICATOR_CATEGORIES } from './strategyBuilderConstants'

export default function IndicatorPickerModal({ isOpen, onClose, onSelect, existingAliases, existingIds }) {
  const [search, setSearch] = useState('')
  const [expandedCategories, setExpandedCategories] = useState({})

  // 카테고리별 지표 그룹핑 + 검색 필터 (hooks는 early return 전에 호출)
  const categorized = useMemo(() => {
    const query = search.trim().toLowerCase()
    const groups = {}

    for (const [id, def] of Object.entries(INDICATOR_CATALOG)) {
      if (query) {
        const match =
          def.nameKo.toLowerCase().includes(query) ||
          def.nameEn.toLowerCase().includes(query) ||
          id.toLowerCase().includes(query)
        if (!match) continue
      }

      const cat = def.category || 'etc'
      if (!groups[cat]) groups[cat] = []
      groups[cat].push({ id, ...def })
    }

    return groups
  }, [search])

  // 카테고리 순서 (INDICATOR_CATEGORIES 순서 따름)
  const categoryOrder = Object.keys(INDICATOR_CATEGORIES)

  if (!isOpen) return null

  const toggleCategory = (cat) => {
    setExpandedCategories((prev) => ({ ...prev, [cat]: !prev[cat] }))
  }

  const handleSelect = (indicatorDef) => {
    onSelect(indicatorDef)
    setSearch('')
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 헤더 */}
        <div className="px-4 py-3 border-b flex items-center justify-between shrink-0">
          <h2 className="text-lg font-bold text-gray-900">지표 추가</h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* 검색바 */}
        <div className="sticky top-0 bg-white px-4 py-3 border-b shrink-0">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="지표 검색..."
            className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            autoFocus
          />
        </div>

        {/* 카테고리 목록 */}
        <div className="overflow-y-auto flex-1 px-4 py-2">
          {categoryOrder.map((cat) => {
            const items = categorized[cat]
            if (!items || items.length === 0) return null
            const catMeta = INDICATOR_CATEGORIES[cat]
            const isExpanded = expandedCategories[cat] ?? (!!search) // 검색 중이면 자동 펼침

            return (
              <div key={cat} className="mb-1">
                {/* 카테고리 헤더 */}
                <button
                  onClick={() => toggleCategory(cat)}
                  className="flex items-center justify-between cursor-pointer py-2 hover:bg-gray-50 rounded px-2 w-full text-left"
                >
                  <div className="flex items-center gap-2">
                    <svg
                      className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    <span className="text-sm font-semibold text-gray-700">{catMeta?.label || cat}</span>
                    <span className="px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-gray-100 text-gray-500">
                      {items.length}
                    </span>
                  </div>
                </button>

                {/* 지표 목록 */}
                {isExpanded && (
                  <div className="ml-2 mb-2">
                    {items.map((ind) => {
                      const alreadyAdded = existingIds?.has?.(ind.id)
                      return (
                        <div
                          key={ind.id}
                          onClick={() => !alreadyAdded && handleSelect(ind)}
                          className={`flex items-center justify-between px-3 py-2 rounded-lg transition-colors ${
                            alreadyAdded
                              ? 'opacity-50 cursor-default'
                              : 'hover:bg-blue-50 cursor-pointer'
                          }`}
                        >
                          <div className="flex items-center gap-1.5 min-w-0">
                            <span className="text-sm text-gray-800">{ind.nameKo}</span>
                            <span className="text-xs text-gray-400">{ind.nameEn}</span>
                          </div>
                          {alreadyAdded ? (
                            <span className="text-xs text-gray-400 shrink-0">추가됨</span>
                          ) : (
                            <span className="text-blue-500 text-xs font-medium shrink-0">+ 추가</span>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}

          {/* 검색 결과 없음 */}
          {Object.keys(categorized).length === 0 && (
            <p className="text-sm text-gray-400 text-center py-8">검색 결과가 없습니다</p>
          )}
        </div>
      </div>
    </div>
  )
}
