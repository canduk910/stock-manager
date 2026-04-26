/**
 * 3컨셉 섹터 추천 탭 (모멘텀/역발상/3개월선점).
 *
 * Props: { concepts, market }
 * concepts: [{ concept, concept_label, description, sectors: [{ sector_name, rationale, stocks }] }]
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import WatchlistButton from '../common/WatchlistButton'

const CONCEPT_STYLES = {
  momentum:    { bg: 'bg-red-50',    border: 'border-red-200',    text: 'text-red-700',    tab: 'bg-red-600',    icon: '🔥' },
  contrarian:  { bg: 'bg-blue-50',   border: 'border-blue-200',   text: 'text-blue-700',   tab: 'bg-blue-600',   icon: '🔄' },
  forward_3m:  { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', tab: 'bg-purple-600', icon: '🔮' },
}

export default function SectorConceptTabs({ concepts, market = 'KR' }) {
  const [activeIdx, setActiveIdx] = useState(0)

  if (!concepts || concepts.length === 0) return null

  const active = concepts[activeIdx] || concepts[0]
  const style = CONCEPT_STYLES[active.concept] || CONCEPT_STYLES.momentum

  return (
    <div className="space-y-3">
      {/* 탭 헤더 */}
      <div className="flex gap-1 border-b border-gray-200">
        {concepts.map((c, i) => {
          const s = CONCEPT_STYLES[c.concept] || CONCEPT_STYLES.momentum
          const isActive = i === activeIdx
          return (
            <button
              key={c.concept}
              onClick={() => setActiveIdx(i)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-1.5 ${
                isActive
                  ? `${s.text} border-current`
                  : 'text-gray-500 border-transparent hover:text-gray-700'
              }`}
            >
              <span>{s.icon}</span>
              <span>{c.concept_label}</span>
              <span className="text-xs text-gray-400">({(c.sectors || []).length})</span>
            </button>
          )
        })}
      </div>

      {/* 컨셉 설명 */}
      <p className={`text-sm ${style.text} font-medium px-1`}>{active.description}</p>

      {/* 섹터 카드들 */}
      <div className="space-y-3">
        {(active.sectors || []).map((sector, si) => (
          <div key={si} className={`border ${style.border} rounded-lg overflow-hidden`}>
            {/* 섹터 헤더 */}
            <div className={`${style.bg} px-4 py-2.5 border-b ${style.border}`}>
              <h4 className={`text-sm font-bold ${style.text}`}>{sector.sector_name}</h4>
              <p className="text-xs text-gray-600 mt-1 leading-relaxed">{sector.rationale}</p>
            </div>

            {/* 종목 리스트 */}
            <div className="divide-y divide-gray-100">
              {(sector.stocks || []).map((stock, sti) => (
                <div key={sti} className="px-4 py-2.5 flex items-center gap-3">
                  <Link
                    to={`/detail/${stock.code}`}
                    className="flex items-center gap-2 hover:text-blue-600 transition-colors min-w-0 flex-1"
                  >
                    <span className="text-sm font-semibold text-gray-900 hover:text-blue-600 truncate">
                      {stock.name}
                    </span>
                    <span className="text-xs text-gray-400 shrink-0">{stock.code}</span>
                  </Link>
                  <p className="text-xs text-gray-500 flex-[2] min-w-0 truncate hidden md:block">
                    {stock.reason}
                  </p>
                  <div className="shrink-0">
                    <WatchlistButton code={stock.code} market={market} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
