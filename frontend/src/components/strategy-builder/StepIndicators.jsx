/**
 * Step 2: 지표 선택 및 파라미터 설정.
 *
 * 추가된 지표 목록을 IndicatorCard로 렌더하고,
 * IndicatorPickerModal로 카탈로그에서 새 지표를 추가한다.
 */
import { useState, useCallback, useMemo } from 'react'
import IndicatorCard from './IndicatorCard'
import IndicatorPickerModal from './IndicatorPickerModal'
import { INDICATOR_CATALOG } from './strategyBuilderConstants'

export default function StepIndicators({ indicators, onAdd, onRemove, onUpdateParams }) {
  const [showPicker, setShowPicker] = useState(false)

  // IndicatorPickerModal의 onSelect는 { id, nameKo, ... } 전체 def를 전달
  const handleSelect = useCallback((indicatorDef) => {
    const id = indicatorDef.id
    const def = INDICATOR_CATALOG[id]
    if (!def) return

    // 자동 alias: id_N (기존 같은 id 개수 기반)
    const existingCount = indicators.filter((i) => i.id === id).length
    const alias = `${id}_${existingCount + 1}`

    // 기본 파라미터
    const params = {}
    for (const [key, spec] of Object.entries(def.params || {})) {
      params[key] = spec.default ?? spec.min ?? 0
    }

    onAdd({
      id,
      alias,
      params,
      selectedOutputs: [...(def.outputs || [])],
    })
    setShowPicker(false)
  }, [indicators, onAdd])

  // 이미 추가된 지표 ID Set (모달에서 표시용)
  const existingIds = useMemo(() => new Set(indicators.map((i) => i.id)), [indicators])

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-semibold text-gray-900">
          지표 설정
        </h3>
        {indicators.length > 0 && (
          <span className="text-xs text-gray-500">추가된 지표 ({indicators.length}개)</span>
        )}
      </div>

      {/* 지표 카드 목록 */}
      {indicators.length > 0 ? (
        <div className="space-y-3 mb-4">
          {indicators.map((ind) => (
            <IndicatorCard
              key={ind.alias}
              indicator={ind}
              catalog={INDICATOR_CATALOG[ind.id]}
              onUpdateParams={(params) => onUpdateParams(ind.alias, params)}
              onRemove={() => onRemove(ind.alias)}
            />
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-400 text-center py-8">
          지표를 추가하여 전략 조건에 사용하세요
        </p>
      )}

      {/* 지표 추가 버튼 */}
      <button
        onClick={() => setShowPicker(true)}
        className="border-2 border-dashed border-gray-300 text-gray-400 hover:border-blue-400 hover:text-blue-500 rounded-lg py-3 text-sm w-full transition-colors font-medium"
      >
        + 지표 추가
      </button>

      {/* 지표 선택 모달 */}
      <IndicatorPickerModal
        isOpen={showPicker}
        onClose={() => setShowPicker(false)}
        onSelect={handleSelect}
        existingIds={existingIds}
      />
    </div>
  )
}
