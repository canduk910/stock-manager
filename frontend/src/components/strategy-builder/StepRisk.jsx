/**
 * Step 5 (리스크 부분): 손절/익절/추적손절 설정.
 *
 * 각 리스크 항목은 토글 + 슬라이더로 구성.
 */

const RISK_ITEMS = [
  {
    key: 'stopLoss',
    label: '손절 (Stop Loss)',
    description: (pct) => `진입가 대비 -${pct.toFixed(1)}% 하락 시 자동 매도`,
    borderColor: 'border-l-red-400',
    min: 0.5,
    max: 20,
    step: 0.5,
  },
  {
    key: 'takeProfit',
    label: '익절 (Take Profit)',
    description: (pct) => `진입가 대비 +${pct.toFixed(1)}% 상승 시 자동 매도`,
    borderColor: 'border-l-green-400',
    min: 1,
    max: 50,
    step: 0.5,
  },
  {
    key: 'trailingStop',
    label: '추적손절 (Trailing Stop)',
    description: (pct) => `최고점 대비 -${pct.toFixed(1)}% 하락 시 자동 매도`,
    borderColor: 'border-l-blue-400',
    min: 0.5,
    max: 10,
    step: 0.5,
  },
]

function Toggle({ enabled, onChange }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!enabled)}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors cursor-pointer ${
        enabled ? 'bg-blue-600' : 'bg-gray-200'
      }`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 rounded-full bg-white transform transition-transform ${
          enabled ? 'translate-x-4' : 'translate-x-0.5'
        }`}
      />
    </button>
  )
}

export default function StepRisk({ risk, onUpdate }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h3 className="text-base font-semibold text-gray-900 mb-4">리스크 관리</h3>

      <div className="space-y-4">
        {RISK_ITEMS.map((item) => {
          const data = risk?.[item.key] || { enabled: false, percent: item.min }
          const enabled = data.enabled
          const percent = data.percent ?? item.min

          return (
            <div
              key={item.key}
              className={`border-l-4 ${item.borderColor} bg-gray-50/50 rounded-lg p-4`}
            >
              {/* 헤더: 라벨 + 토글 */}
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-gray-700">{item.label}</span>
                <Toggle
                  enabled={enabled}
                  onChange={(val) => onUpdate(item.key, { enabled: val })}
                />
              </div>

              {/* 설명 */}
              <p className="text-xs text-gray-500 mb-3">{item.description(percent)}</p>

              {/* 슬라이더 + 값 */}
              <div className={`flex items-center gap-3 ${!enabled ? 'opacity-50 pointer-events-none' : ''}`}>
                <input
                  type="range"
                  value={percent}
                  onChange={(e) => onUpdate(item.key, { percent: Number(e.target.value) })}
                  min={item.min}
                  max={item.max}
                  step={item.step}
                  className="flex-1 h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
                />
                <span className="text-sm font-mono text-gray-700 w-14 text-right">
                  {percent.toFixed(1)}%
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
