import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { usePortfolio } from '../hooks/usePortfolio'
import { useEarnings } from '../hooks/useEarnings'
import PortfolioSummary from '../components/balance/PortfolioSummary'
import RegimeBanner from '../components/portfolio/RegimeBanner'
import AllocationChart from '../components/portfolio/AllocationChart'
import FilingsTable from '../components/earnings/FilingsTable'
import LoadingSpinner from '../components/common/LoadingSpinner'
import EmptyState from '../components/common/EmptyState'

function todayKRX() {
  const d = new Date()
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`
}

function SectionHeader({ title, linkTo, linkLabel }) {
  return (
    <div className="flex items-center justify-between mb-3">
      <h2 className="text-lg font-semibold text-gray-800">{title}</h2>
      {linkTo && (
        <Link to={linkTo} className="text-sm text-blue-600 hover:underline">
          {linkLabel} →
        </Link>
      )}
    </div>
  )
}

export default function DashboardPage() {
  const { isAdmin } = useAuth()
  const {
    balance, sentiment, loading, error,
    allocation, totalReturn, cashRatio,
  } = usePortfolio()

  const earnings = useEarnings()

  useEffect(() => {
    earnings.load(todayKRX())
  }, [])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">대시보드</h1>

      {/* 매크로 체제 배너 */}
      <RegimeBanner sentiment={sentiment} />

      {/* 잔고 요약 (admin only) */}
      {isAdmin && (
        <section>
          <SectionHeader title="자산 현황" linkTo="/portfolio" linkLabel="포트폴리오" />
          {loading && <LoadingSpinner message="잔고 조회 중..." />}
          {error && !loading && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700">
              KIS API 키가 설정되지 않아 잔고 조회를 사용할 수 없습니다.
              <Link to="/balance" className="ml-2 underline">설정 안내 →</Link>
            </div>
          )}
          {balance && !loading && (
            <div className="space-y-4">
              <PortfolioSummary data={balance} />
              {totalReturn != null && (
                <div className="flex gap-4 text-sm text-gray-600">
                  <span>총 수익률 <strong className={totalReturn >= 0 ? 'text-red-500' : 'text-blue-500'}>
                    {totalReturn >= 0 ? '+' : ''}{totalReturn}%
                  </strong></span>
                  <span>현금 비중 <strong>{cashRatio}%</strong></span>
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {/* 자산 배분 + 오늘 공시 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 자산 배분 (admin only) */}
        {isAdmin && allocation.length > 0 && (
          <AllocationChart allocation={allocation} />
        )}

        {/* 오늘 공시 */}
        <div>
          <SectionHeader title="오늘 공시" linkTo="/earnings" linkLabel="전체 보기" />
          {earnings.loading && <LoadingSpinner message="공시 조회 중..." />}
          {earnings.error && (
            <p className="text-sm text-red-500">{earnings.error}</p>
          )}
          {earnings.data && !earnings.loading && (
            earnings.data.filings.length === 0 ? (
              <EmptyState message="오늘 제출된 정기보고서가 없습니다." />
            ) : (
              <FilingsTable filings={earnings.data.filings.slice(0, 5)} />
            )
          )}
        </div>
      </div>
    </div>
  )
}
