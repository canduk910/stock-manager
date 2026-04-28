/**
 * Step 5 (미리보기 부분): YAML 출력 + 검증 + 전략 요약 + 저장.
 */
import { useState, useCallback } from 'react'
import { INDICATOR_CATALOG } from './strategyBuilderConstants'

function countConditions(groups) {
  return (groups || []).reduce((sum, g) => sum + (g.conditions?.length || 0), 0)
}

export default function StepPreview({
  state,
  yamlPreview,
  validationResult,
}) {
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(async () => {
    if (!yamlPreview) return
    try {
      await navigator.clipboard.writeText(yamlPreview)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // fallback
    }
  }, [yamlPreview])

  const vResult = validationResult

  // 전략 요약
  const indicatorSummary = (state.indicators || []).map((ind) => {
    const def = INDICATOR_CATALOG[ind.id]
    const name = def?.nameKo || ind.id
    const params = Object.values(ind.params || {})
    return params.length > 0 ? `${name}(${params.join(',')})` : name
  }).join(', ')

  const entryCount = countConditions(state.entryGroups)
  const exitCount = countConditions(state.exitGroups)
  const risk = state.risk || {}

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h3 className="text-base font-semibold text-gray-900 mb-4">전략 미리보기</h3>

      {/* 전략 요약 */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-4">
        <p className="text-sm font-medium text-gray-700 mb-1">전략 요약</p>
        <ul className="text-xs text-gray-600 space-y-0.5">
          <li>- 지표: {indicatorSummary || '없음'}</li>
          <li>
            - 진입 조건: {entryCount}개 &nbsp;|&nbsp; 청산 조건: {exitCount}개
          </li>
          <li>
            - 손절: {risk.stopLoss?.enabled ? `${risk.stopLoss.percent}%` : '없음'}
            &nbsp;|&nbsp; 익절: {risk.takeProfit?.enabled ? `${risk.takeProfit.percent}%` : '없음'}
            {risk.trailingStop?.enabled && (
              <> &nbsp;|&nbsp; 추적손절: {risk.trailingStop.percent}%</>
            )}
          </li>
        </ul>
      </div>

      {/* YAML 코드 블록 */}
      {yamlPreview ? (
        <div className="relative mb-4">
          <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 font-mono text-xs overflow-auto max-h-80">
            {yamlPreview}
          </pre>
          <button
            onClick={handleCopy}
            className="absolute top-2 right-2 bg-gray-700 hover:bg-gray-600 text-gray-300 px-2 py-1 rounded text-xs transition-colors"
          >
            {copied ? '복사 완료' : '복사'}
          </button>
        </div>
      ) : (
        <div className="bg-gray-100 rounded-lg p-8 text-center text-sm text-gray-400 mb-4">
          아래 &quot;전략 완성&quot; 버튼을 클릭하면 YAML이 생성됩니다
        </div>
      )}

      {/* 검증 결과 */}
      {vResult && (
        vResult.valid ? (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-green-700 text-sm">
            &#10003; 유효한 전략입니다
          </div>
        ) : (
          <div className="bg-red-50 border border-red-300 rounded-lg p-3 text-red-700 text-sm">
            &#10007; 검증 실패
            {vResult.errors?.length > 0 && (
              <ul className="mt-1 list-disc list-inside text-xs">
                {vResult.errors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            )}
          </div>
        )
      )}
    </div>
  )
}
