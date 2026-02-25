import { useEffect, useState } from 'react'
import { useWatchlist, useDashboard } from '../hooks/useWatchlist'
import AddStockForm from '../components/watchlist/AddStockForm'
import WatchlistDashboard from '../components/watchlist/WatchlistDashboard'
import StockInfoModal from '../components/watchlist/StockInfoModal'
import EmptyState from '../components/common/EmptyState'
import ErrorAlert from '../components/common/ErrorAlert'

export default function WatchlistPage() {
  const { items, loading: listLoading, error: listError, load: loadList, add, remove, memo } = useWatchlist()
  const { stocks, loading: dashLoading, error: dashError, load: loadDash } = useDashboard()
  const [modal, setModal] = useState(null) // { code, name, market }

  // 첫 마운트 시 목록 + 대시보드 동시 로드
  useEffect(() => {
    loadList()
    loadDash()
  }, [])

  const handleAdd = async (code, memoText, market) => {
    await add(code, memoText, market)
    loadDash()
  }

  const handleDelete = async (code, market) => {
    await remove(code, market)
    loadDash()
  }

  const handleMemoSave = async (code, text, market) => {
    await memo(code, text, market)
    loadDash()
  }

  const handleRefresh = () => loadDash()

  const totalCount = items?.length ?? 0

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">관심종목</h1>

      <AddStockForm onAdd={handleAdd} />

      <ErrorAlert message={listError || dashError} />

      {/* 빈 상태 */}
      {!listLoading && items?.length === 0 && (
        <EmptyState message="관심종목이 없습니다. 위에서 종목을 추가해보세요." />
      )}

      {/* 대시보드 테이블 */}
      {(items?.length > 0 || dashLoading) && (
        <WatchlistDashboard
          stocks={stocks}
          loading={dashLoading}
          totalCount={totalCount}
          onRefresh={handleRefresh}
          onDelete={handleDelete}
          onMemoSave={handleMemoSave}
          onShowInfo={(code, name, market) => setModal({ code, name, market })}
        />
      )}

      {/* 종목 상세 모달 */}
      {modal && (
        <StockInfoModal
          code={modal.code}
          name={modal.name}
          market={modal.market}
          onClose={() => setModal(null)}
          onMemoSave={handleMemoSave}
        />
      )}
    </div>
  )
}
