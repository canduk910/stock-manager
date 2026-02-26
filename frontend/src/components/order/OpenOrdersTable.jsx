/**
 * 미체결 주문 테이블 + 정정/취소 버튼.
 */
import { useState } from 'react'
import ModifyOrderModal from './ModifyOrderModal'

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

export default function OpenOrdersTable({ orders, onRefresh, onCancel, onModify }) {
  const [modifyTarget, setModifyTarget] = useState(null)

  if (!orders || orders.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400 text-sm">미체결 주문이 없습니다.</div>
    )
  }

  const handleCancel = (order) => {
    if (!confirm(`주문을 취소하시겠습니까?\n[${order.symbol_name || order.symbol}] ${order.side_label} ${order.quantity}주`)) return
    onCancel(order)
  }

  const COLS = [
    { label: '시장',    align: 'left'  },
    { label: '종목',    align: 'left'  },
    { label: '매매',    align: 'left'  },
    { label: '유형',    align: 'left'  },
    { label: '주문가',  align: 'right' },
    { label: '수량',    align: 'right' },
    { label: '잔량',    align: 'right' },
    { label: '체결',    align: 'right' },
    { label: '주문번호', align: 'left' },
    { label: '조작',    align: 'left'  },
  ]

  return (
    <>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              {COLS.map(({ label, align }) => (
                <th
                  key={label}
                  className={`px-3 py-2 text-${align} text-xs font-semibold text-gray-600 whitespace-nowrap`}
                >
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {orders.map((order) => (
              <tr key={order.order_no} className="hover:bg-gray-50">
                <td className="px-3 py-2 text-xs text-gray-500">{order.market}</td>
                <td className="px-3 py-2">
                  <div className="font-medium text-gray-900">{order.symbol_name || order.symbol}</div>
                  <div className="text-xs text-gray-400">{order.symbol}</div>
                </td>
                <td className="px-3 py-2"><SideBadge side={order.side} /></td>
                <td className="px-3 py-2 text-xs text-gray-600">{order.order_type_label || order.order_type}</td>
                <td className="px-3 py-2 text-right font-mono text-xs">
                  {Number(order.price).toLocaleString()}
                </td>
                <td className="px-3 py-2 text-right font-mono text-xs">{Number(order.quantity).toLocaleString()}</td>
                <td className="px-3 py-2 text-right font-mono text-xs text-orange-600">
                  {Number(order.remaining_qty).toLocaleString()}
                </td>
                <td className="px-3 py-2 text-right font-mono text-xs text-green-600">
                  {Number(order.filled_qty).toLocaleString()}
                </td>
                <td className="px-3 py-2 text-xs text-gray-400 font-mono">{order.order_no}</td>
                <td className="px-3 py-2">
                  {order.api_cancellable === false ? (
                    <span
                      className="text-xs text-gray-400 italic"
                      title="HTS/MTS(증권사 앱)로 접수된 주문은 해당 앱에서 취소하세요"
                    >
                      앱취소필요
                    </span>
                  ) : (
                    <div className="flex gap-1">
                      <button
                        onClick={() => setModifyTarget(order)}
                        className="px-2 py-1 text-xs rounded border border-gray-300 text-gray-600 hover:bg-gray-100"
                      >
                        정정
                      </button>
                      <button
                        onClick={() => handleCancel(order)}
                        className="px-2 py-1 text-xs rounded border border-red-300 text-red-600 hover:bg-red-50"
                      >
                        취소
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {modifyTarget && (
        <ModifyOrderModal
          order={modifyTarget}
          onClose={() => setModifyTarget(null)}
          onModify={(orderNo, body) => {
            onModify(orderNo, body)
            setModifyTarget(null)
          }}
        />
      )}
    </>
  )
}
