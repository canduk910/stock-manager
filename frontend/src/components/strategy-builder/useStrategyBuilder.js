/**
 * 전략빌더 상태 관리 훅.
 *
 * 5단계 빌더 워크플로우의 전체 상태를 관리한다:
 *   0. 메타데이터 (전략명, 설명, 카테고리, 태그)
 *   1. 지표 선택 (카탈로그에서 추가/제거/파라미터 조정)
 *   2. 진입 조건 (그룹 + AND/OR 조건 조합)
 *   3. 청산 조건 + 리스크 관리 (손절/익절/추적손절)
 *   4. 미리보기 + YAML 변환 + 저장
 *
 * @see api/strategyBuilder.js
 * @see components/strategy-builder/strategyBuilderConstants.js
 */
import { useState, useCallback } from 'react'
import {
  convertBuilderState,
  saveBuilderStrategy,
  listBuilderStrategies,
  loadBuilderStrategy,
  deleteBuilderStrategy,
} from '../../api/strategyBuilder'

/** @typedef {{ type: 'indicator', alias: string, output: string } | { type: 'price', field: string } | { type: 'number', value: number }} ConditionOperand */
/** @typedef {{ left: ConditionOperand, operator: string, right: ConditionOperand }} Condition */
/** @typedef {{ operator: 'AND'|'OR', conditions: Condition[] }} ConditionGroup */

/**
 * @typedef {object} BuilderState
 * @property {{ name: string, description: string, category: string, tags: string[] }} metadata
 * @property {Array<{ id: string, alias: string, params: Record<string, number>, selectedOutputs: string[] }>} indicators
 * @property {ConditionGroup[]} entryGroups
 * @property {ConditionGroup[]} exitGroups
 * @property {{ stopLoss: { enabled: boolean, percent: number }, takeProfit: { enabled: boolean, percent: number }, trailingStop: { enabled: boolean, percent: number } }} risk
 */

const INITIAL_STATE = {
  metadata: { name: '', description: '', category: 'trend', tags: [] },
  indicators: [],
  entryGroups: [{ operator: 'AND', conditions: [] }],
  exitGroups: [{ operator: 'AND', conditions: [] }],
  risk: {
    stopLoss: { enabled: false, percent: 5.0 },
    takeProfit: { enabled: false, percent: 10.0 },
    trailingStop: { enabled: false, percent: 3.0 },
  },
}

export function useStrategyBuilder() {
  const [state, setState] = useState(INITIAL_STATE)
  const [step, setStep] = useState(0)             // 0~4 (5단계)
  const [yamlPreview, setYamlPreview] = useState('')
  const [validationResult, setValidationResult] = useState(null) // { valid, errors }
  const [converting, setConverting] = useState(false)
  const [saving, setSaving] = useState(false)

  // ── 메타데이터 ──────────────────────────────────────────

  const updateMetadata = useCallback((field, value) => {
    setState(prev => ({
      ...prev,
      metadata: { ...prev.metadata, [field]: value },
    }))
  }, [])

  // ── 지표 ──────────────────────────────────────────────

  /** @param {{ id: string, alias: string, params: Record<string, number>, selectedOutputs: string[] }} indicator */
  const addIndicator = useCallback((indicator) => {
    setState(prev => ({
      ...prev,
      indicators: [...prev.indicators, indicator],
    }))
  }, [])

  const removeIndicator = useCallback((alias) => {
    setState(prev => ({
      ...prev,
      indicators: prev.indicators.filter(i => i.alias !== alias),
    }))
  }, [])

  const updateIndicatorParams = useCallback((alias, params) => {
    setState(prev => ({
      ...prev,
      indicators: prev.indicators.map(i =>
        i.alias === alias ? { ...i, params: { ...i.params, ...params } } : i
      ),
    }))
  }, [])

  // ── 조건 그룹 ──────────────────────────────────────────

  /** @param {'entry'|'exit'} mode */
  const addConditionGroup = useCallback((mode) => {
    const key = mode === 'entry' ? 'entryGroups' : 'exitGroups'
    setState(prev => ({
      ...prev,
      [key]: [...prev[key], { operator: 'AND', conditions: [] }],
    }))
  }, [])

  const removeConditionGroup = useCallback((mode, groupIdx) => {
    const key = mode === 'entry' ? 'entryGroups' : 'exitGroups'
    setState(prev => ({
      ...prev,
      [key]: prev[key].filter((_, i) => i !== groupIdx),
    }))
  }, [])

  const setGroupOperator = useCallback((mode, groupIdx, operator) => {
    const key = mode === 'entry' ? 'entryGroups' : 'exitGroups'
    setState(prev => ({
      ...prev,
      [key]: prev[key].map((g, i) =>
        i === groupIdx ? { ...g, operator } : g
      ),
    }))
  }, [])

  // ── 조건 ──────────────────────────────────────────────

  const addCondition = useCallback((mode, groupIdx) => {
    const key = mode === 'entry' ? 'entryGroups' : 'exitGroups'
    const newCond = {
      left: { type: 'indicator', alias: '', output: 'value' },
      operator: 'greater_than',
      right: { type: 'number', value: 0 },
    }
    setState(prev => ({
      ...prev,
      [key]: prev[key].map((g, i) =>
        i === groupIdx ? { ...g, conditions: [...g.conditions, newCond] } : g
      ),
    }))
  }, [])

  const removeCondition = useCallback((mode, groupIdx, condIdx) => {
    const key = mode === 'entry' ? 'entryGroups' : 'exitGroups'
    setState(prev => ({
      ...prev,
      [key]: prev[key].map((g, i) =>
        i === groupIdx
          ? { ...g, conditions: g.conditions.filter((_, j) => j !== condIdx) }
          : g
      ),
    }))
  }, [])

  /** @param {Partial<Condition>} data — 병합할 조건 필드 */
  const updateCondition = useCallback((mode, groupIdx, condIdx, data) => {
    const key = mode === 'entry' ? 'entryGroups' : 'exitGroups'
    setState(prev => ({
      ...prev,
      [key]: prev[key].map((g, i) =>
        i === groupIdx
          ? {
              ...g,
              conditions: g.conditions.map((c, j) =>
                j === condIdx ? { ...c, ...data } : c
              ),
            }
          : g
      ),
    }))
  }, [])

  // ── 리스크 ──────────────────────────────────────────────

  /** @param {'stopLoss'|'takeProfit'|'trailingStop'} riskType */
  const updateRisk = useCallback((riskType, data) => {
    setState(prev => ({
      ...prev,
      risk: { ...prev.risk, [riskType]: { ...prev.risk[riskType], ...data } },
    }))
  }, [])

  // ── YAML 변환 ──────────────────────────────────────────

  const convertToYaml = useCallback(async (validate = true) => {
    setConverting(true)
    setValidationResult(null)
    try {
      const res = await convertBuilderState(state, validate)
      setYamlPreview(res.yaml_content || '')
      if (res.valid !== undefined && res.valid !== null) {
        setValidationResult({ valid: res.valid, errors: res.errors || [] })
      }
      return res
    } catch (err) {
      setValidationResult({ valid: false, errors: [err.message] })
      throw err
    } finally {
      setConverting(false)
    }
  }, [state])

  // ── 저장/로드 ──────────────────────────────────────────

  const save = useCallback(async (name, description) => {
    setSaving(true)
    try {
      // YAML이 아직 없으면 먼저 변환
      let yaml = yamlPreview
      if (!yaml) {
        const res = await convertBuilderState(state, false)
        yaml = res.yaml_content || ''
        setYamlPreview(yaml)
      }
      return await saveBuilderStrategy(name, description, yaml, state)
    } finally {
      setSaving(false)
    }
  }, [state, yamlPreview])

  const loadSaved = useCallback(async (name) => {
    const s = await loadBuilderStrategy(name)
    if (s.builder_state_json) {
      setState(s.builder_state_json)
      setYamlPreview(s.yaml_content || '')
      setStep(0)
    }
    return s
  }, [])

  const listSaved = useCallback(async () => {
    return await listBuilderStrategies()
  }, [])

  const deleteSaved = useCallback(async (name) => {
    return await deleteBuilderStrategy(name)
  }, [])

  // ── 프리셋 로드 ────────────────────────────────────────

  const loadPreset = useCallback((presetState) => {
    setState(presetState)
    setYamlPreview('')
    setValidationResult(null)
    setStep(0)
  }, [])

  // ── 단계 이동 ──────────────────────────────────────────

  const nextStep = useCallback(() => setStep(s => Math.min(s + 1, 4)), [])
  const prevStep = useCallback(() => setStep(s => Math.max(s - 1, 0)), [])
  const goToStep = useCallback((s) => setStep(s), [])

  // ── 리셋 ──────────────────────────────────────────────

  const resetBuilder = useCallback(() => {
    setState(INITIAL_STATE)
    setStep(0)
    setYamlPreview('')
    setValidationResult(null)
  }, [])

  return {
    state,
    step,
    yamlPreview,
    validationResult,
    converting,
    saving,
    // 메타
    updateMetadata,
    // 지표
    addIndicator, removeIndicator, updateIndicatorParams,
    // 조건 그룹
    addConditionGroup, removeConditionGroup, setGroupOperator,
    // 조건
    addCondition, removeCondition, updateCondition,
    // 리스크
    updateRisk,
    // YAML
    convertToYaml,
    // 저장
    save, loadSaved, listSaved, deleteSaved,
    // 프리셋
    loadPreset,
    // 단계
    nextStep, prevStep, goToStep,
    // 리셋
    resetBuilder,
  }
}
