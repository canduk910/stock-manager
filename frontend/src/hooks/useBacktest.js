/**
 * 백테스트 React 훅.
 *
 * useMcpStatus — MCP 서버 연결 상태
 * usePresets — 프리셋 전략 목록
 * useBacktest — 백테스트 실행 + 3초 폴링 + 결과
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { useAsyncState } from './useAsyncState'
import {
  fetchMcpStatus, fetchPresets as fetchPresetsApi,
  runPresetBacktest, runCustomBacktest, runBatchBacktest,
  fetchBacktestResult,
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

  const MAX_POLLS = 60 // 3초 × 60 = 3분

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
        setError('백테스트 시간이 초과되었습니다 (3분)')
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

  const runPreset = useCallback(async (preset, symbol, market, startDate, endDate, initialCash) => {
    setStatus('submitting')
    setResult(null)
    setError(null)
    setProgress(null)
    try {
      const res = await runPresetBacktest(preset, symbol, market, startDate, endDate, initialCash)
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
