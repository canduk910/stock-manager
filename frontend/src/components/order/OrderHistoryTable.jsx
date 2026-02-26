/**
 * 로컬 주문 이력 테이블 + 필터.
 */
import { useState } from 'react'

const STATUS_LABELS = {
  PLACED: '대기',
  PARTIAL: '부분체결',
  FILLED: '체결',
  CANCELLED: '취소',
  CANCEL_REQUESTED: '취소요청',
  MODIFY_REQUESTED: '정정요청',
  REJECTED: '거부',
  UNKNOWN: '알 수 없음',
}

const STATUS_COLORS = {
  PLACED: 'bg-yellow-100 text-yellow-700',
  PARTIAL: 'bg-orange-100 text-orange-700',
  FILLED: 'bg-green-100 text-green-700',
  CANCELLED: 'bg-gray-100 text-gray-500',
  CANCEL_REQUESTED: 'bg-gray-100 text-gray-500',
  REJECTED: 'bg-red-100 text-red-600',
}

function StatusBadge({ status }) {
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
      STATUS_COLORS[status] || 'bg-gray-100 text-gray-600'
    }`}>
      {STATUS_LABELS[status] || status}
    </span>
  )
}

function SideBadge({ side }) {
  const isBuy = side === 'buy'
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-bold ${
      isBuy ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'
    }`}>
      {isBuy ? '매수' : '매도'}
    </span>
  )
}

export default function OrderHistoryTable({ orders, onFilter }) {
  const [filters, setFilters] = useState({
    symbol: '',
    market: '',
    status: '',
    dateFrom: '',
    dateTo: '',
  })

  const handleFilter = (e) => {
    e.preventDefault()
    onFilter(filters)
  }

  const handleReset = () => {
    const reset = { symbol: '', market: '', status: '', dateFrom: '', dateTo: '' }
    setFilters(reset)
    onFilter(reset)
  }

  return (
    <div className="space-y-4">
      {/* 필터 */}
      <form onSubmit={handleFilter} className="flex flex-wrap gap-2 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">종목코드</label>
          <input
            type="text"
            value={filters.symbol}
            onChange={(e) => setFilters((f) => ({ ...f, symbol: e.target.value }))}
            placeholder="005930"
            className="border border-gray-300 rounded px-2 py-1.5 text-sm w-28"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">시장</label>
          <select
            value={filters.market}
            onChange={(e) => setFilters((f) => ({ ...f, market: e.target.value }))}
            className="border border-gray-300 rounded px-2 py-1.5 text-sm"
          >
            <option value="">전체</option>
            <option value="KR">국내</option>
            <option value="US">미국</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">상태</label>
          <select
            value={filters.status}
            onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
            className="border border-gray-300 rounded px-2 py-1.5 text-sm"
          >
            <option value="">전체</option>
            <option value="PLACED">대기</option>
            <option value="PARTIAL">부분체결</option>
            <option value="FILLED">체결</option>
            <option value="CANCELLED">취소</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">시작일</label>
          <input
            type="date"
            value={filters.dateFrom}
            onChange={(e) => setFilters((f) => ({ ...f, dateFrom: e.target.value }))}
            className="border border-gray-300 rounded px-2 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">종료일</label>
          <input
            type="date"
            value={filters.dateTo}
            onChange={(e) => setFilters((f) => ({ ...f, dateTo: e.target.value }))}
            className="border border-gray-300 rounded px-2 py-1.5 text-sm"
          />
        </div>
        <button
          type="submit"
          className="px-3 py-1.5 bg-gray-700 text-white text-sm rounded hover:bg-gray-800"
        >
          검색
        </button>
        <button
          type="button"
          onClick={handleReset}
          className="px-3 py-1.5 border border-gray-300 text-sm rounded text-gray-600 hover:bg-gray-50"
        >
          초기화
        </button>
      </form>

      {/* 테이블 */}
      {!orders || orders.length === 0 ? (
        <div className="text-center py-8 text-gray-400 text-sm">주문 이력이 없습니다.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                {['ID', '시장', '종목', '매매', '유형', '주문가', '수량', '체결가', '체결수량', '상태', '주문일시', '메모'].map((h) => (
                  <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-gray-600 whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {orders.map((order) => (
                <tr key={order.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 text-xs text-gray-400">{order.id}</td>
                  <td className="px-3 py-2 text-xs text-gray-500">{order.market}</td>
                  <td className="px-3 py-2">
                    <div className="font-medium text-gray-900">{order.symbol_name || order.symbol}</div>
                    <div className="text-xs text-gray-400">{order.symbol}</div>
                  </td>
                  <td className="px-3 py-2"><SideBadge side={order.side} /></td>
                  <td className="px-3 py-2 text-xs text-gray-600">
                    {order.order_type === '01' ? '시장가' : '지정가'}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-xs">
                    {Number(order.price).toLocaleString()}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-xs">{Number(order.quantity).toLocaleString()}</td>
                  <td className="px-3 py-2 text-right font-mono text-xs text-gray-500">
                    {order.filled_price ? Number(order.filled_price).toLocaleString() : '-'}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-xs text-green-600">
                    {order.filled_quantity > 0 ? Number(order.filled_quantity).toLocaleString() : '-'}
                  </td>
                  <td className="px-3 py-2"><StatusBadge status={order.status} /></td>
                  <td className="px-3 py-2 text-xs text-gray-400 whitespace-nowrap">
                    {order.placed_at?.slice(0, 16) || '-'}
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-500">{order.memo || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
