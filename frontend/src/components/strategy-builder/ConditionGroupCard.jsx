/**
 * 조건 그룹 카드.
 *
 * 여러 ConditionCard를 AND/OR 연산자로 묶는 컨테이너.
 * entry(진입)는 blue, exit(청산)는 red 좌측 보더.
 */
import ConditionCard from './ConditionCard'

const MODE_LABELS = {
  entry: '진입 조건',
  exit: '청산 조건',
}

const BORDER_COLORS = {
  entry: 'border-l-blue-400',
  exit: 'border-l-red-400',
}

export default function ConditionGroupCard({
  group,
  mode,
  groupIdx,
  indicators,
  onSetOperator,
  onAddCondition,
  onRemoveCondition,
  onUpdateCondition,
  onRemoveGroup,
  canRemove,
}) {
  const borderColor = BORDER_COLORS[mode] || 'border-l-gray-400'
  const label = `${MODE_LABELS[mode] || mode} 그룹 #${groupIdx + 1}`

  return (
    <div className={`rounded-lg p-3 space-y-2 border-l-4 ${borderColor} bg-gray-50/50`}>
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-semibold text-gray-700">{label}</span>
        <div className="flex items-center gap-2">
          {/* AND/OR 토글 */}
          <select
            value={group.operator || 'AND'}
            onChange={(e) => onSetOperator(e.target.value)}
            className="text-xs border border-gray-300 rounded px-2 py-1 font-medium focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="AND">AND</option>
            <option value="OR">OR</option>
          </select>
          {/* 그룹 삭제 */}
          {canRemove && (
            <button
              onClick={onRemoveGroup}
              className="p-1.5 rounded hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors text-xs"
              title="그룹 삭제"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* 조건들 */}
      {group.conditions.map((cond, condIdx) => (
        <div key={condIdx}>
          {/* AND/OR 구분선 (첫 번째 이후) */}
          {condIdx > 0 && (
            <div className="flex items-center gap-2 py-1">
              <div className="border-t border-gray-200 flex-1" />
              <span className="text-xs font-bold text-gray-400">{group.operator}</span>
              <div className="border-t border-gray-200 flex-1" />
            </div>
          )}
          <ConditionCard
            condition={cond}
            onChange={(data) => onUpdateCondition(condIdx, data)}
            onRemove={() => onRemoveCondition(condIdx)}
            indicators={indicators}
          />
        </div>
      ))}

      {/* 빈 상태 메시지 */}
      {group.conditions.length === 0 && (
        <p className="text-xs text-gray-400 text-center py-2">조건을 추가하세요</p>
      )}

      {/* 조건 추가 버튼 */}
      <button
        onClick={onAddCondition}
        className="border border-dashed border-gray-300 text-gray-400 hover:border-blue-400 hover:text-blue-500 rounded-lg py-2 text-sm w-full transition-colors"
      >
        + 조건 추가
      </button>
    </div>
  )
}
