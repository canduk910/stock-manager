/**
 * 반도체 사이클 모니터링 — 상세 모달.
 *
 * 좌측 sticky nav (anchor scroll) + 본문 5종 누적 섹션 + 신호 이력 + 임계값 패널 (관리자).
 * Pattern: fixed inset-0 bg-black/50 + ESC + 백드롭 클릭.
 */

import { useCallback, useEffect } from 'react'
import SemiIndicatorChart from './SemiIndicatorChart'
import SemiThresholdsPanel from './SemiThresholdsPanel'

const LEVEL_BADGE = {
  GREEN: 'bg-green-100 text-green-700',
  INFO: 'bg-blue-100 text-blue-700',
  YELLOW: 'bg-yellow-100 text-yellow-800',
  WARNING: 'bg-yellow-100 text-yellow-800',
  ALERT: 'bg-red-100 text-red-700',
  RED: 'bg-red-100 text-red-700',
}

const NAV_ITEMS = [
  { id: 'composite', label: '종합 신호' },
  { id: 'hyperscaler_capex', label: '지표 2 — 캐펙스' },
  { id: 'memory_inventory', label: '지표 4 — 메모리 재고' },
  { id: 'hbm_contracts', label: '지표 5 — HBM 공시' },
  { id: 'ai_ipo', label: '지표 6 — AI IPO' },
  { id: 'market_breadth', label: '지표 8 — 시장폭' },
  { id: 'signals', label: '신호 이력' },
  { id: 'thresholds', label: '⚙ 임계값 (관리)' },
]

function _scrollTo(id) {
  const el = document.getElementById(`semi-section-${id}`)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function _renderThresholdSummary(threshold) {
  if (!threshold) return null
  return (
    <div className="text-xs text-gray-600 mt-1">
      임계:{' '}
      {Object.entries(threshold).map(([k, v]) => (
        <span key={k} className="mr-2">
          <code>{k}</code>={String(v)}
        </span>
      ))}
    </div>
  )
}

function CompositeSection({ composite }) {
  const level = composite?.level || 'GREEN'
  return (
    <section id="semi-section-composite" className="scroll-mt-20">
      <h3 className="text-base font-bold mb-2">종합 신호</h3>
      <div className={`px-4 py-3 rounded ${LEVEL_BADGE[level]}`}>
        <div className="font-semibold">{level}</div>
        <div className="text-sm mt-1">{composite?.reason || '데이터 없음'}</div>
      </div>
      <div className="bg-amber-50 border border-amber-200 text-amber-800 text-xs px-3 py-2 rounded mt-3">
        ⚠ Phase 1 임시 규칙: 지표 1(반도체 가격)/지표 3(가이던스) 부재 — Phase 2에서 완전 활성화.
        <br />
        현재 룰: <code>capex ∈ (WARNING, ALERT) AND (memory_inventory WARNING OR market_breadth WARNING) → RED</code>
      </div>
    </section>
  )
}

function IndicatorSection({ id, payload, threshold = null }) {
  if (!payload) return null
  const level = payload.level || 'GREEN'
  return (
    <section id={`semi-section-${id}`} className="scroll-mt-20 mt-6">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-bold">{payload.label || id}</h3>
        <span className={`text-xs px-2 py-0.5 rounded font-semibold ${LEVEL_BADGE[level]}`}>
          {level}
        </span>
      </div>
      <div className="text-sm text-gray-700 mt-1">{payload.reason}</div>
      {_renderThresholdSummary(payload.threshold)}
      <div className="mt-3">
        <SemiIndicatorChart name={id} days={180} threshold={threshold} label={payload.label} />
      </div>
      {payload.recent_4 && payload.recent_4.length > 0 && (
        <div className="text-xs text-gray-600 mt-2">
          최근 4관측: {payload.recent_4.map((p) =>
            `${p.observed_at}=${typeof p.value === 'number' ? p.value.toFixed(2) : '—'}`
          ).join(' / ')}
        </div>
      )}
      {/* AI IPO 티커별 상세 */}
      {payload.details && (
        <table className="text-xs border w-full mt-3">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-2 py-1 text-left">티커</th>
              <th className="px-2 py-1 text-left">등급</th>
              <th className="px-2 py-1 text-right">수익률%</th>
              <th className="px-2 py-1 text-right">현재가</th>
              <th className="px-2 py-1 text-right">공모가</th>
              <th className="px-2 py-1 text-right">락업 D-N</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(payload.details).map(([t, d]) => (
              <tr key={t} className="border-t">
                <td className="px-2 py-1 font-mono">{t}</td>
                <td className="px-2 py-1">
                  <span className={`px-1.5 py-0.5 rounded ${LEVEL_BADGE[d.level]}`}>{d.level}</span>
                </td>
                <td className="px-2 py-1 text-right">
                  {typeof d.return_pct === 'number' ? d.return_pct.toFixed(1) : '—'}
                </td>
                <td className="px-2 py-1 text-right">
                  {d.current_price ? d.current_price.toFixed(2) : '—'}
                </td>
                <td className="px-2 py-1 text-right">
                  {d.ipo_price ? d.ipo_price.toFixed(2) : '—'}
                </td>
                <td className="px-2 py-1 text-right">
                  {d.dminus !== null && d.dminus !== undefined ? `D-${d.dminus}` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {/* HBM 공시 items */}
      {payload.items && payload.items.length > 0 && (
        <div className="mt-3">
          <div className="text-xs font-medium text-gray-700">매칭 공시:</div>
          <ul className="text-xs mt-1 space-y-1">
            {payload.items.map((it) => (
              <li key={it.rcept_no} className="flex gap-2">
                <span className="text-gray-500">{it.rcept_dt || '—'}</span>
                <span className="font-medium">{it.corp_name}</span>
                <a
                  href={it.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline"
                >
                  {it.report_nm}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
      {/* market_breadth 집중도 */}
      {id === 'market_breadth' && typeof payload.concentration === 'number' && (
        <div className="text-xs mt-2">
          삼성+SK 시총 집중도:{' '}
          <span className="font-semibold">{(payload.concentration * 100).toFixed(1)}%</span>
          {payload.concentration_meta?.is_252d_high && (
            <span className="ml-2 text-red-600">⚠ 252일 신고치</span>
          )}
          {payload.is_kospi_252d_high && (
            <span className="ml-2 text-amber-600">📈 KOSPI 252일 신고가</span>
          )}
        </div>
      )}
    </section>
  )
}

function SignalsSection({ signals }) {
  return (
    <section id="semi-section-signals" className="scroll-mt-20 mt-8">
      <h3 className="text-base font-bold mb-2">신호 이력</h3>
      {!signals || signals.length === 0 ? (
        <div className="text-sm text-gray-500">최근 신호 없음</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs border">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-2 py-1">시각</th>
                <th className="text-left px-2 py-1">지표</th>
                <th className="text-left px-2 py-1">등급</th>
                <th className="text-left px-2 py-1">메시지</th>
              </tr>
            </thead>
            <tbody>
              {signals.map((s) => (
                <tr key={s.id} className="border-t align-top">
                  <td className="px-2 py-1 text-[11px] text-gray-500 whitespace-nowrap">
                    {s.fired_at?.slice(0, 19)}
                  </td>
                  <td className="px-2 py-1 font-mono text-[11px]">{s.indicator_name}</td>
                  <td className="px-2 py-1">
                    <span className={`px-1.5 py-0.5 rounded ${LEVEL_BADGE[s.level] || ''}`}>
                      {s.level}
                    </span>
                  </td>
                  <td className="px-2 py-1">{s.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export default function SemiconductorDetailModal({ dashboard, signals, onClose, onRefresh }) {
  const composite = dashboard?.composite || {}
  const indicators = dashboard?.indicators || {}

  const onKey = useCallback((e) => {
    if (e.key === 'Escape') onClose?.()
  }, [onClose])

  useEffect(() => {
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onKey])

  const onBackdrop = (e) => {
    if (e.target === e.currentTarget) onClose?.()
  }

  // 지표별 임계값 추출 (차트 ReferenceLine용)
  const memoryAlertTh = indicators?.memory_inventory?.threshold?.days_alert_threshold || null
  const adrTh = indicators?.market_breadth?.threshold?.adr20_warning || null

  return (
    <div
      className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center overflow-y-auto p-2 sm:p-6"
      onClick={onBackdrop}
    >
      <div className="bg-white rounded-lg shadow-xl w-full max-w-5xl my-4">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-4 py-3 flex items-center justify-between rounded-t-lg z-10">
          <h2 className="text-lg font-bold">반도체 사이클 모니터링 — 상세</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-2xl text-gray-500 hover:text-gray-800 leading-none"
            aria-label="닫기"
          >×</button>
        </div>

        <div className="flex flex-col md:flex-row">
          {/* Left nav */}
          <nav className="md:w-56 md:sticky md:top-12 self-start border-b md:border-b-0 md:border-r p-3 text-sm">
            <ul className="space-y-1">
              {NAV_ITEMS.map((it) => (
                <li key={it.id}>
                  <button
                    type="button"
                    onClick={() => _scrollTo(it.id)}
                    className="text-left text-gray-700 hover:text-blue-600 w-full"
                  >
                    {it.label}
                  </button>
                </li>
              ))}
            </ul>
          </nav>

          {/* Body */}
          <div className="flex-1 p-4 space-y-4">
            <CompositeSection composite={composite} />
            <IndicatorSection
              id="hyperscaler_capex"
              payload={indicators.hyperscaler_capex}
            />
            <IndicatorSection
              id="memory_inventory"
              payload={indicators.memory_inventory}
              threshold={memoryAlertTh}
            />
            <IndicatorSection id="hbm_contracts" payload={indicators.hbm_contracts} />
            <IndicatorSection id="ai_ipo" payload={indicators.ai_ipo} />
            <IndicatorSection
              id="market_breadth"
              payload={indicators.market_breadth}
              threshold={adrTh}
            />

            <SignalsSection signals={signals} />

            <section id="semi-section-thresholds" className="scroll-mt-20 mt-8 border-t pt-4">
              <SemiThresholdsPanel />
            </section>
          </div>
        </div>

        <div className="border-t px-4 py-2 flex justify-between text-xs text-gray-500">
          <span>마지막 갱신: {dashboard?.composite ? new Date().toLocaleString('ko-KR') : '—'}</span>
          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              className="text-blue-600 hover:underline"
            >
              새로고침
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
