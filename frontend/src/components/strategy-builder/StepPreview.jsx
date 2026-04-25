/**
 * Step 5 (미리보기 부분): YAML 출력 + 검증 + 전략 요약 + 저장.
 */
import { useState, useCallback } from 'react'
import { validateYaml } from '../../api/strategyBuilder'
import { INDICATOR_CATALOG } from './strategyBuilderConstants'

function countConditions(groups) {
  return (groups || []).reduce((sum, g) => sum + (g.conditions?.length || 0), 0)
}

export default function StepPreview({
  state,
  yamlPreview,
  validationResult,
  converting,
  onConvert,
  onSave,
  saving,
}) {
  const [copied, setCopied] = useState(false)
  const [showSaveInput, setShowSaveInput] = useState(false)
  const [saveName, setSaveName] = useState(state.metadata?.name || '')
  const [saveDesc, setSaveDesc] = useState(state.metadata?.description || '')
  const [validating, setValidating] = useState(false)
  const [localValidation, setLocalValidation] = useState(null)

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

  const handleValidate = useCallback(async () => {
    if (!yamlPreview) return
    setValidating(true)
    setLocalValidation(null)
    try {
      const res = await validateYaml(yamlPreview)
      setLocalValidation({ valid: res.valid, errors: res.errors || [] })
    } catch (err) {
      setLocalValidation({ valid: false, errors: [err.message] })
    } finally {
      setValidating(false)
    }
  }, [yamlPreview])

  const handleSave = useCallback(async () => {
    if (!saveName.trim()) return
    try {
      await onSave(saveName.trim(), saveDesc.trim())
      setShowSaveInput(false)
    } catch {
      // error handled by parent
    }
  }, [saveName, saveDesc, onSave])

  // 최종 검증 결과: 로컬(검증하기) 우선, 없으면 변환 시 결과
  const vResult = localValidation || validationResult

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

      {/* 액션 버튼 */}
      <div className="flex flex-wrap gap-2 mb-4">
        <button
          onClick={onConvert}
          disabled={converting}
          className="px-4 py-2 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {converting ? 'YAML 변환 중...' : 'YAML 변환'}
        </button>
        <button
          onClick={handleValidate}
          disabled={!yamlPreview || validating}
          className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors"
        >
          {validating ? '검증 중...' : '검증하기'}
        </button>
        <button
          onClick={() => {
            setSaveName(state.metadata?.name || '')
            setSaveDesc(state.metadata?.description || '')
            setShowSaveInput(true)
          }}
          disabled={saving}
          className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors"
        >
          {saving ? '저장 중...' : '전략 저장'}
        </button>
      </div>

      {/* 저장 인라인 입력 */}
      {showSaveInput && (
        <div className="mb-4 border border-gray-200 rounded-lg p-3 bg-gray-50 space-y-2">
          <input
            type="text"
            value={saveName}
            onChange={(e) => setSaveName(e.target.value)}
            placeholder="전략명"
            className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <input
            type="text"
            value={saveDesc}
            onChange={(e) => setSaveDesc(e.target.value)}
            placeholder="설명 (선택)"
            className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={!saveName.trim() || saving}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              저장
            </button>
            <button
              onClick={() => setShowSaveInput(false)}
              className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
            >
              취소
            </button>
          </div>
        </div>
      )}

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
          YAML 변환 버튼을 클릭하면 여기에 결과가 표시됩니다
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
