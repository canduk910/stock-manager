import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useDetailReport } from '../hooks/useDetail'
import { useAdvisoryData, useAdvisoryReport } from '../hooks/useAdvisory'
import StockHeader from '../components/detail/StockHeader'
import KLineChartPanel from '../components/detail/KLineChartPanel'
import FinancialTable from '../components/detail/FinancialTable'
import ReportSummary from '../components/detail/ReportSummary'
import FundamentalPanel from '../components/advisory/FundamentalPanel'
import TechnicalPanel from '../components/advisory/TechnicalPanel'
import AIReportPanel from '../components/advisory/AIReportPanel'
import ResearchDataPanel from '../components/advisory/ResearchDataPanel'
import ValuationChart from '../components/detail/ValuationChart'

const TABS = [
  { id: 'financials', label: '재무분석' },
  { id: 'report', label: '종합 리포트' },
]

const REPORT_SUB_TABS = [
  { id: 'cagr',        label: '요약' },
  { id: 'fundamental', label: '기본적 분석' },
  { id: 'technical',   label: '기술적 분석' },
  { id: 'ai',          label: 'AI 자문' },
]

function TabBtn({ id, active, onClick, children }) {
  return (
    <button
      onClick={() => onClick(id)}
      className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
        active
          ? 'border-blue-600 text-blue-600'
          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
      }`}
    >
      {children}
    </button>
  )
}

function SubTabBtn({ id, active, onClick, children }) {
  return (
    <button
      onClick={() => onClick(id)}
      className={`px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
        active
          ? 'border-indigo-500 text-indigo-600'
          : 'border-transparent text-gray-400 hover:text-gray-600 hover:border-gray-300'
      }`}
    >
      {children}
    </button>
  )
}

export default function DetailPage() {
  const { symbol } = useParams()
  const [activeTab, setActiveTab] = useState('financials')
  const [subTab, setSubTab] = useState('cagr')
  const { data, loading, error, load } = useDetailReport()

  const { data: advData, loading: advLoading, error: advError, load: loadAdvData, refresh: refreshAdvData } = useAdvisoryData()
  const { report, history: reportHistory, loading: reportLoading, error: reportError, load: loadReport, generate, loadById: loadReportById } = useAdvisoryReport()
  // advisory 데이터 lazy load: 종합리포트 탭 + cagr 외 서브탭 최초 진입 시
  const advLoadedRef = useRef(false)

  useEffect(() => {
    if (symbol) load(symbol)
  }, [symbol, load])

  useEffect(() => {
    if (activeTab === 'report' && subTab !== 'cagr' && symbol && !advData && !advLoading && !advLoadedRef.current) {
      const market = /^\d{6}$/.test(symbol) ? 'KR' : 'US'
      advLoadedRef.current = true
      loadAdvData(symbol, market)
      loadReport(symbol, market)
    }
  }, [activeTab, subTab, symbol]) // eslint-disable-line

  const market = /^\d{6}$/.test(symbol) ? 'KR' : 'US'

  const handleRefresh = useCallback(() => {
    advLoadedRef.current = true
    refreshAdvData(symbol, market, data?.basic?.name)
  }, [symbol, market, data, refreshAdvData]) // eslint-disable-line

  const handleGenerate = useCallback(async () => {
    await generate(symbol, market)
  }, [symbol, market, generate])

  return (
    <div className="space-y-5">
      {/* 뒤로가기 */}
      <div>
        <Link
          to="/watchlist"
          className="text-sm text-gray-400 hover:text-gray-600 flex items-center gap-1"
        >
          ← 관심종목으로
        </Link>
      </div>

      {loading && (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <div className="inline-block w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-3" />
          <p className="text-sm text-gray-500">
            {symbol} 데이터 수집 중...
          </p>
          <p className="text-xs text-gray-400 mt-1">
            재무 및 밸류에이션 히스토리 조회 중 (첫 조회는 수십 초 소요)
          </p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-5 py-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {data && !loading && (
        <>
          {/* 헤더 */}
          <StockHeader
            symbol={symbol}
            name={data.basic?.name}
            basic={data.basic}
            summary={data.summary}
          />

          {/* 차트 */}
          <KLineChartPanel symbol={symbol} market={market} />

          {/* 탭 네비게이션 */}
          <div className="flex border-b border-gray-200 bg-white rounded-t-xl px-2 pt-2">
            {TABS.map((tab) => (
              <TabBtn
                key={tab.id}
                id={tab.id}
                active={activeTab === tab.id}
                onClick={setActiveTab}
              >
                {tab.label}
              </TabBtn>
            ))}
          </div>

          {/* 탭 컨텐츠 */}
          <div className="mt-0">
            {activeTab === 'financials' && (
              <FinancialTable data={data.financials} basic={data.basic} forward={data.forward_estimates} />
            )}
            {activeTab === 'report' && (
              <div>
                {/* 서브탭 네비게이션 + 액션 버튼 */}
                <div className="flex items-center border-b border-gray-100 bg-white px-3 mb-4">
                  {REPORT_SUB_TABS.map((s) => (
                    <SubTabBtn
                      key={s.id}
                      id={s.id}
                      active={subTab === s.id}
                      onClick={setSubTab}
                    >
                      {s.label}
                    </SubTabBtn>
                  ))}

                  {/* 새로고침/AI분석 버튼: cagr 탭에서는 숨김 */}
                  {subTab !== 'cagr' && (
                    <div className="ml-auto flex gap-2 py-1">
                      <button
                        onClick={handleRefresh}
                        disabled={advLoading}
                        className="px-3 py-1.5 text-xs font-medium rounded border border-gray-300 text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {advLoading ? '수집 중...' : '새로고침'}
                      </button>
                      {subTab === 'ai' && (
                        <button
                          onClick={handleGenerate}
                          disabled={reportLoading}
                          className="px-3 py-1.5 text-xs font-medium rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {reportLoading ? 'AI 분석 중...' : 'AI분석 생성'}
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* 서브탭 콘텐츠 */}
                {subTab === 'cagr' && (
                  <>
                    <ReportSummary data={data} />
                    {data?.valuation?.history?.length > 0 && (
                      <div className="mt-6">
                        <ValuationChart data={data.valuation} />
                      </div>
                    )}
                  </>
                )}
                {subTab === 'fundamental' && (
                  <div className="bg-white rounded-xl border border-gray-200 p-5">
                    {advLoading && (
                      <div className="flex items-center gap-3 py-8 justify-center text-gray-500">
                        <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                        <span className="text-sm">데이터 수집 중...</span>
                      </div>
                    )}
                    {!advLoading && advError && (
                      <p className="text-sm text-red-500 text-center py-8">{advError}</p>
                    )}
                    {!advLoading && !advData && !advError && (
                      <p className="text-sm text-gray-400 text-center py-8">
                        [새로고침] 버튼을 눌러 데이터를 수집해주세요. (30초+ 소요)
                      </p>
                    )}
                    {!advLoading && advData && (
                      <FundamentalPanel data={advData} market={market} code={symbol} />
                    )}
                  </div>
                )}
                {subTab === 'technical' && (
                  <div className="bg-white rounded-xl border border-gray-200 p-5">
                    {advLoading && (
                      <div className="flex items-center gap-3 py-8 justify-center text-gray-500">
                        <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                        <span className="text-sm">데이터 수집 중...</span>
                      </div>
                    )}
                    {!advLoading && advError && (
                      <p className="text-sm text-red-500 text-center py-8">{advError}</p>
                    )}
                    {!advLoading && !advData && !advError && (
                      <p className="text-sm text-gray-400 text-center py-8">
                        [새로고침] 버튼을 눌러 데이터를 수집해주세요. (30초+ 소요)
                      </p>
                    )}
                    {!advLoading && advData && (
                      <TechnicalPanel data={advData} symbol={symbol} market={market} />
                    )}
                  </div>
                )}
                {subTab === 'ai' && (
                  <div className="space-y-4">
                    {/* AI분석 입력 데이터 미리보기 */}
                    <ResearchDataPanel
                      data={advData?.research_data}
                      advData={advData}
                      market={market}
                    />
                    {/* AI 리포트 */}
                    <AIReportPanel
                      report={report}
                      history={reportHistory}
                      loading={reportLoading}
                      error={reportError}
                      onGenerate={handleGenerate}
                      onSelectHistory={(id) => loadReportById(symbol, id, market)}
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
