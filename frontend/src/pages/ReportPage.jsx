/**
 * 투자 보고서 페이지 (/reports).
 *
 * 페이지 진입 시 KR/US 파이프라인 자동 실행 (Step 0 중복방지).
 * 매크로 카드는 공유, 섹터 추천은 KR/US 토글로 전환.
 * 하단에 과거 보고서 이력.
 */
import { useEffect, useState, useRef, useCallback } from 'react'
import { useReports, useReportDetail } from '../hooks/useReport'
import { fetchReport } from '../api/report'
import { runPipelineSync } from '../api/pipeline'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorAlert from '../components/common/ErrorAlert'
import ReportDetailView from '../components/report/ReportDetailView'
import ReportHistoryList from '../components/report/ReportHistoryList'

export default function ReportPage() {
  const reports = useReports()
  const [market, setMarket] = useState('KR')
  const [generating, setGenerating] = useState(false)
  const [genError, setGenError] = useState(null)
  const didRun = useRef(false)

  // KR/US 오늘 보고서
  const [krReport, setKrReport] = useState(null)
  const [usReport, setUsReport] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)

  // 이력에서 선택한 보고서 (오늘이 아닌 과거)
  const [historyReport, setHistoryReport] = useState(null)
  const [historyAlt, setHistoryAlt] = useState(null)
  const [activeHistoryId, setActiveHistoryId] = useState(null)

  // 마운트 시 KR/US 파이프라인 병렬 자동 실행
  useEffect(() => {
    if (didRun.current) return
    didRun.current = true

    setGenerating(true)
    setGenError(null)

    Promise.allSettled([
      runPipelineSync('KR'),
      runPipelineSync('US'),
    ]).then(async ([krResult, usResult]) => {
      const krId = krResult.status === 'fulfilled' ? krResult.value.report_id : null
      const usId = usResult.status === 'fulfilled' ? usResult.value.report_id : null

      // 보고서 상세 병렬 로드
      const loads = []
      if (krId) loads.push(fetchReport(krId).then(r => setKrReport(r)).catch(() => {}))
      if (usId) loads.push(fetchReport(usId).then(r => setUsReport(r)).catch(() => {}))
      await Promise.allSettled(loads)

      if (krResult.status === 'rejected' && usResult.status === 'rejected') {
        setGenError('보고서 생성에 실패했습니다.')
      }

      reports.load(undefined, 30)
    }).finally(() => setGenerating(false))
  }, [])

  // 이력에서 보고서 선택
  const handleSelectHistory = useCallback(async (id) => {
    setActiveHistoryId(id)
    setHistoryReport(null)
    setHistoryAlt(null)
    setDetailLoading(true)

    try {
      const r = await fetchReport(id)
      setHistoryReport(r)
      // 같은 날짜의 다른 시장 보고서 찾기
      const items = reports.data?.items || []
      const same = items.find(i => i.date === r.date && i.market !== r.market)
      if (same) {
        const alt = await fetchReport(same.id)
        setHistoryAlt(alt)
      }
      setMarket(r.market || 'KR')
    } catch {
      // ignore
    } finally {
      setDetailLoading(false)
    }
  }, [reports.data])

  // 오늘로 돌아가기
  const handleBackToToday = () => {
    setActiveHistoryId(null)
    setHistoryReport(null)
    setHistoryAlt(null)
    setMarket('KR')
  }

  // 현재 표시할 보고서 결정
  const isHistory = !!activeHistoryId
  const mainReport = isHistory ? historyReport : krReport
  const altReportData = isHistory ? historyAlt : usReport
  const displayLoading = isHistory ? detailLoading : generating

  // 현재 market에 맞는 보고서를 메인으로
  const currentReport = (market === 'US' && altReportData?.market === 'US') ? altReportData
    : (market === 'KR' && altReportData?.market === 'KR') ? altReportData
    : mainReport
  const currentAlt = currentReport === mainReport ? altReportData : mainReport

  const historyItems = reports.data?.items || []

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">투자 보고서</h1>
        {isHistory && (
          <button
            onClick={handleBackToToday}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            오늘 보고서로 돌아가기
          </button>
        )}
      </div>

      {/* 생성 중 */}
      {generating && (
        <div className="flex items-center gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="animate-spin w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full" />
          <span className="text-sm text-blue-700">오늘의 보고서를 생성하고 있습니다...</span>
        </div>
      )}

      {genError && <ErrorAlert message={genError} />}

      {/* 메인 보고서 */}
      {!displayLoading && (
        <ReportDetailView
          report={currentReport}
          altReport={currentAlt}
          market={market}
          onMarketChange={setMarket}
          loading={false}
          error={null}
        />
      )}

      {displayLoading && <LoadingSpinner />}

      {!displayLoading && !currentReport && !genError && (
        <div className="text-center py-12 text-gray-400">
          <p className="text-3xl mb-3">📊</p>
          <p className="text-sm">보고서가 아직 없습니다.</p>
          <p className="text-xs mt-1">잠시 후 자동으로 생성됩니다.</p>
        </div>
      )}

      {/* 과거 이력 */}
      {historyItems.length > 0 && (
        <ReportHistoryList
          items={historyItems}
          activeId={activeHistoryId}
          onSelect={handleSelectHistory}
        />
      )}
    </div>
  )
}
