/**
 * SectorRelativeChart — 섹터 상대평가 산점도 (R3, 2026-05-04)
 *
 * 도메인 자문(MacroSentinel + ValueScreener) 합의:
 *   x축 = SMA20 cross 기반 추세 시작점 경과일 (부호 포함, ±365)
 *   y축 = 1Y 누적수익률을 모든 섹터 분포 z-score로 표준화 (±3)
 *
 * 4분면 라벨링:
 *   (+x, +y) 모멘텀강세  / (+x, -y) 약세지속
 *   (-x, +y) 반등초기   / (-x, -y) 약세초기
 *
 * 백엔드 응답: data.sectors[].trend_days, intensity_z, name_ko, symbol
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

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className="bg-white border rounded shadow px-3 py-2 text-xs">
      <div className="font-bold text-gray-900 mb-1">
        {p._style.icon} {p.name_ko || p.name}
      </div>
      <div className="text-gray-600">지속기간: <span className="font-mono">{p.trend_days}일</span></div>
      <div className="text-gray-600">강도(z-score): <span className="font-mono">{fmt(p.intensity_z, 2)}</span></div>
      <div className="text-gray-600">1Y 수익률: <span className="font-mono">{fmt(p.return_1y, 1)}%</span></div>
    </div>
  )
}

export default function SectorRelativeChart({ data, title = '섹터 상대평가' }) {
  const points = useMemo(() => {
    if (!data?.sectors?.length) return []
    return data.sectors.map((s) => ({
      ...s,
      _style: styleFor(s),
    }))
  }, [data])

  if (!points.length) return null

  // 모든 점이 trend_days/intensity_z 중 하나라도 없으면 표시 보류
  const hasData = points.some((p) => p.trend_days != null && p.intensity_z != null)
  if (!hasData) return null

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <div>
          <div className="text-sm font-medium text-gray-700">{title}</div>
          <div className="text-[10px] text-gray-400">
            x: SMA20 cross 경과일(부호 포함, ±365) · y: 1Y 수익률 z-score(±3)
          </div>
        </div>
        <div className="text-[10px] text-gray-500 flex flex-wrap gap-x-3">
          <span>↗ 모멘텀강세</span>
          <span>↘ 약세지속</span>
          <span>↖ 반등초기</span>
          <span>↙ 약세초기</span>
        </div>
      </div>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 16, right: 24, bottom: 16, left: 8 }}>
            <CartesianGrid stroke="#f0f0f0" />
            {/* 4분면 음영 */}
            <ReferenceArea x1={0} x2={365} y1={0} y2={3} fill="#22c55e" fillOpacity={0.05} />
            <ReferenceArea x1={-365} x2={0} y1={0} y2={3} fill="#3b82f6" fillOpacity={0.05} />
            <ReferenceArea x1={0} x2={365} y1={-3} y2={0} fill="#f97316" fillOpacity={0.05} />
            <ReferenceArea x1={-365} x2={0} y1={-3} y2={0} fill="#ef4444" fillOpacity={0.05} />
            <ReferenceLine x={0} stroke="#9ca3af" strokeDasharray="3 3" />
            <ReferenceLine y={0} stroke="#9ca3af" strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="trend_days"
              name="지속기간"
              domain={[-365, 365]}
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => `${v}일`}
            />
            <YAxis
              type="number"
              dataKey="intensity_z"
              name="강도"
              domain={[-3, 3]}
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => v.toFixed(1)}
            />
            <ZAxis range={[60, 60]} />
            <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />
            <Scatter data={points} isAnimationActive={false}>
              {points.map((p, i) => (
                <Cell key={i} fill={p._style.color} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      {/* 섹터 범례 (아이콘 + 한글명) */}
      <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-[11px]">
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
