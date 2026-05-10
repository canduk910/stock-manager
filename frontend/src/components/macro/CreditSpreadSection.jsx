/**
 * 하이일드 스프레드 섹션 (하워드 막스 시계추 — 백분위 5단계 + 전 기간 baseline).
 *
 * 데이터:
 *   1순위: FRED HY OAS (BAMLH0A0HYM2, ICE BofA US High Yield OAS, 1996-12~)
 *   보조:  FRED IG OAS (BAMLC0A0CM, Investment Grade Corporate OAS) + HY-IG 스프레드
 *
 * 하워드 막스 시계추 백분위 5단계 (전 기간 baseline 약 28년):
 *   < 10  → extreme_greed (위험 둔감 정점)
 *   < 30  → greed
 *   < 70  → normal
 *   < 90  → fear
 *   >= 90 → extreme_fear (패닉, 매집 기회)
 * + OAS > 10% 절대 안전장치 (역사적 단절 감지) → extreme_fear 강제
 */
import { useMemo } from 'react'
import {
  ResponsiveContainer, AreaChart, Area,
  XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine, ReferenceArea,
} from 'recharts'
import LoadingSpinner from '../common/LoadingSpinner'
import ErrorAlert from '../common/ErrorAlert'
import { computeEventRows, makeLabelRenderer } from './EventLabelsOverlay'

const fmt = (v, d = 2) =>
  v != null
    ? v.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d })
    : '-'

const SENTIMENT_CONFIG = {
  extreme_greed: {
    label: '극단적 탐욕 (위험 둔감 정점)',
    strategy: '대폭 수비적 전환',
    icon: '🚨',
    bg: 'bg-red-100 border-red-300',
    text: 'text-red-800',
    strategyText: 'text-red-700',
    desc: '백분위 10% 미만. 신용 사이클의 정점에서 위험을 거의 가격에 반영하지 않은 상태입니다. 다음 사이클 전환 시 고통스러운 조정이 따르는 영역입니다.',
    barColor: 'bg-red-600',
  },
  greed: {
    label: '탐욕 (위험 둔감)',
    strategy: '수비적 포지션 전환',
    icon: '🔴',
    bg: 'bg-red-50 border-red-200',
    text: 'text-red-700',
    strategyText: 'text-red-600',
    desc: '백분위 10~30%. 투자자들이 위험에 둔감해졌습니다. 부도 위험이 있는 채권에도 적은 프리미엄만 요구하고 있어, 시장 과열 신호입니다.',
    barColor: 'bg-red-500',
  },
  normal: {
    label: '정상',
    strategy: '균형 유지',
    icon: '🟡',
    bg: 'bg-amber-50 border-amber-200',
    text: 'text-amber-700',
    strategyText: 'text-amber-600',
    desc: '백분위 30~70%. 시장이 위험을 적절한 수준으로 가격에 반영하고 있습니다. 정상적인 위험 프리미엄 구간입니다.',
    barColor: 'bg-amber-400',
  },
  fear: {
    label: '공포',
    strategy: '선별적 매수 검토',
    icon: '🟢',
    bg: 'bg-emerald-50 border-emerald-200',
    text: 'text-emerald-700',
    strategyText: 'text-emerald-600',
    desc: '백분위 70~90%. 투자자들이 위험을 회피하고 있습니다. 우량 자산 도피 심화 — 선별적 진입 기회입니다.',
    barColor: 'bg-emerald-500',
  },
  extreme_fear: {
    label: '극단적 공포 (매집 기회)',
    strategy: '적극 매수 검토',
    icon: '🎯',
    bg: 'bg-emerald-100 border-emerald-300',
    text: 'text-emerald-800',
    strategyText: 'text-emerald-700',
    desc: '백분위 90% 초과 또는 OAS > 10%. 시장이 극도의 두려움에 빠진 매집의 영역입니다. 실제 부도 확률보다 가격이 과도하게 하락한 역사적 매수 기회입니다.',
    barColor: 'bg-emerald-600',
  },
}

/* 백분위 게이지 — 0~100 백분위 축으로 표시 (하워드 막스 친화적) */
function PercentileGauge({ percentile }) {
  if (percentile == null) return null
  const pct = Math.min(Math.max(percentile, 0), 100)

  return (
    <div className="mt-2">
      <div className="relative h-4 rounded-full overflow-hidden bg-gray-100">
        {/* 5단계 구간 배경: 빨강 → 적색 → 노랑 → 초록 → 진초록 */}
        <div className="absolute inset-y-0 left-0 bg-red-300" style={{ width: '10%' }} />
        <div className="absolute inset-y-0 bg-red-200" style={{ left: '10%', width: '20%' }} />
        <div className="absolute inset-y-0 bg-amber-100" style={{ left: '30%', width: '40%' }} />
        <div className="absolute inset-y-0 bg-emerald-200" style={{ left: '70%', width: '20%' }} />
        <div className="absolute inset-y-0 bg-emerald-300" style={{ left: '90%', width: '10%' }} />
        {/* 현재 위치 마커 */}
        <div
          className="absolute top-0 bottom-0 w-1 bg-gray-900 rounded-full shadow-sm"
          style={{ left: `${pct}%`, transform: 'translateX(-50%)' }}
        />
      </div>
      <div className="flex justify-between text-[10px] text-gray-400 mt-0.5 px-0.5">
        <span>0</span>
        <span className="text-red-500">10</span>
        <span className="text-red-400">30</span>
        <span className="text-amber-500">탐욕 ← 정상 → 공포</span>
        <span className="text-emerald-500">70</span>
        <span className="text-emerald-600">90</span>
        <span>100 백분위</span>
      </div>
    </div>
  )
}

export default function CreditSpreadSection({ data, loading, error }) {
  if (loading) return <LoadingSpinner message="크레딧 스프레드 로딩 중..." />
  if (error) return <ErrorAlert message={error} />
  if (!data) return null

  // 명시적 fallback 제거: API 응답은 항상 { credit_spread: {...} } 형식
  const cs = data?.credit_spread || data
  if (!cs) return null

  const {
    oas_current, oas_history_10y, oas_history_5y, oas_stats, oas_sentiment, oas_percentile,
    ig_current, hy_ig_spread,
    partial_failure,
    events,
  } = cs

  const sentiment = SENTIMENT_CONFIG[oas_sentiment] || null

  // OAS 시계열 (FRED 공식, 자체 oas_history_store FIFO 누적) — 주 단위 샘플링.
  // 2026-04~ ICE BofA 라이센스 변경으로 FRED는 ~3년만 반환. 매일 +1일치 누적되어
  // 7년 후 자연스럽게 10년 시계열로 확장됨.
  const oasChartData = useMemo(() => {
    const src = oas_history_10y || oas_history_5y || cs.oas_history || []
    if (!src.length) return []
    const step = Math.max(1, Math.floor(src.length / 520))
    return src.filter((_, i) => i % step === 0 || i === src.length - 1)
  }, [oas_history_10y, oas_history_5y, cs.oas_history])

  // 백분위 임계 → OAS 절댓값 매핑 (시계열 ReferenceLine 동적)
  const refLines = useMemo(() => {
    if (!oas_stats) return []
    const lines = []
    const map = [
      { p: 'p10', label: '백분위 10', color: '#dc2626' },
      { p: 'p25', label: '백분위 30', color: '#f97316' },  // p25는 30 근사
      { p: 'p75', label: '백분위 70', color: '#10b981' },
      { p: 'p90', label: '백분위 90', color: '#059669' },
    ]
    for (const m of map) {
      const v = oas_stats[m.p]
      if (v != null) lines.push({ y: v, label: `${m.label} ${v.toFixed(2)}%`, color: m.color })
    }
    return lines
  }, [oas_stats])

  const hyIgPanic = hy_ig_spread != null && hy_ig_spread > 5.0

  // 음영 좌표 snap만 수행. 라벨 충돌 회피는 EventLabelsOverlay가 픽셀 공간에서 처리.
  const snappedEvents = useMemo(() => {
    if (!events || !oasChartData.length) return { recessions: [], bear_markets: [] }
    const dataDates = new Set(oasChartData.map((d) => d.date))
    const sorted = [...dataDates].sort()
    const minD = sorted[0]
    const maxD = sorted[sorted.length - 1]
    const snap = (target) => {
      if (target < sorted[0]) return sorted[0]
      if (target > sorted[sorted.length - 1]) return sorted[sorted.length - 1]
      if (dataDates.has(target)) return target
      let best = sorted[0]
      let bestDiff = Math.abs(new Date(target) - new Date(best))
      for (const d of sorted) {
        const diff = Math.abs(new Date(target) - new Date(d))
        if (diff < bestDiff) { best = d; bestDiff = diff }
      }
      return best
    }
    const adapt = (e) => {
      if (e.end < minD || e.start > maxD) return null
      const x1 = snap(e.start)
      const x2 = snap(e.end)
      if (!x1 || !x2 || x1 === x2) return null
      return { ...e, x1, x2 }
    }
    const recs = (events.recessions || []).map(adapt).filter(Boolean)
    const bears = (events.bear_markets || []).map(adapt).filter(Boolean)
    return { recessions: recs, bear_markets: bears }
  }, [events, oasChartData])

  const csRowMap = useMemo(() => computeEventRows([
    ...snappedEvents.bear_markets.map(b => ({ kind: 'bear', x1: b.x1, x2: b.x2, label: b.label })),
    ...snappedEvents.recessions.map(r => ({ kind: 'rec', x1: r.x1, x2: r.x2, label: r.label })),
  ]), [snappedEvents])

  return (
    <section>
      <h2 className="text-lg font-semibold text-gray-900 mb-3">하이일드 스프레드</h2>

      {/* 부분 실패 안내 */}
      {partial_failure?.length > 0 && (
        <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1 mb-3">
          ⚠ 일부 데이터 미수집: {partial_failure.join(', ')}
        </div>
      )}

      {/* 하워드 막스 시계추 카드 (백분위 게이지) */}
      {oas_current != null && sentiment && (
        <div className={`rounded-xl border p-4 mb-4 ${sentiment.bg}`}>
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-lg">{sentiment.icon}</span>
                <span className={`text-sm font-bold ${sentiment.text}`}>
                  하워드 막스 시계추: {sentiment.label}
                </span>
              </div>
              <div className="text-xs text-gray-600 mb-2">{sentiment.desc}</div>
              <div className={`text-xs font-semibold ${sentiment.strategyText}`}>
                전략: {sentiment.strategy}
              </div>
            </div>
            <div className="text-right shrink-0">
              <div className="text-2xl font-bold text-gray-900">{fmt(oas_current)}%</div>
              <div className="text-xs text-gray-500">HY OAS</div>
              {oas_percentile != null && (
                <div className="text-xs text-gray-700 mt-0.5 font-semibold">
                  백분위 {fmt(oas_percentile, 1)}%
                </div>
              )}
            </div>
          </div>
          <PercentileGauge percentile={oas_percentile} />
          {/* 절댓값 부제 */}
          {oas_stats && (
            <div className="text-[11px] text-gray-500 mt-2">
              현재 OAS = {fmt(oas_current)}%
              {oas_stats.mean != null && ` · 역사 평균 ${fmt(oas_stats.mean, 1)}%`}
              {oas_stats.max != null && ` · 정점 ${fmt(oas_stats.max, 1)}%`}
              {oas_stats.max_date && ` (${oas_stats.max_date})`}
              {' '}· baseline 1996-12 ~ 현재 (전 기간)
            </div>
          )}
        </div>
      )}

      {/* IG OAS / HY-IG 스프레드 보조 카드 */}
      {(ig_current != null || hy_ig_spread != null) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
          <div className="rounded-lg border bg-white p-4 shadow-sm">
            <div className="text-sm font-medium text-gray-500 mb-1">IG OAS (투자등급)</div>
            <div className="text-2xl font-bold text-gray-900">{fmt(ig_current)}%</div>
            <div className="text-xs text-gray-400 mt-1">FRED BAMLC0A0CM</div>
          </div>
          <div className={`rounded-lg border p-4 shadow-sm ${hyIgPanic ? 'bg-red-50 border-red-200' : 'bg-white'}`}>
            <div className="text-sm font-medium text-gray-500 mb-1">HY-IG 스프레드 (정크 디스카운트)</div>
            <div className="text-2xl font-bold text-gray-900">{fmt(hy_ig_spread)}%p</div>
            {hyIgPanic ? (
              <div className="text-xs text-red-700 font-semibold mt-1">
                ⚠ 정크 영역 패닉 (선별적 매수 시그널, &gt; 5%p)
              </div>
            ) : (
              <div className="text-xs text-gray-400 mt-1">정크 디스카운트 (HY OAS - IG OAS)</div>
            )}
          </div>
        </div>
      )}

      {/* OAS 시계열 차트 (FRED) — 백분위 임계선 동적 + 침체/약세장 음영 */}
      {oasChartData.length > 0 && (
        <div className="rounded-lg border bg-white p-4 shadow-sm mb-4">
          <div className="text-sm font-medium text-gray-500 mb-2">
            HY OAS 추이 (FRED)
            <span className="ml-2 text-[10px] text-gray-400">
              ■ 회색=NBER 침체 / ▼ 붉은색=S&amp;P -20% 약세장
            </span>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={oasChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                <YAxis tick={{ fontSize: 12 }} domain={['auto', 'auto']} tickFormatter={(v) => `${v}%`} />
                <Tooltip
                  formatter={(v) => [`${v.toFixed(2)}%`, 'HY OAS']}
                  labelFormatter={(l) => l}
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                />

                {/* 음영 + ReferenceArea label 콜백. 글로벌 row 할당으로 충돌 회피. */}
                {snappedEvents.bear_markets.map((b, i) => {
                  const { row, displayLabel } = csRowMap.rowDisplayFor('bear', b.x1, b.x2)
                  return (
                    <ReferenceArea
                      key={`bear-${i}`}
                      x1={b.x1}
                      x2={b.x2}
                      fill="#ef4444"
                      fillOpacity={0.10}
                      stroke="none"
                      ifOverflow="hidden"
                      label={makeLabelRenderer({ kind: 'bear', displayLabel, row, fill: '#b91c1c' })}
                    />
                  )
                })}
                {snappedEvents.recessions.map((r, i) => {
                  const { row, displayLabel } = csRowMap.rowDisplayFor('rec', r.x1, r.x2)
                  return (
                    <ReferenceArea
                      key={`rec-${i}`}
                      x1={r.x1}
                      x2={r.x2}
                      fill="#6b7280"
                      fillOpacity={0.18}
                      stroke="#374151"
                      strokeOpacity={0.3}
                      strokeDasharray="3 3"
                      ifOverflow="hidden"
                      label={makeLabelRenderer({ kind: 'rec', displayLabel, row, fill: '#374151' })}
                    />
                  )
                })}
                {refLines.map((rl, i) => (
                  <ReferenceLine
                    key={i}
                    y={rl.y}
                    stroke={rl.color}
                    strokeDasharray="4 4"
                    label={{ value: rl.label, fontSize: 10, fill: rl.color }}
                  />
                ))}
                <defs>
                  <linearGradient id="oasGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#6366f1" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <Area type="monotone" dataKey="oas" stroke="#6366f1" strokeWidth={1.5} fill="url(#oasGrad)" dot={false} isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="text-xs text-gray-400 mt-1">
            OAS(Option-Adjusted Spread) = 하이일드 채권 금리 - 국고채 금리. 임계선은 FRED 전 기간 baseline 백분위 기준.
            <span className="ml-2 text-amber-700">
              ※ ICE BofA 라이센스 정책 변경(2026-04~)으로 FRED API가 최근 ~3년만 반환. 매일 +1일치 자체 누적되어 시간이 지날수록 시계열 확장됩니다.
            </span>
          </div>
        </div>
      )}

    </section>
  )
}
