/**
 * PC별 loadings 테이블 — 탭(주성분 선택) + 지표별 weight 막대.
 *
 * 절대값 정렬(백엔드에서 이미 정렬됨), 양수=빨강/음수=파랑(한국 관례).
 * 축 의미 회전 대비 — loadings를 항상 노출해 PC 라벨을 재검증 가능하게.
 */
import { useState } from 'react'

export default function FactorLoadingsTable({ loadings, pcLabels }) {
  const data = loadings || []
  const [active, setActive] = useState(0)

  if (data.length === 0) {
    return (
      <div className="text-sm text-gray-500 text-center py-6">
        loadings 데이터 없음
      </div>
    )
  }

  const labelOf = (pc) => (pcLabels && pcLabels[pc]) || `PC${pc}`
  const current = data.find((l) => l.pc === active) || data[0]
  const weights = current?.weights || []
  const maxAbs = Math.max(1e-9, ...weights.map((w) => Math.abs(w.weight)))

  return (
    <div>
      {/* PC 탭 */}
      <div className="flex flex-wrap gap-1 mb-3">
        {data.map((l) => (
          <button
            key={l.pc}
            type="button"
            onClick={() => setActive(l.pc)}
            className={`text-xs px-2 py-1 rounded border transition ${
              l.pc === active
                ? 'bg-violet-600 text-white border-violet-600'
                : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
            }`}
          >
            {labelOf(l.pc)}
            <span className="ml-1 opacity-70">
              {l.explained != null ? `${(l.explained * 100).toFixed(0)}%` : ''}
            </span>
          </button>
        ))}
      </div>

      {/* 지표별 weight 막대 (절대값 정렬) */}
      <div className="space-y-1.5">
        {weights.map((w) => {
          const pct = (Math.abs(w.weight) / maxAbs) * 100
          const positive = w.weight >= 0
          return (
            <div key={w.key} className="flex items-center gap-2 text-xs">
              <span className="w-24 shrink-0 text-gray-600 truncate" title={w.label}>
                {w.label}
              </span>
              {/* 중앙 0 기준 좌(음수, 파랑)/우(양수, 빨강) */}
              <div className="flex-1 flex items-center">
                <div className="w-1/2 flex justify-end">
                  {!positive && (
                    <div
                      className="h-3 bg-blue-500 rounded-l"
                      style={{ width: `${pct}%` }}
                    />
                  )}
                </div>
                <div className="w-px h-4 bg-gray-300" />
                <div className="w-1/2 flex justify-start">
                  {positive && (
                    <div
                      className="h-3 bg-red-500 rounded-r"
                      style={{ width: `${pct}%` }}
                    />
                  )}
                </div>
              </div>
              <span
                className={`w-12 text-right font-medium ${
                  positive ? 'text-red-600' : 'text-blue-600'
                }`}
              >
                {w.weight >= 0 ? '+' : ''}{w.weight.toFixed(2)}
              </span>
            </div>
          )
        })}
      </div>
      <p className="text-[11px] text-gray-400 mt-2">
        ※ 양수(빨강)·음수(파랑) loading. PC 라벨은 경험칙 — 위 weight로 축 의미 재검증.
      </p>
    </div>
  )
}
