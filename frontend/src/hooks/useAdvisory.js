import { useState, useCallback, useEffect, useRef } from 'react'
import { useAsyncState } from './useAsyncState'
import {
  fetchAdvisoryStocks,
  addAdvisoryStock,
  removeAdvisoryStock,
  refreshAdvisoryData,
  refreshAdvisoryDataAsync,
  fetchAdvisoryData,
  generateReport,
  generateReportAsync,
  pollAdvisoryJob,
  fetchReport,
  fetchReportHistory,
  fetchReportById,
  fetchAdvisoryOhlcv,
  collectResearchData,
  fetchStockSupplyDemand,
  fetchForeignHolding,
} from '../api/advisory'
import { saveActiveJob, loadActiveJob, clearActiveJob } from './_advisoryJobPersist'

// fire-and-poll 폴링 설정
const POLL_INTERVAL_MS = 3000
const MAX_POLL_DURATION_MS = 5 * 60 * 1000  // 5분 상한

/**
 * 공용 폴링 루프. submit/resume 양쪽에서 재사용.
 *
 * 완료/실패/취소 모두 localStorage active-job 정리 후 종료.
 * cancelledRef.current=true 시 외부 중단 (페이지 unmount).
 */
async function pollUntilDone({
  jobId, kind, code, market, setProgressMessage, cancelledRef,
}) {
  const labelPrefix = kind === 'refresh' ? '데이터 수집' : 'AI 보고서 생성'
  const startedAt = Date.now()

  while (!cancelledRef.current) {
    if (Date.now() - startedAt > MAX_POLL_DURATION_MS) {
      clearActiveJob(code, market, kind)
      throw new Error(`${labelPrefix}이 5분을 초과했습니다. 잠시 후 다시 시도해주세요.`)
    }
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS))
    const poll = await pollAdvisoryJob(jobId).catch((e) => {
      // 404는 만료(1시간) 또는 권한 — 영속 데이터 정리 후 종료
      if (e?.status === 404) {
        clearActiveJob(code, market, kind)
        return { status: 'expired' }
      }
      return null
    })
    if (!poll || cancelledRef.current) continue
    if (poll.status === 'expired') {
      throw new Error(`${labelPrefix} 작업이 만료되었습니다. 다시 시도해주세요.`)
    }
    if (poll.status === 'running') {
      setProgressMessage(poll.message || `${labelPrefix} 중... (${poll.elapsed_seconds || 0}초 경과)`)
      continue
    }
    if (poll.status === 'failed') {
      clearActiveJob(code, market, kind)
      throw new Error(poll.error_message || `${labelPrefix} 실패`)
    }
    if (poll.status === 'completed') {
      clearActiveJob(code, market, kind)
      return poll.result
    }
  }
  return null
}

/** 자문종목 목록 + CRUD */
export function useAdvisoryStocks() {
  const { data: stocks, loading, error, run } = useAsyncState([])

  const load = useCallback(() => run(() => fetchAdvisoryStocks()).catch(() => {}), [run])

  const add = useCallback(async (code, market, memo = '') => {
    const result = await addAdvisoryStock(code, market, memo)
    await load()
    return result
  }, [load])

  const remove = useCallback(async (code, market) => {
    await removeAdvisoryStock(code, market)
    await load()
  }, [load])

  return { stocks, loading, error, load, add, remove }
}

/**
 * 분석 데이터 새로고침 + 조회 (fire-and-poll + 페이지 이동 후 진행 상태 복원).
 *
 * 마운트 시 localStorage에 진행 중 job 있으면 자동 폴링 재개 → "자문 응답 대기중"
 * 표시 + 새로고침 버튼 비활성화. 사용자가 다른 페이지 갔다 돌아와도 결과 회수 가능.
 */
export function useAdvisoryData() {
  const { data, setData, loading, error, run } = useAsyncState()
  const [progressMessage, setProgressMessage] = useState(null)
  const cancelledRef = useRef(false)

  useEffect(() => {
    cancelledRef.current = false
    return () => { cancelledRef.current = true }
  }, [])

  const load = useCallback(async (code, market) => {
    try {
      await run(() => fetchAdvisoryData(code, market))
    } catch {
      setData(null)
    }
  }, [run, setData])

  const refresh = useCallback(async (code, market, name = null) => {
    setProgressMessage('데이터 수집 시작 중...')
    try {
      const job = await refreshAdvisoryDataAsync(code, market, name)
      saveActiveJob(code, market, 'refresh', job.job_id, job.message)
      setProgressMessage(job.message || '데이터 수집 중...')

      const result = await pollUntilDone({
        jobId: job.job_id, kind: 'refresh', code, market,
        setProgressMessage, cancelledRef,
      })
      setProgressMessage(null)
      if (result) setData(result)
      return result
    } catch (e) {
      setProgressMessage(null)
      throw e
    }
  }, [setData])

  /**
   * 페이지 진입 시 진행 중 작업 복원. localStorage에 active job 있으면 폴링 재개.
   * DetailPage useEffect에서 code/market 결정 후 호출.
   */
  const resumeIfActive = useCallback(async (code, market) => {
    const active = loadActiveJob(code, market, 'refresh')
    if (!active) return false
    setProgressMessage('자문 응답 대기중... (페이지 이동 후 폴링 재개)')
    try {
      const result = await pollUntilDone({
        jobId: active.job_id, kind: 'refresh', code, market,
        setProgressMessage, cancelledRef,
      })
      setProgressMessage(null)
      if (result) setData(result)
      return true
    } catch (e) {
      setProgressMessage(null)
      // 만료/실패는 silent — 사용자가 새로 새로고침 가능
      return false
    }
  }, [setData])

  return { data, loading, error, load, refresh, resumeIfActive, progressMessage }
}

/**
 * AI 리포트 생성 + 조회 + 히스토리 + 페이지 이동 후 진행 상태 복원.
 */
export function useAdvisoryReport() {
  const [report, setReport] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [progressMessage, setProgressMessage] = useState(null)
  const cancelledRef = useRef(false)

  useEffect(() => {
    cancelledRef.current = false
    return () => { cancelledRef.current = true }
  }, [])

  const load = useCallback(async (code, market) => {
    setLoading(true)
    setError(null)
    try {
      const [latestResult, historyResult] = await Promise.allSettled([
        fetchReport(code, market),
        fetchReportHistory(code, market),
      ])
      if (latestResult.status === 'fulfilled') {
        setReport(latestResult.value)
      } else if (latestResult.reason?.status === 404) {
        setReport(null)
      } else {
        setError(latestResult.reason?.message)
      }
      if (historyResult.status === 'fulfilled') {
        setHistory(historyResult.value)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  const generate = useCallback(async (code, market, userComment = null) => {
    setLoading(true)
    setError(null)
    setProgressMessage('AI 보고서 생성 시작 중...')
    try {
      const job = await generateReportAsync(code, market, userComment)
      saveActiveJob(code, market, 'analyze', job.job_id, job.message)
      setProgressMessage(job.message || 'AI 보고서 생성 중...')

      const result = await pollUntilDone({
        jobId: job.job_id, kind: 'analyze', code, market,
        setProgressMessage, cancelledRef,
      })

      if (result) {
        setReport(result)
        // 히스토리 갱신
        const h = await fetchReportHistory(code, market).catch(() => [])
        setHistory(h)
      }
      try { window.dispatchEvent(new Event('ai-usage-changed')) } catch (_) {}
    } catch (e) {
      setError(e.message)
      try { window.dispatchEvent(new Event('ai-usage-changed')) } catch (_) {}
    } finally {
      setProgressMessage(null)
      setLoading(false)
    }
  }, [])

  /**
   * 페이지 진입 시 진행 중 AI 분석 작업 복원. 폴링 재개 + "자문 응답 대기중" 표시.
   * DetailPage useEffect에서 호출.
   */
  const resumeIfActive = useCallback(async (code, market) => {
    const active = loadActiveJob(code, market, 'analyze')
    if (!active) return false
    setLoading(true)
    setError(null)
    setProgressMessage('자문 응답 대기중... (페이지 이동 후 폴링 재개)')
    try {
      const result = await pollUntilDone({
        jobId: active.job_id, kind: 'analyze', code, market,
        setProgressMessage, cancelledRef,
      })
      if (result) {
        setReport(result)
        const h = await fetchReportHistory(code, market).catch(() => [])
        setHistory(h)
      }
      try { window.dispatchEvent(new Event('ai-usage-changed')) } catch (_) {}
      return true
    } catch (e) {
      setError(e.message)
      return false
    } finally {
      setProgressMessage(null)
      setLoading(false)
    }
  }, [])

  const loadById = useCallback(async (code, reportId, market) => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchReportById(code, reportId, market)
      setReport(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  return { report, history, loading, error, load, generate, loadById, resumeIfActive, progressMessage }
}

/** 리서치 데이터 수집 (입력정보 획득) */
export function useResearchData() {
  const { data, loading, error, run } = useAsyncState()
  const collect = useCallback(
    (code, market, name) => run(() => collectResearchData(code, market, name)).catch(() => {}),
    [run]
  )
  return { data, loading, error, collect }
}

/** OHLCV 타임프레임별 데이터 조회 */
export function useAdvisoryOhlcv() {
  const { data: result, loading, error, run } = useAsyncState()
  const load = useCallback(
    (code, market, interval, period) => run(() => fetchAdvisoryOhlcv(code, market, interval, period)).catch(() => {}),
    [run]
  )
  return { result, loading, error, load }
}

/** REQ-SUPPLY-UI-02: 종목 수급. 부분 실패 격리. */
export function useStockSupplyDemand() {
  const { data, loading, error, run } = useAsyncState()
  const load = useCallback(
    (code, days = 30) => run(() => fetchStockSupplyDemand(code, days)).catch(() => {}),
    [run]
  )
  return { data, loading, error, load }
}

/** REQ-FH-UI-01 / REQ-FH-EXT-UI-01: 종목 외국인 보유 추이 + 매수여력.
 *
 * V1.5 → V1.6: days 기본값 30 → 120 (사용자 요구 "반년"). 범위 5~180. 부분 실패 격리.
 */
export function useForeignHolding() {
  const { data, loading, error, run } = useAsyncState()
  const load = useCallback(
    (code, days = 120) => run(() => fetchForeignHolding(code, days)).catch(() => {}),
    [run]
  )
  return { data, loading, error, load }
}
