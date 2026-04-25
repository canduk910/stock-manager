/**
 * 개별 조건 행.
 *
 * [left OperandSelector] [연산자 select] [right OperandSelector] [삭제]
 */
import OperandSelector from './OperandSelector'
import { CONDITION_OPERATORS, INDICATOR_CATALOG } from './strategyBuilderConstants'

export default function ConditionCard({ condition, onChange, onRemove, indicators }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-3 flex items-center gap-2">
      {/* left operand */}
      <div className="flex-1 min-w-0">
        <OperandSelector
          value={condition.left}
          onChange={(left) => onChange({ left })}
          indicators={indicators}
          catalog={INDICATOR_CATALOG}
        />
      </div>

      {/* operator */}
      <select
        value={condition.operator || 'greater_than'}
        onChange={(e) => onChange({ operator: e.target.value })}
        className="text-xs border border-gray-300 rounded px-2 py-1.5 min-w-[120px] focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      >
        {CONDITION_OPERATORS.map((op) => (
          <option key={op.value} value={op.value}>{op.label}</option>
        ))}
      </select>

      {/* right operand */}
      <div className="flex-1 min-w-0">
        <OperandSelector
          value={condition.right}
          onChange={(right) => onChange({ right })}
          indicators={indicators}
          catalog={INDICATOR_CATALOG}
        />
      </div>

      {/* delete */}
      <button
        onClick={onRemove}
        className="p-1 rounded hover:bg-red-50 text-gray-300 hover:text-red-500 transition-colors shrink-0"
        title="조건 삭제"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  )
}
