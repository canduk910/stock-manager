import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import LoadingSpinner from '../common/LoadingSpinner'
import ErrorAlert from '../common/ErrorAlert'
import SectorRelativeChart from './SectorRelativeChart'
import { getPrimaryReps, getAllReps } from './sectorRepresentatives'

const fmt = (v) =>
  v != null
    ? v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : '-'

function heatmapStyle(val) {
  if (val == null) return { backgroundColor: '#f9fafb' } // gray-50
  const intensity = Math.min(Math.abs(val) / 30, 1)
  const alpha = 0.1 + intensity * 0.5
  if (val > 0) return { backgroundColor: `rgba(34,197,94,${alpha})` }
  return { backgroundColor: `rgba(239,68,68,${alpha})` }
}

function ReturnCell({ value }) {
  if (value == null) return <td className="px-3 py-2 text-center text-gray-400 text-sm">-</td>
  const sign = value > 0 ? '+' : ''
  const textColor = value > 0 ? 'text-red-600' : value < 0 ? 'text-blue-600' : 'text-gray-600'
  return (
    <td className="px-3 py-2 text-center text-sm font-medium" style={heatmapStyle(value)}>
      <span className={textColor}>{sign}{fmt(value)}%</span>
    </td>
  )
}

// 종목 링크 (DetailPage로 이동)
function StockChip({ stock, market }) {
  if (!stock) return null
  return (
    <Link
      to={`/detail/${stock.code}`}
      className="inline-block px-1.5 py-0.5 rounded text-[11px] font-medium bg-white border border-gray-200 text-gray-700 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700 transition-colors mr-1 mb-0.5"
      title={`${market === 'KR' ? '🇰🇷' : '🇺🇸'} ${stock.code}`}
    >
      {stock.name}
    </Link>
  )
}

// 섹터명 셀 (선택된 시장의 대표 1개 + 클릭 시 5개 펼침)
function SectorNameCell({ sector, market, expanded, onToggle }) {
  const primary = getPrimaryReps(sector)
  const all = getAllReps(sector)
  const marketKey = market === 'KR' ? 'kr' : 'us'
  const flag = market === 'KR' ? '🇰🇷' : '🇺🇸'
  const primaryStock = primary?.[marketKey]
  const allStocks = all?.[marketKey] || []
  const hasReps = !!primaryStock

  return (
    <td className="px-3 py-2 align-top">
      <button
        onClick={onToggle}
        className="font-medium text-gray-900 whitespace-nowrap hover:text-blue-600 transition-colors flex items-center gap-1"
        disabled={!hasReps}
      >
        {sector.name_ko || sector.name}
        {hasReps && (
          <span className="text-[10px] text-gray-400">{expanded ? '▾' : '▸'}</span>
        )}
      </button>
      {!expanded && primaryStock && (
        <div className="text-[11px] text-gray-500 mt-0.5 whitespace-nowrap">
          <span>{flag} {primaryStock.name}</span>
        </div>
      )}
      {expanded && allStocks.length > 0 && (
        <div className="mt-1.5 p-2 bg-gray-50 rounded border border-gray-200">
          <div className="text-[10px] text-gray-500 mb-1 font-semibold">{flag} 대표 종목</div>
          <div className="flex flex-wrap">
            {allStocks.map((s) => <StockChip key={s.code} stock={s} market={market} />)}
          </div>
        </div>
      )}
    </td>
  )
}

export default function SectorHeatmapSection({ data, loading, error }) {
  const [market, setMarket] = useState('US')
  const [expandedSym, setExpandedSym] = useState(null)

  // 시장별 섹터 리스트 — sectors_us/sectors_kr 우선, 없으면 sectors(백워드 호환=US)
  const sectorList = useMemo(() => {
    if (!data) return []
    if (market === 'KR') return data.sectors_kr || []
    return data.sectors_us || data.sectors || []
  }, [data, market])

  // 3M 수익률 내림차순 정렬
  const sorted = useMemo(() => {
    if (!sectorList.length) return []
    return [...sectorList].sort((a, b) => (b.return_3m ?? -999) - (a.return_3m ?? -999))
  }, [sectorList])

  // 산점도용 wrapper — 선택된 시장의 섹터만 전달
  const scatterData = useMemo(() => ({ ...data, sectors: sectorList }), [data, sectorList])

  if (loading) return <LoadingSpinner message="섹터 히트맵 로딩 중..." />
  if (error) return <ErrorAlert message={error} />
  const hasAnyData = (data?.sectors_us?.length || 0) + (data?.sectors_kr?.length || 0) + (data?.sectors?.length || 0)
  if (!hasAnyData) return null

  const subtitle = market === 'KR'
    ? 'KRX 자체 분류 13섹터 (KODEX/TIGER ETF)'
    : 'GICS 11섹터 (SPDR Select Sector ETF)'

  return (
    <section>
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">섹터 히트맵</h2>
          <p className="text-[11px] text-gray-500 mt-0.5">{subtitle}</p>
        </div>
        {/* KR/US 토글 (ReportPage 패턴 동일) */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-600">시장</span>
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            {['KR', 'US'].map((m) => (
              <button
                key={m}
                onClick={() => { setMarket(m); setExpandedSym(null) }}
                className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  market === m
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {m === 'KR' ? '🇰🇷 한국' : '🇺🇸 미국'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 선택된 시장에 데이터 없을 때 */}
      {!sorted.length && (
        <div className="rounded-lg border bg-white p-6 text-center text-sm text-gray-400">
          {market === 'KR' ? '한국' : '미국'} 섹터 데이터가 아직 수집되지 않았습니다.
        </div>
      )}

      {/* 좌(산점도) + 우(히트맵 테이블) 2분할. 모바일은 세로 스택. */}
      {sorted.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div>
            <SectorRelativeChart data={scatterData} />
          </div>
          <div className="rounded-lg border bg-white shadow-sm overflow-x-auto">
            <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 text-left font-medium text-gray-600">
                  섹터 <span className="text-[10px] font-normal text-gray-400 ml-1">(클릭 시 대표종목 펼침)</span>
                </th>
                <th className="px-3 py-2 text-center font-medium text-gray-600">1M</th>
                <th className="px-3 py-2 text-center font-medium text-gray-600">3M</th>
                <th className="px-3 py-2 text-center font-medium text-gray-600">6M</th>
                <th className="px-3 py-2 text-center font-medium text-gray-600">1Y</th>
                <th className="px-3 py-2 text-center font-medium text-gray-600">3Y</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((s) => {
                const isExpanded = expandedSym === s.symbol
                return (
                  <tr key={s.symbol} className="border-b last:border-b-0 hover:bg-gray-50/50">
                    <SectorNameCell
                      sector={s}
                      market={market}
                      expanded={isExpanded}
                      onToggle={() => setExpandedSym(isExpanded ? null : s.symbol)}
                    />
                    <ReturnCell value={s.return_1m} />
                    <ReturnCell value={s.return_3m} />
                    <ReturnCell value={s.return_6m} />
                    <ReturnCell value={s.return_1y} />
                    <ReturnCell value={s.return_3y} />
                  </tr>
                )
              })}
            </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  )
}
