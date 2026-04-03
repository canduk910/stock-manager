const ACTION_STYLES = {
  increase: { icon: '↑', color: 'text-red-600', bg: 'bg-red-50', label: '비중 확대' },
  reduce:   { icon: '↓', color: 'text-blue-600', bg: 'bg-blue-50', label: '비중 축소' },
  hold:     { icon: '→', color: 'text-gray-500', bg: 'bg-gray-50', label: '유지' },
  exit:     { icon: '×', color: 'text-blue-700', bg: 'bg-blue-100', label: '전량 매도' },
}

export default function RebalanceCard({ suggestions }) {
  if (!suggestions || suggestions.length === 0) return null

  const sorted = [...suggestions].sort((a, b) => (a.priority || 99) - (b.priority || 99))

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="bg-gray-50 px-4 py-2.5 text-sm font-semibold text-gray-700 border-b border-gray-200">
        리밸런싱 제안
      </div>
      <div className="divide-y divide-gray-100">
        {sorted.map((item, i) => {
          const style = ACTION_STYLES[item.action] || ACTION_STYLES.hold
          return (
            <div key={i} className={`p-3 ${style.bg}`}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className={`text-lg font-bold ${style.color}`}>{style.icon}</span>
                  <span className="text-sm font-semibold text-gray-900">
                    {item.stock_name || item.target}
                  </span>
                  {item.stock_code && (
                    <span className="text-xs text-gray-400">{item.stock_code}</span>
                  )}
                  <span className={`text-xs px-1.5 py-0.5 rounded ${style.color} ${style.bg} border border-current/20`}>
                    {style.label}
                  </span>
                </div>
                <div className="text-xs text-gray-500">
                  우선순위 {item.priority || '-'}
                </div>
              </div>

              {/* 비중 변화 */}
              <div className="flex items-center gap-2 text-xs text-gray-600 mb-1">
                <span>현재 {item.current_weight != null ? `${item.current_weight}%` : '-'}</span>
                <span className={style.color}>→</span>
                <span className="font-medium">제안 {item.suggested_weight != null ? `${item.suggested_weight}%` : '-'}</span>
              </div>

              {/* 근거 */}
              <p className="text-xs text-gray-600 leading-relaxed">{item.reason}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
