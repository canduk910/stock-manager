import { useState, useCallback } from 'react'
import { useAsyncState } from './useAsyncState'
import {
  fetchAdvisoryStocks,
  addAdvisoryStock,
  removeAdvisoryStock,
  refreshAdvisoryData,
  fetchAdvisoryData,
  generateReport,
  fetchReport,
  fetchReportHistory,
  fetchReportById,
  fetchAdvisoryOhlcv,
  collectResearchData,
} from '../api/advisory'

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

/** 분석 데이터 새로고침 + 조회 */
export function useAdvisoryData() {
  const { data, setData, loading, error, run } = useAsyncState()

  const load = useCallback(async (code, market) => {
    try {
      await run(() => fetchAdvisoryData(code, market))
    } catch {
      setData(null)
    }
  }, [run, setData])

  const refresh = useCallback(
    (code, market, name = null) => run(() => refreshAdvisoryData(code, market, name)).catch(() => {}),
    [run]
  )

  return { data, loading, error, load, refresh }
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

  const generate = useCallback(async (code, market) => {
    setLoading(true)
    setError(null)
    try {
      const result = await generateReport(code, market)
      setReport(result)
      // 히스토리 갱신
      const h = await fetchReportHistory(code, market)
      setHistory(h)
    } catch (e) {
      setError(e.message)
    } finally {
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

  return { report, history, loading, error, load, generate, loadById }
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
