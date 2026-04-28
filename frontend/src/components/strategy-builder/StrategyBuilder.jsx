/**
 * 전략빌더 메인 컨테이너.
 *
 * 5단계 스테퍼 + Step 컴포넌트 + StrategyListPanel 사이드바 + 하단 네비게이션.
 * useStrategyBuilder 훅으로 전체 상태를 관리한다.
 */
import { useCallback, useState } from 'react'
import { useStrategyBuilder } from './useStrategyBuilder'
import StepMetadata from './StepMetadata'
import StepIndicators from './StepIndicators'
import StepConditions from './StepConditions'
import StepRisk from './StepRisk'
import StepPreview from './StepPreview'
import StrategyListPanel from './StrategyListPanel'

const STEPS = [
  { label: '기본 정보', icon: '1' },
  { label: '지표 선택', icon: '2' },
  { label: '진입 조건', icon: '3' },
  { label: '청산 조건', icon: '4' },
  { label: '리스크 + 미리보기', icon: '5' },
]

function Stepper({ currentStep, onGoToStep }) {
  return (
    <div className="flex items-center w-full">
      {STEPS.map((s, idx) => {
        const isComplete = idx < currentStep
        const isCurrent = idx === currentStep
        const isFuture = idx > currentStep

        return (
          <div key={idx} className="flex items-center flex-1 last:flex-none">
            {/* 원형 + 라벨 */}
            <button
              onClick={() => onGoToStep(idx)}
              className="flex flex-col items-center"
              type="button"
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
                  isComplete
                    ? 'bg-blue-600 text-white'
                    : isCurrent
                      ? 'bg-blue-600 text-white ring-4 ring-blue-100'
                      : 'bg-gray-200 text-gray-500'
                }`}
              >
                {isComplete ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  s.icon
                )}
              </div>
              <span
                className={`text-xs mt-1 whitespace-nowrap ${
                  isCurrent
                    ? 'text-blue-600 font-semibold'
                    : 'text-gray-500'
                }`}
              >
                {s.label}
              </span>
            </button>

            {/* 연결선 */}
            {idx < STEPS.length - 1 && (
              <div
                className={`flex-1 h-0.5 mx-2 ${
                  idx < currentStep ? 'bg-blue-600' : 'bg-gray-200'
                }`}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

export default function StrategyBuilder({ onYamlGenerated, onRunSavedStrategy }) {
  const {
    state,
    step,
    yamlPreview,
    validationResult,
    converting,
    saving,
    updateMetadata,
    addIndicator, removeIndicator, updateIndicatorParams,
    addConditionGroup, removeConditionGroup, setGroupOperator,
    addCondition, removeCondition, updateCondition,
    updateRisk,
    convertToYaml,
    save, listSaved, deleteSaved,
    loadPreset,
    nextStep, prevStep, goToStep,
    resetBuilder,
  } = useStrategyBuilder()

  // 리스크 항목 하나라도 활성화되었는지 검사
  const hasRisk = state.risk && Object.values(state.risk).some(r => r?.enabled)

  // 저장 UI 상태
  const [riskError, setRiskError] = useState(false)
  const [showSaveInput, setShowSaveInput] = useState(false)
  const [saveName, setSaveName] = useState('')
  const [saveDesc, setSaveDesc] = useState('')

  const handleSave = useCallback(async () => {
    if (!saveName.trim()) return
    try {
      await save(saveName.trim(), saveDesc.trim())
      setShowSaveInput(false)
    } catch {
      // error handled by parent
    }
  }, [saveName, saveDesc, save])
  const handleConvertYaml = useCallback(async () => {
    if (!hasRisk) {
      setRiskError(true)
      return
    }
    setRiskError(false)
    let yaml = yamlPreview
    if (!yaml) {
      try {
        const res = await convertToYaml(false)
        yaml = res.yaml_content || ''
      } catch {
        return
      }
    }
    if (yaml && onYamlGenerated) {
      onYamlGenerated(yaml, state)
      setSaveName(state.metadata?.name || '')
      setSaveDesc(state.metadata?.description || '')
    }
  }, [yamlPreview, convertToYaml, onYamlGenerated, state, hasRisk])

  // 현재 Step 렌더
  const renderStep = () => {
    switch (step) {
      case 0:
        return (
          <StepMetadata
            metadata={state.metadata}
            onUpdate={updateMetadata}
          />
        )
      case 1:
        return (
          <StepIndicators
            indicators={state.indicators}
            onAdd={addIndicator}
            onRemove={removeIndicator}
            onUpdateParams={updateIndicatorParams}
          />
        )
      case 2:
        return (
          <StepConditions
            mode="entry"
            groups={state.entryGroups}
            indicators={state.indicators}
            onAddGroup={() => addConditionGroup('entry')}
            onRemoveGroup={(groupIdx) => removeConditionGroup('entry', groupIdx)}
            onSetOperator={(groupIdx, op) => setGroupOperator('entry', groupIdx, op)}
            onAddCondition={(groupIdx) => addCondition('entry', groupIdx)}
            onRemoveCondition={(groupIdx, condIdx) => removeCondition('entry', groupIdx, condIdx)}
            onUpdateCondition={(groupIdx, condIdx, data) => updateCondition('entry', groupIdx, condIdx, data)}
          />
        )
      case 3:
        return (
          <StepConditions
            mode="exit"
            groups={state.exitGroups}
            indicators={state.indicators}
            onAddGroup={() => addConditionGroup('exit')}
            onRemoveGroup={(groupIdx) => removeConditionGroup('exit', groupIdx)}
            onSetOperator={(groupIdx, op) => setGroupOperator('exit', groupIdx, op)}
            onAddCondition={(groupIdx) => addCondition('exit', groupIdx)}
            onRemoveCondition={(groupIdx, condIdx) => removeCondition('exit', groupIdx, condIdx)}
            onUpdateCondition={(groupIdx, condIdx, data) => updateCondition('exit', groupIdx, condIdx, data)}
          />
        )
      case 4:
        return (
          <div className="space-y-4">
            <StepRisk
              risk={state.risk}
              onUpdate={(key, val) => { setRiskError(false); updateRisk(key, val) }}
            />
            {riskError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
                손절, 익절, 추적손절 중 최소 1개는 활성화해야 합니다.
              </div>
            )}
            <StepPreview
              state={state}
              yamlPreview={yamlPreview}
              validationResult={validationResult}
            />
          </div>
        )
      default:
        return null
    }
  }

  return (
    <div className="space-y-4">
      {/* 헤더 */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h2 className="text-lg font-bold text-gray-900 mb-4">전략 빌더</h2>
        <Stepper currentStep={step} onGoToStep={goToStep} />
      </div>

      {/* 2컬럼 레이아웃 */}
      <div className="flex gap-4">
        {/* 사이드바 (lg 이상만) */}
        <div className="hidden lg:block w-64 shrink-0">
          <StrategyListPanel
            onLoad={loadPreset}
            onListSaved={listSaved}
            onDeleteSaved={deleteSaved}
            onRunStrategy={onRunSavedStrategy}
          />
        </div>

        {/* 메인 Step */}
        <div className="flex-1 min-w-0">
          {renderStep()}
        </div>
      </div>

      {/* 하단 네비게이션 */}
      <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 flex items-center justify-between">
        <button
          onClick={resetBuilder}
          className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50 transition-colors"
        >
          초기화
        </button>

        <div className="flex items-center gap-2">
          {step > 0 && (
            <button
              onClick={prevStep}
              className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
            >
              이전
            </button>
          )}
          {step < 4 ? (
            <button
              onClick={nextStep}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors"
            >
              다음
            </button>
          ) : (
            <>
              <button
                onClick={handleConvertYaml}
                disabled={converting}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 transition-colors"
              >
                {converting ? '변환 중...' : '전략 완성'}
              </button>
              {yamlPreview && (
                <button
                  onClick={() => setShowSaveInput(v => !v)}
                  disabled={saving}
                  className="px-4 py-2 text-sm font-medium rounded-lg bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 transition-colors"
                >
                  {saving ? '저장 중...' : '전략 저장'}
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* 전략 저장 인라인 입력 */}
      {showSaveInput && (
        <div className="border border-gray-200 rounded-lg p-3 bg-gray-50 space-y-2">
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
              className="px-4 py-2 text-sm font-medium rounded-lg bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 transition-colors"
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
    </div>
  )
}
