import { useEffect } from 'react'
import { usePortfolio } from '../hooks/usePortfolio'
import { usePortfolioAdvisor } from '../hooks/usePortfolioAdvisor'
import PortfolioSummary from '../components/balance/PortfolioSummary'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorAlert from '../components/common/ErrorAlert'
import RegimeBanner from '../components/portfolio/RegimeBanner'
import AllocationChart from '../components/portfolio/AllocationChart'
import ProfitChart from '../components/portfolio/ProfitChart'
import AdvisorPanel from '../components/advisor/AdvisorPanel'

export default function PortfolioPage({ notify }) {
  const {
    balance, sentiment, loading, error, load,
    allocation, holdings, totalReturn, cashRatio,
  } = usePortfolio()

  const advisor = usePortfolioAdvisor()

  useEffect(() => {
    advisor.loadLatest()
  }, [])

  const isKeyMissing = error && (error.includes('설정되지 않았습니다') || error.includes('503'))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">포트폴리오</h1>
          {totalReturn != null && (
            <p className={`text-sm mt-0.5 ${totalReturn >= 0 ? 'text-red-500' : 'text-blue-500'}`}>
              총 수익률 {totalReturn >= 0 ? '+' : ''}{totalReturn}% · 현금 비중 {cashRatio}%
            </p>
          )}
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="px-4 py-1.5 bg-gray-800 hover:bg-gray-900 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
        >
          새로고침
        </button>
      </div>

      {loading && <LoadingSpinner />}

      {error && !loading && (
        isKeyMissing ? (
          <div className="rounded-xl border border-amber-300 bg-amber-50 p-5 text-sm text-amber-800 space-y-1">
            <p className="font-semibold">KIS API 키가 설정되지 않았습니다</p>
            <p>{error}</p>
            <p className="text-xs text-amber-600 mt-2">
              .env 파일에 KIS_APP_KEY, KIS_APP_SECRET, KIS_ACNT_NO, KIS_ACNT_PRDT_CD_STK를 설정하세요.
            </p>
          </div>
        ) : (
          <ErrorAlert message={error} />
        )
      )}

      {balance && !loading && (
        <div className="space-y-6">
          {/* 매크로 체제 배너 */}
          <RegimeBanner sentiment={sentiment} />

          {/* 자산 현황 요약 */}
          <PortfolioSummary data={balance} />

          {/* 차트: 자산 배분 + 종목별 수익률 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <AllocationChart allocation={allocation} />
            <ProfitChart holdings={holdings} />
          </div>

          {/* AI 포트폴리오 자문 (진단 + 리밸런싱 + 매매실행안 + 이력) */}
          <AdvisorPanel
            balanceData={balance}
            notify={notify}
            advisor={advisor}
            showHistory={true}
          />
        </div>
      )}
    </div>
  )
}
