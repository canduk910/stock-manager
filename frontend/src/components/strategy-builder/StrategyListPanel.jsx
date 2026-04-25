/**
 * 저장된 전략 목록 + 빌더 프리셋 사이드바.
 *
 * 상단: 내 전략 (서버 저장), 하단: 빌더 프리셋 (정적).
 */
import { useState, useEffect, useCallback } from 'react'
import { BUILDER_PRESETS } from './strategyBuilderConstants'

const CATEGORY_BADGE = {
  trend: 'bg-blue-100 text-blue-700',
  momentum: 'bg-orange-100 text-orange-700',
  mean_reversion: 'bg-purple-100 text-purple-700',
  volatility: 'bg-emerald-100 text-emerald-700',
  composite: 'bg-cyan-100 text-cyan-700',
}

export default function StrategyListPanel({ onLoad, onListSaved, onDeleteSaved, onRunStrategy }) {
  const [savedStrategies, setSavedStrategies] = useState([])
  const [loading, setLoading] = useState(false)

  const loadList = useCallback(async () => {
    setLoading(true)
    try {
      const list = await onListSaved()
      setSavedStrategies(list || [])
    } catch {
      // 조용히 실패
    } finally {
      setLoading(false)
    }
  }, [onListSaved])

  useEffect(() => {
    loadList()
  }, [loadList])

  const handleDelete = useCallback(async (name) => {
    if (!confirm(`"${name}" 전략을 삭제하시겠습니까?`)) return
    try {
      await onDeleteSaved(name)
      setSavedStrategies((prev) => prev.filter((s) => s.name !== name))
    } catch {
      // error
    }
  }, [onDeleteSaved])

  const handleLoadSaved = useCallback((strategy) => {
    if (strategy.builder_state_json) {
      onLoad(strategy.builder_state_json)
    }
  }, [onLoad])

  return (
    <div className="space-y-4">
      {/* 내 전략 */}
      <div className="bg-white border border-gray-200 rounded-lg p-3">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-semibold text-gray-900">
            내 전략 ({savedStrategies.length}개)
          </h4>
          <button
            onClick={loadList}
            className="text-xs text-gray-400 hover:text-blue-500 transition-colors"
            title="새로고침"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>

        {loading ? (
          <p className="text-xs text-gray-400 text-center py-3">불러오는 중...</p>
        ) : savedStrategies.length === 0 ? (
          <p className="text-xs text-gray-400 text-center py-3">저장된 전략이 없습니다</p>
        ) : (
          <div className="space-y-1.5 max-h-60 overflow-y-auto">
            {savedStrategies.map((s) => (
              <div
                key={s.name}
                className="flex items-center justify-between gap-1 px-2 py-1.5 rounded hover:bg-gray-50 group text-xs"
              >
                <div className="flex items-center gap-1.5 min-w-0 flex-1">
                  <span className="font-medium text-gray-800 truncate">{s.name}</span>
                  {s.strategy_type && (
                    <span className="px-1 py-0.5 bg-gray-100 text-gray-500 rounded text-[10px] shrink-0">
                      {s.strategy_type}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                  {s.yaml_content && onRunStrategy && (
                    <button
                      onClick={() => onRunStrategy(s)}
                      className="px-1.5 py-0.5 rounded bg-green-50 text-green-600 hover:bg-green-100 transition-colors"
                    >
                      실행
                    </button>
                  )}
                  {s.builder_state_json && (
                    <button
                      onClick={() => handleLoadSaved(s)}
                      className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors"
                    >
                      로드
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(s.name)}
                    className="px-1.5 py-0.5 rounded bg-red-50 text-red-500 hover:bg-red-100 transition-colors"
                  >
                    삭제
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 빌더 프리셋 */}
      <div className="bg-white border border-gray-200 rounded-lg p-3">
        <h4 className="text-sm font-semibold text-gray-900 mb-2">
          빌더 프리셋 ({BUILDER_PRESETS.length}개)
        </h4>
        <div className="flex flex-wrap gap-1.5">
          {BUILDER_PRESETS.map((preset) => {
            const badgeCls = CATEGORY_BADGE[preset.category] || 'bg-gray-100 text-gray-700'
            return (
              <button
                key={preset.id}
                onClick={() => onLoad(preset.state)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors hover:ring-2 hover:ring-blue-200 ${badgeCls}`}
                title={preset.description}
              >
                {preset.name}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
