/**
 * 당일 체결 내역 테이블.
 */
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

export default function ExecutionsTable({ executions }) {
  if (!executions || executions.length === 0) {
    return <div className="text-center py-8 text-gray-400 text-sm">당일 체결 내역이 없습니다.</div>
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50">
            {['시장', '종목', '매매', '유형', '체결가', '주문수량', '체결수량', '체결금액', '주문번호'].map((h) => (
              <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-gray-600 whitespace-nowrap">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {executions.map((exec, i) => (
            <tr key={`${exec.order_no}-${i}`} className="hover:bg-gray-50">
              <td className="px-3 py-2 text-xs text-gray-500">{exec.market}</td>
              <td className="px-3 py-2">
                <div className="font-medium text-gray-900">{exec.symbol_name || exec.symbol}</div>
                <div className="text-xs text-gray-400">{exec.symbol}</div>
              </td>
              <td className="px-3 py-2"><SideBadge side={exec.side} /></td>
              <td className="px-3 py-2 text-xs text-gray-600">{exec.order_type_label || '-'}</td>
              <td className="px-3 py-2 text-right font-mono text-xs">
                {Number(exec.filled_price || exec.price).toLocaleString()}
              </td>
              <td className="px-3 py-2 text-right font-mono text-xs">{Number(exec.quantity).toLocaleString()}</td>
              <td className="px-3 py-2 text-right font-mono text-xs text-green-600">
                {Number(exec.filled_qty).toLocaleString()}
              </td>
              <td className="px-3 py-2 text-right font-mono text-xs">
                {Number(exec.filled_amount).toLocaleString()}
              </td>
              <td className="px-3 py-2 text-xs text-gray-400 font-mono">{exec.order_no}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
