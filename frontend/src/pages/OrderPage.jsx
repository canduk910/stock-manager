/**
 * 주문 페이지.
 * 탭: 주문 발송 / 미체결 / 체결 내역 / 주문 이력 / 예약주문
 *
 * URL 파라미터: ?symbol=&market=&side= (잔고 페이지에서 연계)
 */
import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import OrderForm from '../components/order/OrderForm'
import OrderConfirmModal from '../components/order/OrderConfirmModal'
import OpenOrdersTable from '../components/order/OpenOrdersTable'
import ExecutionsTable from '../components/order/ExecutionsTable'
import OrderHistoryTable from '../components/order/OrderHistoryTable'
import ReservationForm from '../components/order/ReservationForm'
import ReservationsTable from '../components/order/ReservationsTable'
import SyncButton from '../components/order/SyncButton'
import ErrorAlert from '../components/common/ErrorAlert'
import LoadingSpinner from '../components/common/LoadingSpinner'
import {
  useOrderPlace,
  useOpenOrders,
  useExecutions,
  useOrderHistory,
  useOrderSync,
  useReservations,
} from '../hooks/useOrder'

const TABS = [
  { key: 'order', label: '주문 발송' },
  { key: 'open', label: '미체결' },
  { key: 'executions', label: '체결 내역' },
  { key: 'history', label: '주문 이력' },
  { key: 'reservation', label: '예약주문' },
]

const MARKET_TABS = [
  { key: 'KR', label: '국내' },
  { key: 'US', label: '미국' },
]

export default function OrderPage({ notify }) {
  const [searchParams] = useSearchParams()
  const [activeTab, setActiveTab] = useState('order')
  const [market, setMarket] = useState('KR')
  const [pendingOrder, setPendingOrder] = useState(null)

  // 잔고 페이지 연계: URL 파라미터에서 기본값 읽기
  const defaultValues = {
    symbol: searchParams.get('symbol') || '',
    symbol_name: searchParams.get('symbol_name') || '',
    market: searchParams.get('market') || 'KR',
    side: searchParams.get('side') || 'buy',
    price: searchParams.get('price') || '',
    quantity: searchParams.get('quantity') || '',
  }

  const { loading: placing, error: placeError, place } = useOrderPlace()
  const { orders: openOrders, loading: openLoading, error: openError, load: loadOpen, modify, cancel } = useOpenOrders()
  const { executions, loading: execLoading, error: execError, load: loadExec } = useExecutions()
  const { orders: history, loading: histLoading, error: histError, load: loadHistory } = useOrderHistory()
  const { result: syncResult, loading: syncLoading, sync } = useOrderSync()
  const { reservations, loading: resLoading, error: resError, load: loadReservations, create: createRes, remove: removeRes } = useReservations()

  // 탭 변경 시 데이터 로드
  useEffect(() => {
    if (activeTab === 'open') loadOpen(market)
    if (activeTab === 'executions') loadExec(market)
    if (activeTab === 'history') loadHistory({})
    if (activeTab === 'reservation') loadReservations()
  }, [activeTab, market])

  // 주문 확인 모달 → 발송
  const handleConfirmOrder = async (order) => {
    try {
      await place(order)
      setPendingOrder(null)
      notify?.(`주문 발송 완료: ${order.symbol_name || order.symbol} ${order.side === 'buy' ? '매수' : '매도'} ${order.quantity}주`, 'success')
    } catch (e) {
      notify?.(e.message, 'error')
    }
  }

  // 미체결 취소
  const handleCancelOrder = async (order) => {
    try {
      await cancel(order.order_no, {
        org_no: order.org_no,
        market: order.market,
        order_type: order.order_type,
        quantity: Number(order.remaining_qty || order.quantity),
        total: true,
      })
      notify?.(`취소 요청: ${order.symbol_name || order.symbol}`, 'info')
      loadOpen(market)
    } catch (e) {
      notify?.(e.message, 'error')
    }
  }

  // 미체결 정정
  const handleModifyOrder = async (orderNo, body) => {
    try {
      await modify(orderNo, body)
      notify?.('정정 요청 완료', 'success')
      loadOpen(market)
    } catch (e) {
      notify?.(e.message, 'error')
    }
  }

  // 동기화
  const handleSync = async () => {
    const result = await sync()
    if (result?.synced > 0) {
      notify?.(`${result.synced}건 상태 갱신됨`, 'success')
    }
  }

  // 예약주문 등록
  const handleCreateReservation = async (body) => {
    try {
      await createRes(body)
      notify?.(`예약주문 등록: ${body.symbol}`, 'success')
    } catch (e) {
      notify?.(e.message, 'error')
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-gray-900">주문</h1>

      {/* 탭 */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-1">
          {TABS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px ${
                activeTab === key
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* 국내/미국 탭 (주문 발송 제외) */}
      {activeTab !== 'order' && activeTab !== 'history' && activeTab !== 'reservation' && (
        <div className="flex gap-2">
          {MARKET_TABS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setMarket(key)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                market === key
                  ? 'bg-gray-800 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {/* 주문 발송 탭 */}
      {activeTab === 'order' && (
        <div className="max-w-lg">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-4">주문 입력</h2>
            <OrderForm
              defaultValues={defaultValues}
              onConfirm={(body) => setPendingOrder(body)}
            />
            {placeError && <ErrorAlert message={placeError} className="mt-3" />}
          </div>
        </div>
      )}

      {/* 미체결 탭 */}
      {activeTab === 'open' && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">
              {openOrders ? `${openOrders.length}건` : ''}
            </span>
            <div className="flex items-center gap-2">
              <SyncButton onSync={handleSync} loading={syncLoading} result={syncResult} />
              <button
                onClick={() => loadOpen(market)}
                className="px-3 py-1.5 text-sm border border-gray-300 rounded text-gray-600 hover:bg-gray-50"
              >
                새로고침
              </button>
            </div>
          </div>
          {openLoading ? <LoadingSpinner /> : openError ? <ErrorAlert message={openError} /> : (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <OpenOrdersTable
                orders={openOrders}
                onRefresh={() => loadOpen(market)}
                onCancel={handleCancelOrder}
                onModify={handleModifyOrder}
              />
            </div>
          )}
        </div>
      )}

      {/* 체결 내역 탭 */}
      {activeTab === 'executions' && (
        <div className="space-y-3">
          <div className="flex justify-end">
            <button
              onClick={() => loadExec(market)}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded text-gray-600 hover:bg-gray-50"
            >
              새로고침
            </button>
          </div>
          {execLoading ? <LoadingSpinner /> : execError ? <ErrorAlert message={execError} /> : (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <ExecutionsTable executions={executions} />
            </div>
          )}
        </div>
      )}

      {/* 주문 이력 탭 */}
      {activeTab === 'history' && (
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          {histLoading ? <LoadingSpinner /> : histError ? <ErrorAlert message={histError} /> : (
            <OrderHistoryTable
              orders={history}
              onFilter={(filters) => loadHistory(filters)}
            />
          )}
        </div>
      )}

      {/* 예약주문 탭 */}
      {activeTab === 'reservation' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-4">예약주문 등록</h2>
            <ReservationForm onSubmit={handleCreateReservation} />
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <h2 className="text-base font-semibold text-gray-900 mb-4">예약주문 목록</h2>
            {resLoading ? <LoadingSpinner /> : resError ? <ErrorAlert message={resError} /> : (
              <ReservationsTable reservations={reservations} onDelete={removeRes} />
            )}
          </div>
        </div>
      )}

      {/* 주문 확인 모달 */}
      {pendingOrder && (
        <OrderConfirmModal
          order={pendingOrder}
          onConfirm={handleConfirmOrder}
          onCancel={() => setPendingOrder(null)}
          loading={placing}
        />
      )}
    </div>
  )
}
