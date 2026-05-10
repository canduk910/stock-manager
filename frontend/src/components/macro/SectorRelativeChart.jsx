/**
 * SectorRelativeChart — 섹터 추세-강도 산점도 (2026-05-10 골든/데드크로스 직관화).
 *
 * 옛 기준(trend_days × z-score)을 유지하되 한국 투자자 친숙 용어로 라벨 직관화:
 *   x축 = SMA20 cross 경과일 (부호 = 추세 방향, 절댓값 = 지속 일수)
 *         양수 = 골든크로스 N일째 / 음수 = 데드크로스 N일째
 *   y축 = 1Y 수익률 z-score (전체 섹터 평균 대비 상대 강도, ±3 cap)
 *
 * 4분면 (한국식):
 *   (+x, +y) 추세 가속  — 골든크로스 + 평균↑ → 따라가기
 *   (-x, +y) 전환 직전  — 데드크로스인데도 평균↑ → 돌아설 가능성
 *   (+x, -y) 추세 약화  — 골든크로스인데 평균↓ → 멈출 위험
 *   (-x, -y) 약세 가속  — 데드크로스 + 평균↓ → 피하기
 *
 * 백엔드: data.sectors[].trend_days, intensity_z (z-score는 시장별로 별도 정규화)
 */
import { useMemo } from 'react'
import {
  ResponsiveContainer, ScatterChart, Scatter,
  XAxis, YAxis, ZAxis, CartesianGrid, Tooltip,
  ReferenceLine, ReferenceArea, Cell,
} from 'recharts'

// 섹터 매핑: name_ko/name 키워드 → {icon, color (Tailwind hex)}
// US 11종 + KR 13종 통합 매핑(키워드 기반 부분일치)
const SECTOR_STYLE = [
  { match: /기술|반도체|Tech|Semi/i,         icon: '💻', color: '#6366f1' }, // indigo-500
  { match: /금융|은행|Bank|Financial/i,        icon: '🏦', color: '#2563eb' }, // blue-600
  { match: /헬스|바이오|Health|Pharma/i,       icon: '⚕️', color: '#14b8a6' }, // teal-500
  { match: /에너지|화학|Energy|Chemical/i,     icon: '⚡', color: '#f59e0b' }, // amber-500
  { match: /산업|건설|Industrial|Construct/i,  icon: '🏭', color: '#64748b' }, // slate-500
  { match: /임의소비|경기소비|Discretionary/i, icon: '🛍️', color: '#ec4899' }, // pink-500
  { match: /필수소비|Staples/i,                icon: '🛒', color: '#84cc16' }, // lime-500
  { match: /유틸|Utilit/i,                     icon: '💡', color: '#a855f7' }, // purple-500
  { match: /부동산|Real|REIT/i,                icon: '🏠', color: '#f97316' }, // orange-500
  { match: /소재|철강|Material|Steel/i,        icon: '⛏️', color: '#78716c' }, // stone-500
  { match: /통신|Communication|Media|엔터/i,   icon: '📡', color: '#06b6d4' }, // cyan-500
  { match: /2차전지|Battery/i,                 icon: '🔋', color: '#10b981' }, // emerald-500
  { match: /자동차|Auto/i,                     icon: '🚗', color: '#8b5cf6' }, // violet-500
  { match: /운송|물류|Transport/i,             icon: '🚚', color: '#0ea5e9' }, // sky-500
]

const DEFAULT_STYLE = { icon: '◆', color: '#9ca3af' }

function styleFor(sector) {
  const label = sector.name_ko || sector.name || ''
  for (const s of SECTOR_STYLE) {
    if (s.match.test(label)) return s
  }
  return DEFAULT_STYLE
}

const fmt = (v, d = 2) => (v != null ? v.toFixed(d) : '-')

// 4분면 컨셉 라벨
function quadrantOf(x, y) {
  if (x == null || y == null) return null
  if (x >= 0 && y >= 0) return { label: '추세 가속', color: '#16a34a' }
  if (x < 0 && y >= 0)  return { label: '전환 직전', color: '#2563eb' }
  if (x >= 0 && y < 0)  return { label: '추세 약화', color: '#ea580c' }
  return { label: '약세 가속', color: '#dc2626' }
}

// 추세 라벨 (골든크로스/데드크로스 N일째)
function trendLabel(trendDays) {
  if (trendDays == null || trendDays === 0) return '추세 미확인'
  const n = Math.abs(trendDays)
  return trendDays > 0 ? `🟢 골든크로스 ${n}일째` : `🔴 데드크로스 ${n}일째`
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  const q = quadrantOf(p.trend_days, p.intensity_z)
  return (
    <div className="bg-white border rounded shadow px-3 py-2 text-xs min-w-[180px]">
      <div className="font-bold text-gray-900 mb-1.5 flex items-center gap-2 flex-wrap">
        <span>{p._style.icon} {p.name_ko || p.name}</span>
        {q && (
          <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ backgroundColor: q.color + '20', color: q.color }}>
            {q.label}
          </span>
        )}
      </div>
      <div className="text-gray-600">{trendLabel(p.trend_days)}</div>
      <div className="text-gray-600">섹터평균 대비: <span className="font-mono">{fmt(p.intensity_z, 2)}σ</span></div>
      <div className="text-gray-600">1Y 수익률: <span className="font-mono">{fmt(p.return_1y, 1)}%</span></div>
    </div>
  )
}

export default function SectorRelativeChart({ data, title = '섹터 추세-강도' }) {
  const points = useMemo(() => {
    if (!data?.sectors?.length) return []
    return data.sectors.map((s) => ({
      ...s,
      _style: styleFor(s),
    }))
  }, [data])

  // 동적 도메인 — 점들이 가운데 모이지 않도록 max(|값|) × 1.18 padding.
  // 최소 도메인 보장: x ±30일(추세 미확인 다수일 때) / y ±0.5σ
  const { xDomain, yDomain } = useMemo(() => {
    const xs = points.map((p) => p.trend_days).filter((v) => Number.isFinite(v))
    const ys = points.map((p) => p.intensity_z).filter((v) => Number.isFinite(v))
    const xAbs = xs.length ? Math.max(30, ...xs.map(Math.abs)) : 30
    const yAbs = ys.length ? Math.max(0.5, ...ys.map(Math.abs)) : 1
    return {
      xDomain: [-xAbs * 1.18, xAbs * 1.18],
      yDomain: [-yAbs * 1.18, yAbs * 1.18],
    }
  }, [points])

  if (!points.length) return null

  const hasData = points.some((p) => p.trend_days != null && p.intensity_z != null)
  if (!hasData) return null

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm h-full">
      <div className="flex items-start justify-between mb-2 flex-wrap gap-2">
        <div>
          <div className="text-sm font-medium text-gray-700">{title}</div>
          <div className="text-[11px] text-gray-500 mt-0.5">
            x축 = 골든/데드크로스 경과일 · y축 = 섹터 평균 대비 강도(σ)
          </div>
        </div>
        {/* 4분면 범례 */}
        <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[10px]">
          <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-sm" style={{ backgroundColor: '#16a34a' }} />↗ 추세 가속</span>
          <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-sm" style={{ backgroundColor: '#2563eb' }} />↖ 전환 직전</span>
          <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-sm" style={{ backgroundColor: '#ea580c' }} />↘ 추세 약화</span>
          <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-sm" style={{ backgroundColor: '#dc2626' }} />↙ 약세 가속</span>
        </div>
      </div>
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 24, right: 32, bottom: 28, left: 8 }}>
            <CartesianGrid stroke="#f0f0f0" />
            {/* 4분면 음영 + 큰 컨셉 라벨 (각 분면 안쪽) */}
            <ReferenceArea
              x1={0} x2={xDomain[1]} y1={0} y2={yDomain[1]}
              fill="#22c55e" fillOpacity={0.06}
              label={{
                value: '추세 가속 ↗',
                position: 'insideTopRight',
                fill: '#16a34a', fontSize: 12, fontWeight: 600, opacity: 0.55,
              }}
            />
            <ReferenceArea
              x1={xDomain[0]} x2={0} y1={0} y2={yDomain[1]}
              fill="#3b82f6" fillOpacity={0.06}
              label={{
                value: '전환 직전 ↖',
                position: 'insideTopLeft',
                fill: '#2563eb', fontSize: 12, fontWeight: 600, opacity: 0.55,
              }}
            />
            <ReferenceArea
              x1={0} x2={xDomain[1]} y1={yDomain[0]} y2={0}
              fill="#f97316" fillOpacity={0.06}
              label={{
                value: '추세 약화 ↘',
                position: 'insideBottomRight',
                fill: '#ea580c', fontSize: 12, fontWeight: 600, opacity: 0.55,
              }}
            />
            <ReferenceArea
              x1={xDomain[0]} x2={0} y1={yDomain[0]} y2={0}
              fill="#ef4444" fillOpacity={0.06}
              label={{
                value: '약세 가속 ↙',
                position: 'insideBottomLeft',
                fill: '#dc2626', fontSize: 12, fontWeight: 600, opacity: 0.55,
              }}
            />
            <ReferenceLine x={0} stroke="#9ca3af" strokeDasharray="3 3" />
            <ReferenceLine y={0} stroke="#9ca3af" strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="trend_days"
              name="추세 경과일"
              domain={xDomain}
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => {
                const n = Math.abs(Math.round(v))
                if (n === 0) return '0'
                return v > 0 ? `🟢${n}` : `🔴${n}`
              }}
              label={{ value: '🟢 골든크로스 / 🔴 데드크로스 N일째', position: 'insideBottom', offset: -10, fontSize: 11, fill: '#6b7280' }}
            />
            <YAxis
              type="number"
              dataKey="intensity_z"
              name="섹터 평균 대비 강도"
              domain={yDomain}
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => `${v >= 0 ? '+' : ''}${v.toFixed(1)}σ`}
              label={{ value: '평균 대비 ±σ', angle: -90, position: 'insideLeft', offset: 15, fontSize: 11, fill: '#6b7280' }}
            />
            <ZAxis range={[110, 110]} />
            <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />
            <Scatter data={points} isAnimationActive={false}>
              {points.map((p, i) => (
                <Cell key={i} fill={p._style.color} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      {/* 지표 정의 설명 */}
      <div className="mt-3 p-2.5 bg-gray-50 rounded text-[11px] text-gray-600 leading-relaxed">
        <div className="mb-1">
          <span className="font-semibold text-gray-700">🟢 골든크로스</span> 종가가 20일 이동평균선을 <span className="text-red-600 font-medium">위로 돌파</span>한 후 유지된 일수.
          <span className="text-gray-400 mx-1">/</span>
          <span className="font-semibold text-gray-700">🔴 데드크로스</span> 종가가 20일선을 <span className="text-blue-600 font-medium">아래로 깬</span> 후 유지된 일수.
        </div>
        <div>
          <span className="font-semibold text-gray-700">평균 대비 ±σ</span> 1년 수익률을 전체 섹터 평균/표준편차로 표준화 (z-score). <span className="font-mono">+1σ</span> = 평균보다 1표준편차 우위, <span className="font-mono">-1σ</span> = 열위.
        </div>
      </div>
      {/* 섹터 범례 (아이콘 + 한글명) */}
      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px]">
        {points.map((p) => (
          <span key={p.symbol} className="inline-flex items-center gap-1">
            <span
              className="inline-block w-2 h-2 rounded-full"
              style={{ backgroundColor: p._style.color }}
            />
            <span>{p._style.icon}</span>
            <span className="text-gray-700">{p.name_ko || p.name}</span>
          </span>
        ))}
      </div>
    </div>
  )
}
