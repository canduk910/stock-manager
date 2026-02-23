import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useBalance } from '../hooks/useBalance'
import { useEarnings } from '../hooks/useEarnings'
import { useScreener } from '../hooks/useScreener'
import PortfolioSummary from '../components/balance/PortfolioSummary'
import FilingsTable from '../components/earnings/FilingsTable'
import StockTable from '../components/screener/StockTable'
import LoadingSpinner from '../components/common/LoadingSpinner'
import EmptyState from '../components/common/EmptyState'

function todayKRX() {
  // 오늘 날짜 YYYYMMDD
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}${m}${day}`
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
  const balance = useBalance()
  const earnings = useEarnings()
  const screener = useScreener()

  useEffect(() => {
    const today = todayKRX()
    balance.load()
    earnings.load(today)
    screener.search({ top: 10 })
  }, [])

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">대시보드</h1>

      {/* 잔고 요약 */}
      <section>
        <SectionHeader title="잔고 요약" linkTo="/balance" linkLabel="전체 보기" />
        {balance.loading && <LoadingSpinner message="잔고 조회 중..." />}
        {balance.error && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700">
            KIS API 키가 설정되지 않아 잔고 조회를 사용할 수 없습니다.
            <Link to="/balance" className="ml-2 underline">설정 안내 →</Link>
          </div>
        )}
        {balance.data && !balance.loading && <PortfolioSummary data={balance.data} />}
      </section>

      {/* 오늘 공시 */}
      <section>
        <SectionHeader title="오늘 공시 (최근 5건)" linkTo="/earnings" linkLabel="전체 보기" />
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
      </section>

      {/* 시총 상위 10종목 */}
      <section>
        <SectionHeader title="시가총액 상위 10종목" linkTo="/screener" linkLabel="스크리너 열기" />
        {screener.loading && <LoadingSpinner message="전종목 데이터 수집 중..." />}
        {screener.error && (
          <p className="text-sm text-red-500">{screener.error}</p>
        )}
        {screener.data && !screener.loading && (
          screener.data.stocks.length === 0 ? (
            <EmptyState message="데이터가 없습니다." />
          ) : (
            <StockTable stocks={screener.data.stocks} />
          )
        )}
      </section>
    </div>
  )
}
