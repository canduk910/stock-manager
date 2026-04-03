import { useState, useCallback } from 'react'
import { analyzePortfolio, fetchAdvisorHistory, fetchAdvisorReport } from '../api/advisor'

export function usePortfolioAdvisor() {
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadHistory = useCallback(async () => {
    try {
      const h = await fetchAdvisorHistory()
      setHistory(h)
      // 현재 표시 중인 결과가 없고, 이력이 있으면 최신 리포트 자동 로드
      if (!result && h.length > 0) {
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
    }
  }, [result])

  const analyze = useCallback(async (balanceData, forceRefresh = false) => {
    setLoading(true)
    setError(null)
    try {
      const res = await analyzePortfolio(balanceData, forceRefresh)
      setResult(res)
      await loadHistory()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [loadHistory])

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

  return { result, history, loading, error, analyze, loadHistory, loadById }
}
