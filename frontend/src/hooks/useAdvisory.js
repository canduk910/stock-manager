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
} from '../api/advisory'

// fire-and-poll 폴링 설정
const POLL_INTERVAL_MS = 3000
const MAX_POLL_DURATION_MS = 5 * 60 * 1000  // 5분 상한 (refresh + analyze 합산 여유)

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

/** 분석 데이터 새로고침 + 조회 (fire-and-poll 적용 — 504 회피, 진행 메시지) */
export function useAdvisoryData() {
  const { data, setData, loading, error, run } = useAsyncState()
  const [progressMessage, setProgressMessage] = useState(null)
  const cancelledRef = useRef(false)

  // 컴포넌트 언마운트/탭 전환 시 진행 중인 폴링 중단
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

  // fire-and-poll: 즉시 job_id + status 받고 3초 폴링. 504 회피 + 진행 메시지 표시.
  const refresh = useCallback(async (code, market, name = null) => {
    setProgressMessage('데이터 수집 시작 중...')
    try {
      const job = await refreshAdvisoryDataAsync(code, market, name)
      setProgressMessage(job.message || '데이터 수집 중...')

      const startedAt = Date.now()
      const jobId = job.job_id

      // 폴링 루프
      while (!cancelledRef.current) {
        if (Date.now() - startedAt > MAX_POLL_DURATION_MS) {
          setProgressMessage(null)
          throw new Error('데이터 수집이 5분을 초과했습니다. 잠시 후 다시 시도해주세요.')
        }
        await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS))
        const poll = await pollAdvisoryJob(jobId).catch(() => null)
        if (!poll || cancelledRef.current) continue
        if (poll.status === 'running') {
          setProgressMessage(poll.message || `데이터 수집 중... (${poll.elapsed_seconds || 0}초 경과)`)
          continue
        }
        if (poll.status === 'failed') {
          setProgressMessage(null)
          throw new Error(poll.error_message || '데이터 수집 실패')
        }
        if (poll.status === 'completed') {
          setProgressMessage(null)
          setData(poll.result)
          return poll.result
        }
      }
    } catch (e) {
      setProgressMessage(null)
      throw e
    }
  }, [setData])

  return { data, loading, error, load, refresh, progressMessage }
}

/** AI 리포트 생성 + 조회 + 히스토리 */
export function useAdvisoryReport() {
  const [report, setReport] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

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

  // fire-and-poll: 504 회피 + 진행 메시지. progressMessage state로 UI 노출.
  const [progressMessage, setProgressMessage] = useState(null)

  const generate = useCallback(async (code, market, userComment = null) => {
    setLoading(true)
    setError(null)
    setProgressMessage('AI 보고서 생성 시작 중...')
    try {
      // fire-and-poll 모드 — 즉시 job_id 반환 + 3초 폴링
      const job = await generateReportAsync(code, market, userComment)
      setProgressMessage(job.message || 'AI 보고서 생성 중...')

      const startedAt = Date.now()
      const jobId = job.job_id

      let result = null
      while (true) {
        if (Date.now() - startedAt > MAX_POLL_DURATION_MS) {
          throw new Error('AI 보고서 생성이 5분을 초과했습니다. 잠시 후 다시 시도해주세요.')
        }
        await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS))
        const poll = await pollAdvisoryJob(jobId).catch(() => null)
        if (!poll) continue
        if (poll.status === 'running') {
          setProgressMessage(poll.message || `AI 보고서 생성 중... (${poll.elapsed_seconds || 0}초 경과)`)
          continue
        }
        if (poll.status === 'failed') {
          throw new Error(poll.error_message || 'AI 보고서 생성 실패')
        }
        if (poll.status === 'completed') {
          result = poll.result
          break
        }
      }

      setReport(result)
      // 히스토리 갱신
      const h = await fetchReportHistory(code, market)
      setHistory(h)
      try { window.dispatchEvent(new Event('ai-usage-changed')) } catch (_) {}
    } catch (e) {
      setError(e.message)
      try { window.dispatchEvent(new Event('ai-usage-changed')) } catch (_) {}
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

  return { report, history, loading, error, load, generate, loadById, progressMessage }
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
