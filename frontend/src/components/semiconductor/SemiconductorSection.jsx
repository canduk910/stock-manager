/**
 * 반도체 사이클 모니터링 카드 섹션.
 *
 * MacroPage 마운트 (MacroCycleSection 직후).
 * 종합 신호 + 5종 지표 카드 + 최근 신호 요약 + [상세 보기 →] 버튼 → 모달.
 */

import { useState } from 'react'
import { useSemiconductorDashboard, useSemiconductorSignals } from '../../hooks/useSemiconductor'
import SemiconductorDetailModal from './SemiconductorDetailModal'

const LEVEL_BADGE = {
  GREEN: 'bg-green-100 text-green-700',
  INFO: 'bg-blue-100 text-blue-700',
  YELLOW: 'bg-yellow-100 text-yellow-800',
  WARNING: 'bg-yellow-100 text-yellow-800',
  ALERT: 'bg-red-100 text-red-700',
  RED: 'bg-red-100 text-red-700',
}

const LEVEL_ICON = {
  GREEN: '●',
  INFO: '●',
  YELLOW: '⚠',
  WARNING: '⚠',
  ALERT: '🛑',
  RED: '🛑',
}

const LEVEL_LABEL = {
  GREEN: '정상',
  INFO: '관찰',
  YELLOW: '주의',
  WARNING: '경고',
  ALERT: '알람',
  RED: '경고',
}

const INDICATOR_DISPLAY_ORDER = [
  'hyperscaler_capex',
  'memory_inventory',
  'hbm_contracts',
  'ai_ipo',
  'market_breadth',
]

const SHORT_LABEL = {
  hyperscaler_capex: '캐펙스 2',
  memory_inventory: '재고 4',
  hbm_contracts: 'HBM계약 5',
  ai_ipo: 'AI IPO 6',
  market_breadth: '시장폭 8',
}

function formatValue(name, value) {
  if (value === null || value === undefined) return '—'
  if (name === 'hyperscaler_capex') {
    // USD billions
    const b = value / 1_000_000_000
    return `$${b.toFixed(1)}B`
  }
  if (name === 'memory_inventory') return `${value.toFixed(1)}일`
  if (name === 'hbm_contracts') return `${value}건`
  if (name === 'market_breadth') return value.toFixed(2)
  if (typeof value === 'number') return value.toFixed(2)
  return String(value)
}

function CompositeBanner({ composite }) {
  const level = composite?.level || 'GREEN'
  return (
    <div className={`flex items-start gap-3 px-4 py-3 rounded-lg ${LEVEL_BADGE[level] || LEVEL_BADGE.GREEN}`}>
      <div className="text-2xl leading-none">{LEVEL_ICON[level]}</div>
      <div className="flex-1">
        <div className="font-semibold">
          종합 신호: {level} ({LEVEL_LABEL[level] || level})
        </div>
        <div className="text-sm mt-0.5 opacity-90">
          {composite?.reason || '데이터 수집 중'}
        </div>
      </div>
    </div>
  )
}

function IndicatorCard({ name, payload }) {
  const level = payload?.level || 'GREEN'
  const value = payload?.value
  return (
    <div className={`px-3 py-2 rounded border ${LEVEL_BADGE[level] || LEVEL_BADGE.GREEN}`}>
      <div className="text-xs font-semibold opacity-80">
        {SHORT_LABEL[name] || name}
      </div>
      <div className="flex items-center gap-1 mt-1">
        <span className="text-lg">{LEVEL_ICON[level]}</span>
        <span className="text-xs font-medium">{LEVEL_LABEL[level] || level}</span>
      </div>
      <div className="text-sm font-medium mt-0.5">{formatValue(name, value)}</div>
    </div>
  )
}

function RecentSignalsSummary({ signals }) {
  if (!signals || signals.length === 0) {
    return <div className="text-xs text-gray-500">최근 신호 없음</div>
  }
  const counts = signals.slice(0, 20).reduce((acc, s) => {
    const l = s.level
    acc[l] = (acc[l] || 0) + 1
    return acc
  }, {})
  const parts = Object.entries(counts).map(
    ([level, n]) => `${level} ${n}`,
  )
  return (
    <div className="text-xs text-gray-600">
      최근 신호 {signals.length}건 ({parts.join(', ')})
    </div>
  )
}

export default function SemiconductorSection() {
  const { data: dashboard, loading, error, reload } = useSemiconductorDashboard()
  const { data: signalsRes } = useSemiconductorSignals({ limit: 20 })
  const [modalOpen, setModalOpen] = useState(false)

  if (loading && !dashboard) {
    return (
      <section className="bg-white rounded-lg shadow p-4 my-4">
        <div className="text-gray-500 text-sm">반도체 사이클 로딩 중…</div>
      </section>
    )
  }
  if (error && !dashboard) {
    return (
      <section className="bg-white rounded-lg shadow p-4 my-4">
        <div className="text-red-600 text-sm">
          반도체 사이클 데이터 로딩 실패: {error.message || String(error)}
        </div>
      </section>
    )
  }

  const composite = dashboard?.composite || {}
  const indicators = dashboard?.indicators || {}
  const signals = signalsRes?.signals || []

  return (
    <section className="bg-white rounded-lg shadow p-4 my-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-bold">반도체 사이클 모니터링</h2>
        <button
          type="button"
          onClick={() => setModalOpen(true)}
          className="text-sm text-blue-600 hover:underline"
        >
          상세 보기 →
        </button>
      </div>

      <CompositeBanner composite={composite} />

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 mt-3">
        {INDICATOR_DISPLAY_ORDER.map((name) => (
          <IndicatorCard key={name} name={name} payload={indicators[name]} />
        ))}
      </div>

      <div className="mt-3 flex items-center justify-between">
        <RecentSignalsSummary signals={signals} />
        <div className="text-[11px] text-gray-400">
          Phase 1: 지표 2/4/5/6/8 (가격·가이던스 Phase 2)
        </div>
      </div>

      {modalOpen && (
        <SemiconductorDetailModal
          dashboard={dashboard}
          signals={signals}
          onClose={() => setModalOpen(false)}
          onRefresh={reload}
        />
      )}
    </section>
  )
}
