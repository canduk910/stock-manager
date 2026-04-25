/**
 * 추가된 지표 카드.
 *
 * 지표명 + 카테고리 배지 + 파라미터 슬라이더 + 삭제 버튼.
 * 파라미터 슬라이더 패턴은 StrategySelector.jsx를 참고.
 */
import { INDICATOR_CATEGORIES } from './strategyBuilderConstants'

const CATEGORY_BADGE_COLORS = {
  moving_average: 'bg-blue-100 text-blue-700',
  momentum:       'bg-orange-100 text-orange-700',
  oscillator:     'bg-purple-100 text-purple-700',
  volatility:     'bg-emerald-100 text-emerald-700',
  trend:          'bg-cyan-100 text-cyan-700',
  volume:         'bg-amber-100 text-amber-700',
  candle_pattern: 'bg-pink-100 text-pink-700',
}

export default function IndicatorCard({ indicator, onUpdateParams, onRemove, catalog }) {
  const def = catalog || {}
  const category = INDICATOR_CATEGORIES[def.category]
  const badgeColor = CATEGORY_BADGE_COLORS[def.category] || 'bg-gray-100 text-gray-700'
  const paramEntries = Object.entries(def.params || {})

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-3 relative">
      {/* 삭제 버튼 (우상단) */}
      <button
        onClick={onRemove}
        className="absolute top-2 right-2 p-1 rounded hover:bg-red-50 text-gray-300 hover:text-red-500 transition-colors"
        title="지표 삭제"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      {/* 헤더 */}
      <div className="flex items-center gap-2 pr-6">
        {category && (
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${badgeColor}`}>
            {category.label}
          </span>
        )}
        <span className="text-sm font-semibold text-gray-900">{def.nameKo || indicator.id}</span>
        <span className="text-xs font-mono text-gray-400 ml-1">({indicator.alias})</span>
      </div>

      {/* 설명 */}
      {def.description && (
        <p className="text-xs text-gray-500 mt-1">{def.description}</p>
      )}

      {/* 파라미터 슬라이더 */}
      {paramEntries.length > 0 && (
        <div className="mt-2 space-y-2 border-t border-gray-100 pt-2">
          {paramEntries.map(([key, spec]) => {
            const currentVal = indicator.params?.[key] ?? spec.default ?? spec.min ?? 0
            const hasRange = spec.min != null && spec.max != null

            return (
              <div key={key} className="flex items-center gap-3">
                <span className="text-xs text-gray-500 w-20 shrink-0">{spec.label || key}</span>
                {hasRange ? (
                  <input
                    type="range"
                    value={currentVal}
                    onChange={(e) => onUpdateParams({ [key]: Number(e.target.value) })}
                    min={spec.min}
                    max={spec.max}
                    step={spec.step ?? 1}
                    className="flex-1 h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
                  />
                ) : null}
                <input
                  type="number"
                  value={currentVal}
                  onChange={(e) => onUpdateParams({ [key]: Number(e.target.value) })}
                  min={spec.min}
                  max={spec.max}
                  step={spec.step}
                  className="w-14 text-right text-xs border border-gray-300 rounded px-1.5 py-0.5 font-mono focus:ring-1 focus:ring-blue-500"
                />
              </div>
            )
          })}
        </div>
      )}

      {/* 파라미터 없는 경우 */}
      {paramEntries.length === 0 && (
        <p className="text-xs text-gray-400 mt-2 italic">파라미터 없음</p>
      )}
    </div>
  )
}
