/**
 * 전략 선택기 — 프리셋 드롭다운 / 커스텀 YAML 텍스트 에디터.
 */
import { useState } from 'react'

const PRESET_LABELS = {
  sma_crossover: 'SMA 골든/데드 크로스',
  momentum: '모멘텀',
  trend_filter_signal: '추세 필터 + 시그널',
  week52_high: '52주 신고가 돌파',
  ma_divergence: '이격도 평균회귀',
  false_breakout: '돌파 실패 손절',
  short_term_reversal: '단기 반전',
  strong_close: '강한 종가',
  volatility_breakout: '변동성 돌파',
  consecutive_moves: '연속 상승/하락',
}

export default function StrategySelector({ presets, selectedPreset, yamlContent, mode, onModeChange, onPresetChange, onYamlChange }) {
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
              const label = PRESET_LABELS[id] || (typeof p === 'object' ? p.name : id)
              return (
                <option key={id} value={id}>
                  {label}
                </option>
              )
            })}
          </select>
          {selectedPreset && PRESET_LABELS[selectedPreset] && (
            <p className="mt-1 text-xs text-gray-500">{PRESET_LABELS[selectedPreset]}</p>
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
