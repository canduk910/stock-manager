/**
 * 거시 팩터 5축 z-score 신호등 — RadarChart.
 *
 * RatioAnalysisSection.jsx의 RadarChart 패턴 재사용(번들 영향 0).
 * domain [-3, 3], |z|≥1.5(stressed) 강조. 한국 관례 색상은 막대형이 아니라
 * 레이더 채움이므로 단일 색 + |z| 강조 배지로 표현.
 */
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  ResponsiveContainer, Tooltip,
} from 'recharts'

const LEVEL_STYLE = {
  stressed: { text: 'text-red-700', bg: 'bg-red-50', border: 'border-red-200' },
  mild: { text: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200' },
  neutral: { text: 'text-gray-600', bg: 'bg-gray-50', border: 'border-gray-200' },
}

function levelStyle(level) {
  return LEVEL_STYLE[level] || LEVEL_STYLE.neutral
}

export default function FactorSignalRadar({ signalLights }) {
  const lights = signalLights || []
  if (lights.length === 0) {
    return (
      <div className="text-sm text-gray-500 text-center py-6">
        신호등 데이터 없음
      </div>
    )
  }

  // 레이더는 |z|를 반지름으로(0~3 cap), 부호/강도는 카드에서 표기
  const radarData = lights.map((s) => ({
    axis: s.label,
    z: Math.min(3, Math.abs(Number(s.z) || 0)),
    rawZ: Number(s.z) || 0,
  }))

  return (
    <div>
      <div className="w-full h-64">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={radarData} outerRadius="70%">
            <PolarGrid />
            <PolarAngleAxis dataKey="axis" tick={{ fontSize: 11, fill: '#4b5563' }} />
            <PolarRadiusAxis domain={[0, 3]} tick={{ fontSize: 10, fill: '#9ca3af' }} angle={90} />
            <Radar
              name="|z|"
              dataKey="z"
              stroke="#7c3aed"
              fill="#7c3aed"
              fillOpacity={0.35}
            />
            <Tooltip
              formatter={(v, _n, p) => {
                const raw = p?.payload?.rawZ
                return [`z = ${raw != null ? raw.toFixed(2) : '-'}`, '표준화 점수']
              }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* 축별 z-score 칩 (부호 + 레벨) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 mt-2">
        {lights.map((s) => {
          const st = levelStyle(s.level)
          const z = Number(s.z) || 0
          return (
            <div
              key={s.pc}
              className={`flex items-center justify-between border rounded px-2 py-1 ${st.border} ${st.bg}`}
            >
              <span className="text-xs text-gray-700 truncate">{s.label}</span>
              <span className={`text-xs font-bold ${st.text}`}>
                {z > 0 ? '+' : ''}{z.toFixed(2)}σ
                {s.level === 'stressed' && ' ⚠'}
              </span>
            </div>
          )
        })}
      </div>
      <p className="text-[11px] text-gray-400 mt-2">
        ※ z = 윈도우 내 표준화 점수. |z|≥1.5 과열/긴장(⚠), 0.7~1.5 완만.
      </p>
    </div>
  )
}
