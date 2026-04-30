/**
 * 주문 페이지 (/order).
 *
 * 5탭 UI: 주문발송 / 미체결 / 체결내역 / 주문이력 / 예약주문
 *
 * 핵심 설계:
 *   - **공유 상태**: symbol/symbolName/market 3개를 최상단에서 관리하여 모든 탭이 공유
 *   - **URL 파라미터**: ?symbol=&market=&side= — 잔고 페이지 HoldingsTable의 매수/매도 버튼에서 연계
 *   - **isMounted ref**: StrictMode 중복 렌더링 시 초기 API 호출 방지
 *   - **자동 폴링**: 미체결/체결 탭 10초 간격 (setInterval)
 *   - **체결통보 WS**: useExecutionNotice 훅이 H0STCNI0 체결통보 수신 시 토스트 + 자동 갱신
 *   - **주문 후 딜레이**: 주문 발송 → 3초 대기 후 미체결/체결 자동 갱신 (KIS API 반영 지연)
 *
 * 레이아웃 (주문발송 탭):
 *   - xl 이상: 좌측=호가창(OrderbookPanel) + 우측=주문폼(OrderForm) 2컬럼
 *   - xl 미만: 주문폼만 단일 컬럼
 *   - 호가 클릭 → externalPrice/externalSide → OrderForm에 자동 입력
 *
 * MARKET_TABS (미체결/체결/주문이력): KR / US / FNO 3개 시장 탭
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import OrderForm from '../components/order/OrderForm'
import OrderbookPanel from '../components/order/OrderbookPanel'
import OrderConfirmModal from '../components/order/OrderConfirmModal'
import OpenOrdersTable from '../components/order/OpenOrdersTable'
import ModifyOrderModal from '../components/order/ModifyOrderModal'
import ExecutionsTable from '../components/order/ExecutionsTable'
import OrderHistoryTable from '../components/order/OrderHistoryTable'
import ReservationForm from '../components/order/ReservationForm'
import ReservationsTable from '../components/order/ReservationsTable'
import SyncButton from '../components/order/SyncButton'
import PriceChartPanel from '../components/order/PriceChartPanel'
import SymbolSearchBar from '../components/order/SymbolSearchBar'
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
import { useExecutionNotice } from '../hooks/useExecutionNotice'

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
  { key: 'FNO', label: '선물옵션' },
]

export default function OrderPage({ notify }) {
  const [searchParams] = useSearchParams()
  const [activeTab, setActiveTab] = useState('order')
  const [market, setMarket] = useState(searchParams.get('market') || 'KR')
  const [pendingOrder, setPendingOrder] = useState(null)

  // ── 공유 종목 상태 (검색바 + 호가창 + 주문폼 + 차트 공통) ──────────────
  const [symbol, setSymbol] = useState(searchParams.get('symbol') || '')
  const [symbolName, setSymbolName] = useState(searchParams.get('symbol_name') || '')

  // 잔고 페이지 연계: URL 파라미터에서 기본값 읽기 (주문폼 초기값용)
  const defaultValues = {
    side: searchParams.get('side') || 'buy',
    price: searchParams.get('price') || '',
    quantity: searchParams.get('quantity') || '',
  }

  // 호가창 → 주문폼 연동 상태
  const [selectedPrice, setSelectedPrice] = useState(null)
  const [selectedSide, setSelectedSide] = useState(null)
  const [orderSubTab, setOrderSubTab] = useState('new') // 'new' | 'modify'
  const [modifyTarget, setModifyTarget] = useState(null)

  // 종목/시장 변경 핸들러 (검색바에서 호출)
  const handleSymbolSelect = ({ code, name, market: mkt }) => {
    setSymbol(code)
    setSymbolName(name)
    if (mkt) setMarket(mkt)
  }

  const handleMarketChange = (newMarket) => {
    setMarket(newMarket)
    setSymbol('')
    setSymbolName('')
  }

  const { loading: placing, error: placeError, place } = useOrderPlace()
  const { orders: openOrders, loading: openLoading, error: openError, load: loadOpen, modify, cancel } = useOpenOrders()
  const { executions, loading: execLoading, error: execError, load: loadExec } = useExecutions()
  const { orders: history, loading: histLoading, error: histError, load: loadHistory } = useOrderHistory()
  const { result: syncResult, loading: syncLoading, sync } = useOrderSync()
  const { reservations, loading: resLoading, error: resError, load: loadReservations, create: createRes, remove: removeRes } = useReservations()

  // 초기 마운트 여부 추적 (quoteSymbol 변경 useEffect 중복 호출 방지)
  const isMounted = useRef(false)
  const orderTimerRef = useRef(null)

  // 언마운트 시 타이머 정리
  useEffect(() => () => { if (orderTimerRef.current) clearTimeout(orderTimerRef.current) }, [])

  // 탭 변경 시 해당 탭 데이터 로드
  useEffect(() => {
    if (activeTab === 'order') loadOpen(market)
    else if (activeTab === 'open') loadOpen(market)
    else if (activeTab === 'executions') loadExec(market)
    else if (activeTab === 'history') loadHistory({})
    else if (activeTab === 'reservation') loadReservations()
  }, [activeTab]) // eslint-disable-line react-hooks/exhaustive-deps

  // 마켓 변경 시 현재 탭 데이터만 리로드 (초기 마운트 스킵 — [activeTab]에서 처리)
  const marketInitRef = useRef(false)
  useEffect(() => {
    if (!marketInitRef.current) {
      marketInitRef.current = true
      return
    }
    if (activeTab === 'order' || activeTab === 'open') loadOpen(market)
    else if (activeTab === 'executions') loadExec(market)
  }, [market]) // eslint-disable-line react-hooks/exhaustive-deps

  // 체결/미체결 탭 10초 자동 폴링
  useEffect(() => {
    if (activeTab === 'open') {
      const id = setInterval(() => loadOpen(market), 10000)
      return () => clearInterval(id)
    }
    if (activeTab === 'executions') {
      const id = setInterval(() => loadExec(market), 10000)
      return () => clearInterval(id)
    }
  }, [activeTab, market, loadOpen, loadExec])

  // 체결통보 실시간 수신
  useExecutionNotice(useCallback((notice) => {
    const sideLabel = notice.side === 'buy' ? '매수' : '매도'
    if (notice.is_filled === '2') {
      notify?.(`체결: ${notice.symbol_name || notice.symbol} ${sideLabel} ${notice.filled_qty}주 @ ${Number(notice.filled_price).toLocaleString()}원`, 'success')
    } else if (notice.is_rejected === '1') {
      notify?.(`거부: ${notice.symbol_name || notice.symbol} ${sideLabel}`, 'error')
    } else if (notice.is_accepted === '1') {
      notify?.(`접수: ${notice.symbol_name || notice.symbol} ${sideLabel} ${notice.order_qty}주`, 'info')
    }
    // 체결/미체결 자동 갱신
    loadOpen(market)
    loadExec(market)
  }, [market, notify, loadOpen, loadExec]))

  // 주문발송 탭에서 symbol 변경 시 미체결 재조회 (마운트 시 중복 호출 방지)
  useEffect(() => {
    if (!isMounted.current) { isMounted.current = true; return }
    if (activeTab === 'order') loadOpen(market)
  }, [symbol]) // eslint-disable-line

  // 주문 확인 모달 → 발송
  const handleConfirmOrder = async (order) => {
    try {
      await place(order)
      setPendingOrder(null)
      notify?.(`주문 발송 완료: ${order.symbol_name || order.symbol} ${order.side === 'buy' ? '매수' : '매도'} ${order.quantity}주`, 'success')
      // 3초 뒤 미체결/체결 자동 갱신
      if (orderTimerRef.current) clearTimeout(orderTimerRef.current)
      orderTimerRef.current = setTimeout(() => {
        loadOpen(market)
        loadExec(market)
      }, 3000)
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
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_1fr] gap-6">
          {/* 왼쪽: 호가창 */}
          <div className="min-h-[400px]">
            <OrderbookPanel
              symbol={symbol}
              market={market}
              onPriceSelect={(p, side) => {
                setSelectedPrice(p)
                setSelectedSide(side ?? null)
                if (side) setOrderSubTab('new')
              }}
            />
          </div>

          {/* 오른쪽: 검색바 + 서브탭 + 주문폼/미체결 + 차트 */}
          <div className="space-y-3">
            {/* 공유 종목 검색바 */}
            <SymbolSearchBar
              market={market}
              onMarketChange={handleMarketChange}
              symbol={symbol}
              symbolName={symbolName}
              onSymbolSelect={handleSymbolSelect}
              defaultQuery={searchParams.get('symbol_name') || searchParams.get('symbol') || ''}
            />

            {/* 서브탭 */}
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="flex border-b border-gray-100">
                <button
                  onClick={() => setOrderSubTab('new')}
                  className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
                    orderSubTab === 'new'
                      ? 'bg-white text-blue-600 border-b-2 border-blue-600'
                      : 'bg-gray-50 text-gray-500 hover:text-gray-700'
                  }`}
                >
                  신규 주문
                </button>
                <button
                  onClick={() => setOrderSubTab('modify')}
                  className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
                    orderSubTab === 'modify'
                      ? 'bg-white text-blue-600 border-b-2 border-blue-600'
                      : 'bg-gray-50 text-gray-500 hover:text-gray-700'
                  }`}
                >
                  정정/취소
                  {openOrders && openOrders.length > 0 && (
                    <span className="ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full bg-orange-500 text-white text-xs font-bold">
                      {openOrders.length > 9 ? '9+' : openOrders.length}
                    </span>
                  )}
                </button>
              </div>

              {/* 신규 주문 서브탭 */}
              {orderSubTab === 'new' && (
                <div className="p-5">
                  <OrderForm
                    symbol={symbol}
                    symbolName={symbolName}
                    market={market}
                    defaultValues={defaultValues}
                    onConfirm={(body) => setPendingOrder(body)}
                    externalPrice={selectedPrice}
                    externalSide={selectedSide}
                  />
                  {placeError && <ErrorAlert message={placeError} className="mt-3" />}
                </div>
              )}

              {/* 정정/취소 서브탭 */}
              {orderSubTab === 'modify' && (
                <div className="p-4">
                  <OrderPanelOpenOrders
                    orders={openOrders}
                    quoteSymbol={symbol}
                    market={market}
                    onModifyTarget={setModifyTarget}
                    onCancel={handleCancelOrder}
                    onRefresh={() => loadOpen(market)}
                  />
                </div>
              )}
            </div>

            {/* 가격 차트 */}
            <PriceChartPanel symbol={symbol} market={market} />
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

      {/* 정정 모달 (주문발송 탭 정정/취소 서브탭에서 사용) */}
      {modifyTarget && (
        <ModifyOrderModal
          order={modifyTarget}
          onClose={() => setModifyTarget(null)}
          onModify={(orderNo, body) => {
            handleModifyOrder(orderNo, body)
            setModifyTarget(null)
          }}
        />
      )}
    </div>
  )
}

// ── 주문발송 탭 인라인 정정/취소 컴포넌트 ────────────────────────────────────
function OrderPanelOpenOrders({ orders, quoteSymbol, market, onModifyTarget, onCancel, onRefresh }) {
  // quoteSymbol이 있으면 해당 종목만 필터링, 없으면 전체 표시
  const filtered = quoteSymbol
    ? (orders || []).filter(o => o.symbol === quoteSymbol)
    : (orders || [])

  if (!filtered.length) {
    return (
      <div className="text-center py-6 text-gray-400 text-sm">
        {quoteSymbol ? `${quoteSymbol} 미체결 주문이 없습니다` : '미체결 주문이 없습니다'}
        <div className="mt-2">
          <button
            onClick={onRefresh}
            className="text-xs text-blue-500 hover:text-blue-700"
          >
            새로고침
          </button>
        </div>
      </div>
    )
  }

  const handleCancel = (order) => {
    if (!window.confirm(
      `주문을 취소하시겠습니까?\n[${order.symbol_name || order.symbol}] ${order.side_label} ${order.quantity}주`
    )) return
    onCancel(order)
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-gray-500">{filtered.length}건</span>
        <button
          onClick={onRefresh}
          className="text-xs text-blue-500 hover:text-blue-700"
        >
          새로고침
        </button>
      </div>
      {filtered.map((order) => {
        const isBuy = order.side === 'buy'
        return (
          <div
            key={order.order_no}
            className="border border-gray-100 rounded-lg p-3 space-y-1.5"
          >
            {/* 종목 + 배지 */}
            <div className="flex items-center gap-2">
              <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-bold ${
                isBuy ? 'bg-red-500 text-white' : 'bg-blue-500 text-white'
              }`}>
                {isBuy ? '매수' : '매도'}
              </span>
              <span className="text-sm font-medium text-gray-800">
                {order.symbol_name || order.symbol}
              </span>
              <span className="text-xs text-gray-400">{order.symbol}</span>
            </div>
            {/* 주문 정보 */}
            <div className="flex items-center gap-3 text-xs text-gray-600">
              <span>주문가: <span className="font-mono font-medium">{Number(order.price).toLocaleString()}</span></span>
              <span>수량: <span className="font-mono">{Number(order.quantity).toLocaleString()}</span></span>
              <span className="text-orange-600">잔량: <span className="font-mono font-medium">{Number(order.remaining_qty).toLocaleString()}</span></span>
            </div>
            {/* 버튼 */}
            {order.api_cancellable === false ? (
              <span
                className="text-xs text-gray-400 italic"
                title="HTS/MTS(증권사 앱)로 접수된 주문은 해당 앱에서 취소하세요"
              >
                앱취소필요
              </span>
            ) : (
              <div className="flex gap-1.5">
                <button
                  onClick={() => onModifyTarget(order)}
                  className="px-3 py-1 text-xs rounded border border-gray-300 text-gray-600 hover:bg-gray-100"
                >
                  정정
                </button>
                <button
                  onClick={() => handleCancel(order)}
                  className="px-3 py-1 text-xs rounded border border-red-300 text-red-600 hover:bg-red-50"
                >
                  취소
                </button>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
