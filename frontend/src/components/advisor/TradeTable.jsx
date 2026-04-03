import { useState } from 'react'
import TradeConfirmModal from './TradeConfirmModal'

const URGENCY_STYLES = {
  immediate:  { bg: 'bg-red-100', text: 'text-red-700', label: '즉시' },
  this_week:  { bg: 'bg-yellow-100', text: 'text-yellow-700', label: '금주' },
  this_month: { bg: 'bg-gray-100', text: 'text-gray-600', label: '이번 달' },
}

export default function TradeTable({ trades, notify }) {
  const [selectedTrade, setSelectedTrade] = useState(null)

  if (!trades || trades.length === 0) return null

  return (
    <>
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <div className="bg-gray-50 px-4 py-2.5 text-sm font-semibold text-gray-700 border-b border-gray-200">
          매매 실행안
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-gray-500 text-xs">
                <th className="px-3 py-2 text-left font-medium">종목</th>
                <th className="px-3 py-2 text-left font-medium">시장</th>
                <th className="px-3 py-2 text-center font-medium">방향</th>
                <th className="px-3 py-2 text-right font-medium">수량</th>
                <th className="px-3 py-2 text-right font-medium">목표가</th>
                <th className="px-3 py-2 text-center font-medium">긴급도</th>
                <th className="px-3 py-2 text-left font-medium">근거</th>
                <th className="px-3 py-2 text-center font-medium">실행</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {trades.map((t, i) => {
                const isBuy = t.action === 'buy'
                const urg = URGENCY_STYLES[t.urgency] || URGENCY_STYLES.this_month
                return (
                  <tr key={i} className={isBuy ? 'bg-red-50/30' : 'bg-blue-50/30'}>
                    <td className="px-3 py-2">
                      <div className="font-medium text-gray-900">{t.stock_name}</div>
                      <div className="text-xs text-gray-400">{t.stock_code}</div>
                    </td>
                    <td className="px-3 py-2 text-gray-600">{t.market}</td>
                    <td className="px-3 py-2 text-center">
                      <span className={`font-bold ${isBuy ? 'text-red-600' : 'text-blue-600'}`}>
                        {isBuy ? '매수' : '매도'}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right text-gray-900">
                      {Number(t.qty).toLocaleString()}
                    </td>
                    <td className="px-3 py-2 text-right text-gray-900">
                      {Number(t.target_price).toLocaleString()}
                    </td>
                    <td className="px-3 py-2 text-center">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${urg.bg} ${urg.text}`}>
                        {urg.label}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-600 max-w-[300px]">
                      <p className="whitespace-pre-line leading-relaxed">{t.reason}</p>
                    </td>
                    <td className="px-3 py-2 text-center">
                      <button
                        onClick={() => setSelectedTrade(t)}
                        className={`px-2.5 py-1 rounded text-xs font-medium text-white transition-colors ${
                          isBuy ? 'bg-red-500 hover:bg-red-600' : 'bg-blue-500 hover:bg-blue-600'
                        }`}
                      >
                        주문
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      <TradeConfirmModal
        trade={selectedTrade}
        onClose={() => setSelectedTrade(null)}
        notify={notify}
      />
    </>
  )
}
