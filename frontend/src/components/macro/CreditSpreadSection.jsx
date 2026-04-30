/**
 * 하이일드 스프레드 섹션 (하워드 막스 프레임워크).
 *
 * 데이터:
 *   1순위: FRED OAS (ICE BofA US High Yield OAS, BAMLH0A0HYM2)
 *   2순위: HYG/LQD ETF 수익률 차이 (yfinance)
 *
 * 하워드 막스 시계추:
 *   OAS < 3.5%: 탐욕 (위험 둔감) → 수비 전환
 *   OAS 3.5~7%: 정상
 *   OAS > 7%: 공포 (패닉) → 공격적 매수
 */
import { useMemo } from 'react'
import {
  ResponsiveContainer, AreaChart, Area,
  XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine,
} from 'recharts'
import LoadingSpinner from '../common/LoadingSpinner'
import ErrorAlert from '../common/ErrorAlert'

const fmt = (v) =>
  v != null
    ? v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : '-'

const DIRECTION_STYLE = {
  widening: { bg: 'bg-red-100', text: 'text-red-700', label: '확대 중' },
  narrowing: { bg: 'bg-emerald-100', text: 'text-emerald-700', label: '축소 중' },
  stable: { bg: 'bg-gray-100', text: 'text-gray-600', label: '안정' },
}

const SENTIMENT_CONFIG = {
  greed: {
    label: '탐욕 (위험 둔감)',
    strategy: '수비적 포지션 전환',
    icon: '🔴',
    bg: 'bg-red-50 border-red-200',
    text: 'text-red-700',
    strategyText: 'text-red-600',
    desc: '투자자들이 위험에 둔감해졌습니다. 부도 위험이 있는 채권에도 적은 프리미엄만 요구하고 있어, 시장 과열 신호입니다.',
    barColor: 'bg-red-500',
  },
  normal: {
    label: '정상',
    strategy: '균형 유지',
    icon: '🟡',
    bg: 'bg-amber-50 border-amber-200',
    text: 'text-amber-700',
    strategyText: 'text-amber-600',
    desc: '시장이 위험을 적절한 수준으로 가격에 반영하고 있습니다. 정상적인 위험 프리미엄 구간입니다.',
    barColor: 'bg-amber-400',
  },
  fear: {
    label: '공포 (패닉)',
    strategy: '공격적 매수 기회',
    icon: '🟢',
    bg: 'bg-emerald-50 border-emerald-200',
    text: 'text-emerald-700',
    strategyText: 'text-emerald-600',
    desc: '투자자들이 극도의 두려움에 빠져 우량 자산으로만 도피하고 있습니다. 실제 부도 확률보다 가격이 과도하게 하락한 매수 기회입니다.',
    barColor: 'bg-emerald-500',
  },
}

/* 게이지 바 — OAS 위치를 0~12% 구간에 시각화 */
function OasGauge({ oas }) {
  if (oas == null) return null
  const pct = Math.min(Math.max(oas / 12 * 100, 0), 100)
  const greedPct = 3.5 / 12 * 100
  const fearPct = 7.0 / 12 * 100

  return (
    <div className="mt-2">
      <div className="relative h-4 rounded-full overflow-hidden bg-gray-100">
        {/* 구간 배경 */}
        <div className="absolute inset-y-0 left-0 bg-red-200" style={{ width: `${greedPct}%` }} />
        <div className="absolute inset-y-0 bg-amber-100" style={{ left: `${greedPct}%`, width: `${fearPct - greedPct}%` }} />
        <div className="absolute inset-y-0 right-0 bg-emerald-200" style={{ left: `${fearPct}%` }} />
        {/* 현재 위치 마커 */}
        <div
          className="absolute top-0 bottom-0 w-1 bg-gray-900 rounded-full shadow-sm"
          style={{ left: `${pct}%`, transform: 'translateX(-50%)' }}
        />
      </div>
      <div className="flex justify-between text-[10px] text-gray-400 mt-0.5 px-0.5">
        <span>0%</span>
        <span className="text-red-400">3.5%</span>
        <span className="text-amber-500">탐욕 ← 정상 → 공포</span>
        <span className="text-emerald-500">7%</span>
        <span>12%</span>
      </div>
    </div>
  )
}

export default function CreditSpreadSection({ data, loading, error }) {
  if (loading) return <LoadingSpinner message="크레딧 스프레드 로딩 중..." />
  if (error) return <ErrorAlert message={error} />
  if (!data) return null

  const cs = data.credit_spread || data
  const {
    hyg_yield, lqd_yield, spread, spread_direction, history,
    oas_current, oas_history, oas_sentiment, oas_percentile,
  } = cs
  const dirStyle = DIRECTION_STYLE[spread_direction] || DIRECTION_STYLE.stable
  const sentiment = SENTIMENT_CONFIG[oas_sentiment] || null

  // OAS 차트 데이터: 주 1회 샘플링으로 간소화
  const oasChartData = useMemo(() => {
    if (!oas_history?.length) return []
    const step = Math.max(1, Math.floor(oas_history.length / 260))
    return oas_history.filter((_, i) => i % step === 0 || i === oas_history.length - 1)
  }, [oas_history])

  return (
    <section>
      <h2 className="text-lg font-semibold text-gray-900 mb-3">하이일드 스프레드</h2>

      {/* 하워드 막스 시계추 카드 */}
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
                <div className="text-xs text-gray-400 mt-0.5">5년 백분위 {oas_percentile}%</div>
              )}
            </div>
          </div>
          <OasGauge oas={oas_current} />
        </div>
      )}

      {/* ETF 수익률 3카드 */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <div className="text-sm font-medium text-gray-500 mb-1">HYG 수익률</div>
          <div className="text-2xl font-bold text-gray-900">{fmt(hyg_yield)}%</div>
        </div>
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <div className="text-sm font-medium text-gray-500 mb-1">LQD 수익률</div>
          <div className="text-2xl font-bold text-gray-900">{fmt(lqd_yield)}%</div>
        </div>
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <div className="text-sm font-medium text-gray-500 mb-1">스프레드 (HYG-LQD)</div>
          <div className="text-2xl font-bold text-gray-900">{fmt(spread)}%</div>
          <span className={`inline-block mt-1 px-2 py-0.5 rounded text-xs font-medium ${dirStyle.bg} ${dirStyle.text}`}>
            {dirStyle.label}
          </span>
        </div>
      </div>

      {/* OAS 시계열 차트 (FRED) */}
      {oasChartData.length > 0 && (
        <div className="rounded-lg border bg-white p-4 shadow-sm mb-4">
          <div className="text-sm font-medium text-gray-500 mb-2">HY OAS 추이 (5년, FRED)</div>
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
                <ReferenceLine y={3.5} stroke="#ef4444" strokeDasharray="4 4" label={{ value: '탐욕 3.5%', fontSize: 10, fill: '#ef4444' }} />
                <ReferenceLine y={7.0} stroke="#10b981" strokeDasharray="4 4" label={{ value: '공포 7%', fontSize: 10, fill: '#10b981' }} />
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
            OAS(Option-Adjusted Spread) = 하이일드 채권 금리 - 국고채 금리. 상승 = 공포 / 하락 = 탐욕
          </div>
        </div>
      )}

      {/* HYG/LQD 비율 시계열 (기존) */}
      {history?.length > 0 && (
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <div className="text-sm font-medium text-gray-500 mb-2">HYG/LQD 비율 추이</div>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={history}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                <YAxis tick={{ fontSize: 12 }} domain={['auto', 'auto']} tickFormatter={(v) => v.toFixed(3)} />
                <Tooltip
                  formatter={(v) => [v.toFixed(4), 'HYG/LQD']}
                  labelFormatter={(l) => l}
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                />
                <defs>
                  <linearGradient id="creditGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f97316" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#f97316" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <Area type="monotone" dataKey="ratio" stroke="#f97316" strokeWidth={1.5} fill="url(#creditGrad)" dot={false} isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="text-xs text-gray-400 mt-1">
            비율 상승 = 스프레드 확대(위험 증가) / 비율 하락 = 스프레드 축소(안정)
          </div>
        </div>
      )}
    </section>
  )
}
