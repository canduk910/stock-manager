/**
 * 전략빌더 API 클라이언트.
 * 빌더 상태 → YAML 변환, 전략 저장/로드/삭제 등.
 */
import { apiFetch } from './client'

/**
 * 빌더 상태를 KIS YAML로 변환.
 * @param {object} builderState - useStrategyBuilder의 state
 * @param {boolean} [validate=true] - 변환 후 유효성 검증 여부
 * @returns {Promise<{ yaml_content: string, valid: boolean|null, errors: string[] }>}
 */
export function convertBuilderState(builderState, validate = true) {
  return apiFetch('/api/backtest/strategy/convert', {
    method: 'POST',
    body: JSON.stringify({ builder_state: builderState, run_validate: validate }),
  })
}

/**
 * YAML 문자열 유효성 검증.
 * @param {string} yamlContent - KIS YAML 문자열
 * @returns {Promise<{ valid: boolean, errors: string[] }>}
 */
export function validateYaml(yamlContent) {
  return apiFetch('/api/backtest/strategy/validate', {
    method: 'POST',
    body: JSON.stringify({ yaml_content: yamlContent }),
  })
}

/**
 * 빌더 전략 저장.
 * @param {string} name - 전략명
 * @param {string} description - 설명
 * @param {string} yamlContent - 변환된 YAML
 * @param {object} builderState - 빌더 상태 (복원용)
 * @returns {Promise<{ name: string, created_at: string }>}
 */
export function saveBuilderStrategy(name, description, yamlContent, builderState) {
  return apiFetch('/api/backtest/strategies', {
    method: 'POST',
    body: JSON.stringify({
      name,
      description,
      yaml_content: yamlContent,
      builder_state: builderState,
    }),
  })
}

/**
 * 저장된 전략 목록 조회.
 * @param {string} [strategyType] - 필터 ('builder' | 'custom' | 전체)
 * @returns {Promise<Array<{ name: string, description: string, strategy_type: string, created_at: string }>>}
 */
export function listBuilderStrategies(strategyType) {
  const params = new URLSearchParams()
  if (strategyType) params.set('strategy_type', strategyType)
  const qs = params.toString()
  return apiFetch(`/api/backtest/strategies${qs ? `?${qs}` : ''}`)
}

/**
 * 저장된 전략 단건 로드.
 * @param {string} name - 전략명
 * @returns {Promise<{ name: string, description: string, yaml_content: string, builder_state_json: object|null, created_at: string }>}
 */
export function loadBuilderStrategy(name) {
  return apiFetch(`/api/backtest/strategies/${encodeURIComponent(name)}`)
}

/**
 * 저장된 전략 삭제.
 * @param {string} name - 전략명
 * @returns {Promise<{ deleted: boolean }>}
 */
export function deleteBuilderStrategy(name) {
  return apiFetch(`/api/backtest/strategies/${encodeURIComponent(name)}`, {
    method: 'DELETE',
  })
}
