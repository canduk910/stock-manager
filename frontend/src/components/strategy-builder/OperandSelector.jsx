/**
 * 조건 카드의 피연산자(left/right) 선택기.
 *
 * 3가지 타입: indicator(지표출력), price(가격), number(숫자).
 * indicator 선택 시 alias + output 2단계 셀렉트, price는 PRICE_FIELDS, number는 입력.
 */
import { useMemo } from 'react'
import { INDICATOR_CATALOG, PRICE_FIELDS } from './strategyBuilderConstants'

const TYPE_OPTIONS = [
  { value: 'indicator', label: '지표출력' },
  { value: 'price', label: '가격' },
  { value: 'number', label: '숫자' },
]

const selectCls = 'text-xs border border-gray-300 rounded px-2 py-1.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500'

export default function OperandSelector({ value, onChange, indicators, catalog }) {
  const cat = catalog || INDICATOR_CATALOG

  // alias -> outputs 매핑
  const aliasOutputs = useMemo(() => {
    const map = {}
    for (const ind of indicators || []) {
      const def = cat[ind.id]
      if (def) {
        map[ind.alias] = def.outputs || []
      }
    }
    return map
  }, [indicators, cat])

  const handleTypeChange = (newType) => {
    if (newType === 'indicator') {
      const first = indicators?.[0]
      const alias = first?.alias || ''
      const outputs = alias ? (aliasOutputs[alias] || ['value']) : ['value']
      onChange({ type: 'indicator', alias, output: outputs[0] || 'value' })
    } else if (newType === 'price') {
      onChange({ type: 'price', field: 'close' })
    } else {
      onChange({ type: 'number', value: value?.value ?? 0 })
    }
  }

  const handleAliasChange = (alias) => {
    const outputs = aliasOutputs[alias] || ['value']
    onChange({ type: 'indicator', alias, output: outputs[0] || 'value' })
  }

  return (
    <div className="flex items-center gap-1.5">
      {/* 타입 셀렉트 */}
      <select
        value={value?.type || 'indicator'}
        onChange={(e) => handleTypeChange(e.target.value)}
        className={`${selectCls} min-w-[80px]`}
      >
        {TYPE_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>

      {/* 타입별 값 입력 */}
      {value?.type === 'indicator' && (
        <>
          <select
            value={value.alias || ''}
            onChange={(e) => handleAliasChange(e.target.value)}
            className={`${selectCls} min-w-[90px]`}
          >
            <option value="">지표 선택</option>
            {(indicators || []).map((ind) => (
              <option key={ind.alias} value={ind.alias}>{ind.alias}</option>
            ))}
          </select>
          <select
            value={value.output || 'value'}
            onChange={(e) => onChange({ ...value, output: e.target.value })}
            className={`${selectCls} min-w-[80px]`}
          >
            {(aliasOutputs[value.alias] || ['value']).map((out) => (
              <option key={out} value={out}>{out}</option>
            ))}
          </select>
        </>
      )}

      {value?.type === 'price' && (
        <select
          value={value.field || 'close'}
          onChange={(e) => onChange({ ...value, field: e.target.value })}
          className={`${selectCls} min-w-[80px]`}
        >
          {PRICE_FIELDS.map((pf) => (
            <option key={pf.value} value={pf.value}>{pf.label}</option>
          ))}
        </select>
      )}

      {value?.type === 'number' && (
        <input
          type="number"
          value={value.value ?? 0}
          onChange={(e) => onChange({ ...value, value: Number(e.target.value) })}
          className="w-24 text-xs border border-gray-300 rounded px-2 py-1.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      )}
    </div>
  )
}
