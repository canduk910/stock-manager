/**
 * Step 3 (진입) / Step 4 (청산): 조건 빌더.
 *
 * mode='entry'이면 진입 조건, mode='exit'이면 청산 조건.
 * 그룹 간에는 OR 관계, 그룹 내에서는 AND/OR 전환 가능.
 */
import ConditionGroupCard from './ConditionGroupCard'

const MODE_CONFIG = {
  entry: {
    title: '진입 조건 설정',
    subtitle: '지표가 이 조건을 만족하면 매수합니다.',
  },
  exit: {
    title: '청산 조건 설정',
    subtitle: '지표가 이 조건을 만족하면 매도합니다.',
  },
}

export default function StepConditions({
  mode,
  groups,
  indicators,
  onAddGroup,
  onRemoveGroup,
  onSetOperator,
  onAddCondition,
  onRemoveCondition,
  onUpdateCondition,
}) {
  const config = MODE_CONFIG[mode] || MODE_CONFIG.entry

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h3 className="text-base font-semibold text-gray-900">{config.title}</h3>
      <p className="text-sm text-gray-500 mt-0.5 mb-4">{config.subtitle}</p>

      {/* 지표 미추가 경고 */}
      {indicators.length === 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-700 mb-4">
          먼저 지표를 추가해주세요 (Step 2)
        </div>
      )}

      {/* 조건 그룹 목록 */}
      <div className="space-y-3">
        {groups.map((group, groupIdx) => (
          <div key={groupIdx}>
            {/* OR 구분자 */}
            {groupIdx > 0 && (
              <div className="flex items-center gap-3 py-2">
                <div className="border-t border-gray-300 flex-1" />
                <span className="text-xs font-bold text-gray-400 bg-white px-2">또는 (OR)</span>
                <div className="border-t border-gray-300 flex-1" />
              </div>
            )}

            <ConditionGroupCard
              group={group}
              mode={mode}
              groupIdx={groupIdx}
              indicators={indicators}
              onSetOperator={(op) => onSetOperator(groupIdx, op)}
              onAddCondition={() => onAddCondition(groupIdx)}
              onRemoveCondition={(condIdx) => onRemoveCondition(groupIdx, condIdx)}
              onUpdateCondition={(condIdx, data) => onUpdateCondition(groupIdx, condIdx, data)}
              onRemoveGroup={() => onRemoveGroup(groupIdx)}
              canRemove={groups.length > 1}
            />
          </div>
        ))}
      </div>

      {/* 그룹 추가 버튼 */}
      <button
        onClick={onAddGroup}
        className="mt-4 border-2 border-dashed border-gray-300 text-gray-400 hover:border-blue-400 hover:text-blue-500 rounded-lg py-3 text-sm w-full transition-colors font-medium"
      >
        + 조건 그룹 추가
      </button>
    </div>
  )
}
