import { useState, useCallback } from 'react'
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
} from '../api/advisory'

/** 자문종목 목록 + CRUD */
export function useAdvisoryStocks() {
  const [stocks, setStocks] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchAdvisoryStocks()
      setStocks(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

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
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async (code, market) => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchAdvisoryData(code, market)
      setData(result)
    } catch (e) {
      setError(e.message)
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [])

  const refresh = useCallback(async (code, market, name = null) => {
    setLoading(true)
    setError(null)
    try {
      const result = await refreshAdvisoryData(code, market, name)
      setData(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

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

/** OHLCV 타임프레임별 데이터 조회 */
export function useAdvisoryOhlcv() {
  const [result, setResult] = useState(null)  // { ohlcv, indicators, interval, period }
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async (code, market, interval, period) => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchAdvisoryOhlcv(code, market, interval, period)
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  return { result, loading, error, load }
}
