/**
 * 백테스트 API 클라이언트.
 * MCP 서버 연동 — 프리셋/커스텀 전략 백테스트 실행 + 결과 조회.
 */
import { apiFetch } from './client'

/** MCP 서버 상태 확인 → {available: bool} */
export function fetchMcpStatus() {
  return apiFetch('/api/backtest/status')
}

/** 프리셋 전략 목록 (10개) */
export function fetchPresets() {
  return apiFetch('/api/backtest/presets')
}

/** 기술지표 목록 (80개) */
export function fetchIndicators() {
  return apiFetch('/api/backtest/indicators')
}

/** 프리셋 백테스트 실행 → {job_id, status} */
export function runPresetBacktest(preset, symbol, market = 'KR', startDate, endDate, initialCash = 10000000, params, presetName) {
  const body = {
    preset, symbol, market,
    start_date: startDate || undefined,
    end_date: endDate || undefined,
    initial_cash: initialCash,
  }
  if (params && Object.keys(params).length > 0) body.params = params
  if (presetName) body.preset_name = presetName
  return apiFetch('/api/backtest/run/preset', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

/** 커스텀 YAML 백테스트 실행 → {job_id, status} */
export function runCustomBacktest(yamlContent, symbol, market = 'KR', startDate, endDate, initialCash = 10000000) {
  return apiFetch('/api/backtest/run/custom', {
    method: 'POST',
    body: JSON.stringify({
      yaml_content: yamlContent,
      symbol, market,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      initial_cash: initialCash,
    }),
  })
}

/** 배치 백테스트 (전략 비교) */
export function runBatchBacktest(presets, symbol, market = 'KR', startDate, endDate) {
  return apiFetch('/api/backtest/run/batch', {
    method: 'POST',
    body: JSON.stringify({
      presets, symbol, market,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    }),
  })
}

/** 백테스트 결과 조회 (폴링) → {status, metrics, ...} */
export function fetchBacktestResult(jobId) {
  return apiFetch(`/api/backtest/result/${jobId}`)
}

/** 백테스트 이력 삭제 */
export function deleteBacktestJob(jobId) {
  return apiFetch(`/api/backtest/history/${jobId}`, { method: 'DELETE' })
}

/** 백테스트 이력 조회 → [{job_id, strategy_name, symbol, status, ...}] */
export function fetchBacktestHistory(symbol, market, limit = 20) {
  const params = new URLSearchParams()
  if (symbol) params.set('symbol', symbol)
  if (market) params.set('market', market)
  params.set('limit', String(limit))
  return apiFetch(`/api/backtest/history?${params}`)
}
