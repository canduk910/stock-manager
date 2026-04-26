/**
 * 과거 보고서 이력 카드 리스트.
 *
 * Props: { items, activeId, onSelect }
 */

const REGIME_STYLES = {
  accumulation: 'bg-green-100 text-green-800',
  selective: 'bg-yellow-100 text-yellow-800',
  cautious: 'bg-orange-100 text-orange-800',
  defensive: 'bg-red-100 text-red-800',
}

const MARKET_STYLES = {
  KR: 'bg-blue-100 text-blue-700',
  US: 'bg-emerald-100 text-emerald-700',
}

export default function ReportHistoryList({ items, activeId, onSelect }) {
  if (!items || items.length === 0) return null

  return (
    <div>
      <h3 className="text-sm font-bold text-gray-700 mb-3">보고서 이력</h3>
      <div className="space-y-2">
        {items.map((r) => {
          const isActive = r.id === activeId
          return (
            <div
              key={r.id}
              onClick={() => onSelect(r.id)}
              className={`border rounded-lg p-3 cursor-pointer transition-colors ${
                isActive
                  ? 'border-blue-400 bg-blue-50/50'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-mono font-medium text-gray-800">{r.date}</span>
                <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${MARKET_STYLES[r.market] || 'bg-gray-100 text-gray-600'}`}>
                  {r.market}
                </span>
                {r.regime && (
                  <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${REGIME_STYLES[r.regime] || 'bg-gray-100 text-gray-700'}`}>
                    {r.regime}
                  </span>
                )}
                {isActive && (
                  <span className="text-xs text-blue-500 font-medium ml-auto">보기 중</span>
                )}
              </div>
              {r.sector_summary ? (
                <p className="text-xs text-gray-500 mt-1.5 leading-relaxed line-clamp-2">{r.sector_summary}</p>
              ) : (
                <p className="text-xs text-gray-400 mt-1.5">
                  후보 {r.candidates_count ?? 0}개 / 추천 {r.recommended_count ?? 0}개
                </p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
