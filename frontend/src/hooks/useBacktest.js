/**
 * 백테스트 React 훅 3종.
 *
 * useMcpStatus  — KIS MCP 서버 연결 상태 (GET /api/backtest/status → {available: bool})
 * usePresets    — 프리셋 전략 목록 (GET /api/backtest/presets → 10개 전략)
 * useBacktest   — 백테스트 실행 + 비동기 폴링 + 결과
 *
 * 폴링 패턴 (useBacktest):
 *   1. POST /run/preset 또는 /run/custom → {job_id} 반환
 *   2. setInterval(3초) → GET /result/{job_id} 반복 호출
 *   3. status==="completed" 또는 "failed" → clearInterval
 *   4. 최대 60회(3분) 후 타임아웃 → status="timeout"
 *   5. 컴포넌트 unmount 시 자동 cleanup (useEffect return)
 *
 * 상태 전이: idle → submitting → running → completed/failed/timeout
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { useAsyncState } from './useAsyncState'
import {
  fetchMcpStatus, fetchPresets as fetchPresetsApi,
  runPresetBacktest, runCustomBacktest, runBatchBacktest,
  fetchBacktestResult, fetchBacktestHistory,
} from '../api/backtest'

/** MCP 서버 상태 (1회 조회) */
export function useMcpStatus() {
  const { data, loading, error, run } = useAsyncState({ available: false })
  useEffect(() => { run(() => fetchMcpStatus()).catch(() => {}) }, [run])
  return { available: data?.available ?? false, loading, error }
}

/** 프리셋 전략 목록 */
export function usePresets() {
  const { data, loading, error, run } = useAsyncState([])
  const load = useCallback(() => run(() => fetchPresetsApi()).catch(() => {}), [run])
  return { presets: data || [], loading, error, load }
}

/** 백테스트 실행 + 폴링 */
export function useBacktest() {
  const [jobId, setJobId] = useState(null)
  const [status, setStatus] = useState('idle') // idle | submitting | running | completed | failed | timeout
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [progress, setProgress] = useState(null)
  const intervalRef = useRef(null)
  const pollCountRef = useRef(0)

  // 3초 간격 × 200회 = 최대 10분 대기
  // MCP 백테스트 서버는 비동기 2단계 — 실행 후 결과 대기 최대 5분
  const MAX_POLLS = 200

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    pollCountRef.current = 0
  }, [])

  const startPolling = useCallback((jid) => {
    stopPolling()
    setStatus('running')
    pollCountRef.current = 0

    intervalRef.current = setInterval(async () => {
      pollCountRef.current += 1
      if (pollCountRef.current > MAX_POLLS) {
        stopPolling()
        setStatus('timeout')
        setError('백테스트 시간이 초과되었습니다 (10분). 히스토리에서 결과를 확인하세요.')
        return
      }
      try {
        const res = await fetchBacktestResult(jid)
        if (res.progress) setProgress(res.progress)

        if (res.status === 'completed') {
          stopPolling()
          setResult(res)
          setStatus('completed')
        } else if (res.status === 'failed') {
          stopPolling()
          setError(res.error || '백테스트 실패')
          setStatus('failed')
        }
      } catch (e) {
        // 폴링 에러는 무시 (재시도)
      }
    }, 3000)
  }, [stopPolling])

  // cleanup on unmount
  useEffect(() => () => stopPolling(), [stopPolling])

  const runPreset = useCallback(async (preset, symbol, market, startDate, endDate, initialCash, params, presetName) => {
    setStatus('submitting')
    setResult(null)
    setError(null)
    setProgress(null)
    try {
      const res = await runPresetBacktest(preset, symbol, market, startDate, endDate, initialCash, params, presetName)
      setJobId(res.job_id)
      startPolling(res.job_id)
    } catch (e) {
      setError(e.message)
      setStatus('failed')
    }
  }, [startPolling])

  const runCustom = useCallback(async (yaml, symbol, market, startDate, endDate, initialCash) => {
    setStatus('submitting')
    setResult(null)
    setError(null)
    setProgress(null)
    try {
      const res = await runCustomBacktest(yaml, symbol, market, startDate, endDate, initialCash)
      setJobId(res.job_id)
      startPolling(res.job_id)
    } catch (e) {
      setError(e.message)
      setStatus('failed')
    }
  }, [startPolling])

  const runBatch = useCallback(async (presets, symbol, market, startDate, endDate) => {
    setStatus('submitting')
    setResult(null)
    setError(null)
    setProgress(null)
    try {
      const res = await runBatchBacktest(presets, symbol, market, startDate, endDate)
      setResult(res)
      setStatus('completed')
    } catch (e) {
      setError(e.message)
      setStatus('failed')
    }
  }, [])

  const reset = useCallback(() => {
    stopPolling()
    setJobId(null)
    setStatus('idle')
    setResult(null)
    setError(null)
    setProgress(null)
  }, [stopPolling])

  return {
    jobId, status, result, error, progress,
    runPreset, runCustom, runBatch, reset,
  }
}

/** 백테스트 이력 조회 */
export function useBacktestHistory() {
  const { data, loading, error, run } = useAsyncState([])
  const load = useCallback((symbol, market, limit) => {
    return run(() => fetchBacktestHistory(symbol, market, limit)).catch(() => {})
  }, [run])
  return { history: data || [], loading, error, load }
}
