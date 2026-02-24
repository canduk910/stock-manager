import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useDetailReport } from '../hooks/useDetail'
import StockHeader from '../components/detail/StockHeader'
import FinancialTable from '../components/detail/FinancialTable'
import ValuationChart from '../components/detail/ValuationChart'
import ReportSummary from '../components/detail/ReportSummary'

const TABS = [
  { id: 'financials', label: '재무분석' },
  { id: 'valuation', label: '밸류에이션' },
  { id: 'report', label: '종합 리포트' },
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

export default function DetailPage() {
  const { symbol } = useParams()
  const [activeTab, setActiveTab] = useState('financials')
  const { data, loading, error, load } = useDetailReport()

  useEffect(() => {
    if (symbol) load(symbol)
  }, [symbol, load])

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
              <FinancialTable data={data.financials} />
            )}
            {activeTab === 'valuation' && (
              <ValuationChart data={data.valuation} />
            )}
            {activeTab === 'report' && (
              <ReportSummary data={data} />
            )}
          </div>
        </>
      )}
    </div>
  )
}
