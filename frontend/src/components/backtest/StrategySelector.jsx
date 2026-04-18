/**
 * 전략 선택기 — 프리셋 드롭다운(상세 설명 카드) / 커스텀 YAML 텍스트 에디터.
 */
import { useMemo } from 'react'

const CATEGORY_LABELS = {
  trend: '추세추종',
  momentum: '모멘텀',
  mean_reversion: '역추세',
  volatility: '변동성',
  composite: '복합',
}

const CATEGORY_COLORS = {
  trend: 'bg-blue-100 text-blue-700',
  momentum: 'bg-orange-100 text-orange-700',
  mean_reversion: 'bg-green-100 text-green-700',
  volatility: 'bg-purple-100 text-purple-700',
  composite: 'bg-indigo-100 text-indigo-700',
}

export default function StrategySelector({ presets, selectedPreset, yamlContent, mode, onModeChange, onPresetChange, onYamlChange }) {
  const presetDetail = useMemo(() => {
    if (!selectedPreset || !presets?.length) return null
    return presets.find((p) => {
      const id = typeof p === 'string' ? p : p.id || p.strategy_id
      return id === selectedPreset
    })
  }, [selectedPreset, presets])

  return (
    <div className="space-y-3">
      {/* 모드 선택 탭 */}
      <div className="flex gap-2">
        <button
          onClick={() => onModeChange('preset')}
          className={`px-4 py-1.5 text-sm rounded font-medium transition-colors ${
            mode === 'preset'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          프리셋 전략
        </button>
        <button
          onClick={() => onModeChange('custom')}
          className={`px-4 py-1.5 text-sm rounded font-medium transition-colors ${
            mode === 'custom'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          커스텀 YAML
        </button>
      </div>

      {mode === 'preset' ? (
        <div>
          <select
            value={selectedPreset}
            onChange={(e) => onPresetChange(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">전략 선택...</option>
            {(presets || []).map((p) => {
              const id = typeof p === 'string' ? p : p.id || p.strategy_id
              const label = typeof p === 'object' ? p.name : id
              return (
                <option key={id} value={id}>
                  {label}
                </option>
              )
            })}
          </select>

          {/* 선택된 전략 상세 설명 카드 */}
          {presetDetail && typeof presetDetail === 'object' && (
            <div className="mt-3 bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm">
              <div className="flex items-center gap-2 mb-2">
                <span className="font-semibold text-gray-900">{presetDetail.name}</span>
                {presetDetail.category && (
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${CATEGORY_COLORS[presetDetail.category] || 'bg-gray-100 text-gray-600'}`}>
                    {CATEGORY_LABELS[presetDetail.category] || presetDetail.category}
                  </span>
                )}
              </div>

              {presetDetail.description && (
                <p className="text-gray-600 mb-3 leading-relaxed">{presetDetail.description}</p>
              )}

              {presetDetail.tags?.length > 0 && (
                <div className="flex gap-1 flex-wrap mb-3">
                  {presetDetail.tags.map((tag) => (
                    <span key={tag} className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded">
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              {presetDetail.params && Object.keys(presetDetail.params).length > 0 && (
                <div className="border-t border-gray-200 pt-2">
                  <p className="text-xs font-medium text-gray-500 mb-1">파라미터</p>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                    {Object.entries(presetDetail.params).map(([key, spec]) => (
                      <div key={key} className="flex justify-between">
                        <span className="text-gray-500">{key}</span>
                        <span className="text-gray-800 font-mono">
                          {spec?.default ?? '-'}
                          {spec?.min != null && spec?.max != null && (
                            <span className="text-gray-400 ml-1">({spec.min}~{spec.max})</span>
                          )}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <textarea
          value={yamlContent}
          onChange={(e) => onYamlChange(e.target.value)}
          placeholder={`version: "1.0"\nmetadata:\n  name: 나의 전략\n  category: trend\nstrategy:\n  id: my_strategy\n  indicators:\n    - id: sma\n      alias: fast_ma\n      params:\n        period: 10\n  entry:\n    conditions:\n      - indicator: fast_ma\n        operator: cross_above\n        value: 0\n    logic: AND\n  exit:\n    conditions:\n      - indicator: fast_ma\n        operator: cross_below\n        value: 0\n    logic: AND`}
          rows={12}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      )}
    </div>
  )
}
