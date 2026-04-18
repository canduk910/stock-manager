import { Link } from 'react-router-dom'

const TIMING_STYLES = {
  immediate:  { bg: 'bg-red-100', text: 'text-red-700', label: '즉시' },
  this_week:  { bg: 'bg-yellow-100', text: 'text-yellow-700', label: '금주' },
  this_month: { bg: 'bg-gray-100', text: 'text-gray-600', label: '이번 달' },
}

export default function SectorRecommendationCard({ recommendations }) {
  if (!recommendations || recommendations.length === 0) return null

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="bg-gradient-to-r from-emerald-50 to-teal-50 px-4 py-2.5 text-sm font-semibold text-gray-700 border-b border-gray-200 flex items-center gap-2">
        신규 섹터 진입 추천
        <span className="text-xs font-normal text-emerald-600 bg-emerald-100 px-1.5 py-0.5 rounded-full">
          {recommendations.length}개 섹터
        </span>
      </div>
      <div className="divide-y divide-gray-100">
        {recommendations.map((rec, i) => {
          const timing = TIMING_STYLES[rec.entry_timing] || TIMING_STYLES.this_month
          return (
            <div key={i} className="p-4 space-y-2.5">
              {/* 헤더: 섹터명 + 목표비중 + 타이밍 */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-semibold text-gray-900">{rec.sector}</span>
                {rec.target_weight_pct != null && (
                  <span className="text-xs text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                    목표 {rec.target_weight_pct}%
                  </span>
                )}
                <span className={`text-xs px-1.5 py-0.5 rounded ${timing.bg} ${timing.text}`}>
                  {timing.label}
                </span>
              </div>

              {/* 추천 근거 */}
              <p className="text-xs text-gray-600 leading-relaxed">{rec.rationale}</p>

              {/* 대표 종목 */}
              {rec.representative_stocks && rec.representative_stocks.length > 0 && (
                <div className="space-y-1">
                  <h5 className="text-xs font-medium text-gray-500">대표 종목</h5>
                  <div className="flex flex-wrap gap-2">
                    {rec.representative_stocks.map((stock, j) => (
                      <Link
                        key={j}
                        to={`/detail/${stock.stock_code}`}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1.5 bg-white border border-gray-200 rounded-lg hover:border-emerald-300 hover:bg-emerald-50/50 transition-colors group"
                      >
                        <span className="text-xs font-medium text-gray-900 group-hover:text-emerald-700">
                          {stock.stock_name}
                        </span>
                        <span className="text-[10px] text-gray-400">{stock.stock_code}</span>
                        {stock.market && (
                          <span className="text-[10px] text-gray-400 bg-gray-100 px-1 rounded">
                            {stock.market}
                          </span>
                        )}
                      </Link>
                    ))}
                  </div>
                  {/* 종목별 선정 근거 */}
                  <div className="mt-1 space-y-0.5">
                    {rec.representative_stocks.map((stock, j) => (
                      stock.reason && (
                        <p key={j} className="text-[11px] text-gray-500">
                          <span className="font-medium">{stock.stock_name}</span>: {stock.reason}
                        </p>
                      )
                    ))}
                  </div>
                </div>
              )}

              {/* 진입 전략 */}
              {rec.entry_strategy && (
                <div className="text-xs text-gray-500">
                  <span className="font-medium text-gray-600">진입 전략: </span>
                  {rec.entry_strategy}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
