import { useScreener } from '../hooks/useScreener'
import FilterPanel from '../components/screener/FilterPanel'
import StockTable from '../components/screener/StockTable'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorAlert from '../components/common/ErrorAlert'
import EmptyState from '../components/common/EmptyState'

export default function ScreenerPage() {
  const { data, loading, error, search } = useScreener()

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">종목 스크리너</h1>

      <div className="grid grid-cols-[280px_1fr] gap-6 items-start">
        <FilterPanel onSearch={search} loading={loading} />

        <div className="space-y-3">
          {loading && (
            <LoadingSpinner message="전종목 데이터 수집 중... (첫 조회는 수십 초 소요될 수 있습니다)" />
          )}
          <ErrorAlert message={error} />

          {data && !loading && (
            <>
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-500">
                  <span className="font-semibold text-gray-800">{data.total.toLocaleString()}종목</span> 조회됨
                  {data.date && ` (${data.date.slice(0, 4)}-${data.date.slice(4, 6)}-${data.date.slice(6)})`}
                </p>
              </div>
              {data.stocks.length === 0 ? (
                <EmptyState message="조건에 맞는 종목이 없습니다." />
              ) : (
                <StockTable stocks={data.stocks} />
              )}
            </>
          )}

          {!data && !loading && !error && (
            <EmptyState message="필터를 설정하고 '조회하기'를 눌러주세요." />
          )}
        </div>
      </div>
    </div>
  )
}
