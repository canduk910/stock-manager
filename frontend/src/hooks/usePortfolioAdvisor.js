import { useState, useCallback } from 'react'
import { analyzePortfolio, fetchAdvisorHistory, fetchAdvisorReport } from '../api/advisor'

export function usePortfolioAdvisor() {
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // 이력 목록만 가져옴 (리포트 자동 로드 없음)
  const loadHistory = useCallback(async () => {
    try {
      const h = await fetchAdvisorHistory()
      setHistory(h)
      return h
    } catch {
      return []
    }
  }, [])

  // 최신 리포트 로드 (마운트 시 1회 호출)
  const loadLatest = useCallback(async () => {
    setLoading(true)
    try {
      const h = await fetchAdvisorHistory()
      setHistory(h)
      if (h.length > 0) {
        const latest = await fetchAdvisorReport(h[0].id)
        setResult({
          data: latest.report,
          cached: false,
          analyzed_at: latest.generated_at,
          report_id: latest.id,
        })
      }
    } catch {
      // 이력 로드 실패는 무시
    } finally {
      setLoading(false)
    }
  }, [])

  // 새 분석 실행
  const analyze = useCallback(async (balanceData, forceRefresh = false) => {
    setLoading(true)
    setError(null)
    try {
      const res = await analyzePortfolio(balanceData, forceRefresh)
      setResult(res)
      loadHistory()  // 이력 목록만 갱신 (fire-and-forget, result 덮어쓰기 없음)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [loadHistory])

  // 이력에서 특정 리포트 로드
  const loadById = useCallback(async (reportId) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchAdvisorReport(reportId)
      setResult({
        data: res.report,
        cached: false,
        analyzed_at: res.generated_at,
        report_id: res.id,
      })
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  return { result, history, loading, error, analyze, loadLatest, loadById }
}
