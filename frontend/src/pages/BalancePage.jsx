import { useEffect } from 'react'
import { useBalance } from '../hooks/useBalance'
import PortfolioSummary from '../components/balance/PortfolioSummary'
import HoldingsTable from '../components/balance/HoldingsTable'
import OverseasHoldingsTable from '../components/balance/OverseasHoldingsTable'
import FuturesTable from '../components/balance/FuturesTable'
import LoadingSpinner from '../components/common/LoadingSpinner'
import EmptyState from '../components/common/EmptyState'

export default function BalancePage() {
  const { data, loading, error, load } = useBalance()

  useEffect(() => {
    load()
  }, [])

  const isKeyMissing = error && (error.includes('설정되지 않았습니다') || error.includes('503'))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">잔고 조회</h1>
        <button
          onClick={load}
          disabled={loading}
          className="px-4 py-1.5 bg-gray-800 hover:bg-gray-900 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
        >
          새로고침
        </button>
      </div>

      {loading && <LoadingSpinner />}

      {error && (
        isKeyMissing ? (
          <div className="rounded-xl border border-amber-300 bg-amber-50 p-5 text-sm text-amber-800 space-y-1">
            <p className="font-semibold">KIS API 키가 설정되지 않았습니다</p>
            <p>{error}</p>
            <p className="text-xs text-amber-600 mt-2">
              .env 파일에 KIS_APP_KEY, KIS_APP_SECRET, KIS_ACNT_NO, KIS_ACNT_PRDT_CD를 설정하면 잔고 조회를 사용할 수 있습니다.
            </p>
          </div>
        ) : (
          <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-700">
            <span className="font-semibold">오류: </span>{error}
          </div>
        )
      )}

      {data && !loading && (
        <div className="space-y-8">
          <PortfolioSummary data={data} />

          {/* 국내주식 */}
          <div>
            <h2 className="text-lg font-semibold text-gray-800 mb-3">국내주식</h2>
            {data.stock_list.length === 0 ? (
              <EmptyState message="보유 중인 국내주식이 없습니다." />
            ) : (
              <HoldingsTable stocks={data.stock_list} />
            )}
          </div>

          {/* 해외주식 */}
          {data.overseas_list && data.overseas_list.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-gray-800 mb-3">해외주식</h2>
              <OverseasHoldingsTable stocks={data.overseas_list} />
            </div>
          )}

          {/* 국내선물옵션 */}
          {data.futures_list && data.futures_list.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-gray-800 mb-3">국내선물옵션</h2>
              <FuturesTable positions={data.futures_list} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}