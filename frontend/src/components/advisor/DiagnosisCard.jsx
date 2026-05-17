import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

// 섹터 파이차트 색상 — 14색 cycle (KR 14 + US 11 카테고리 커버)
const SECTOR_COLORS = [
  '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
  '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
  '#14b8a6', '#a855f7', '#eab308', '#64748b',
]

function SectorTooltip({ active, payload }) {
  if (!active || !payload?.[0]) return null
  const d = payload[0].payload
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow px-3 py-2 text-sm">
      <p className="font-medium text-gray-900">{d.sector}</p>
      <p className="text-gray-600">{d.weight_pct}%</p>
      {d.assessment && <p className="text-xs text-gray-500 mt-0.5">{d.assessment}</p>}
    </div>
  )
}

// 평가 텍스트 → 배지 스타일 분류 (편중/적정/부족 키워드 기반)
function classifyAssessment(assessment) {
  const txt = (assessment || '').toString()
  if (txt.includes('편중') || txt.includes('과잉') || txt.includes('과다')) {
    return { tag: '편중', bg: 'bg-orange-100', text: 'text-orange-700', border: 'border-orange-300', icon: '⚠' }
  }
  if (txt.includes('부족') || txt.includes('미흡') || txt.includes('낮음')) {
    return { tag: '부족', bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-300', icon: '↓' }
  }
  // 적정/균형/양호/등 또는 기본
  return { tag: '적정', bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-300', icon: '✓' }
}

// 진입 타이밍 배지 스타일
const TIMING_STYLES = {
  immediate:  { bg: 'bg-red-100', text: 'text-red-700', label: '즉시' },
  this_week:  { bg: 'bg-yellow-100', text: 'text-yellow-700', label: '금주' },
  this_month: { bg: 'bg-gray-100', text: 'text-gray-600', label: '이번 달' },
}

const RISK_COLORS = {
  high: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-400', label: '높음' },
  medium: { bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-400', label: '보통' },
  low: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-400', label: '낮음' },
}

function ScoreGauge({ score }) {
  const data = [
    { value: score },
    { value: 100 - score },
  ]
  const color = score >= 70 ? '#22c55e' : score >= 40 ? '#eab308' : '#ef4444'

  return (
    <div className="relative inline-flex items-center justify-center">
      <PieChart width={100} height={100}>
        <Pie
          data={data}
          cx={50}
          cy={50}
          innerRadius={30}
          outerRadius={45}
          startAngle={90}
          endAngle={-270}
          dataKey="value"
          stroke="none"
        >
          <Cell fill={color} />
          <Cell fill="#e5e7eb" />
        </Pie>
      </PieChart>
      <span className="absolute text-lg font-bold text-gray-900">{score}</span>
    </div>
  )
}

export default function DiagnosisCard({ diagnosis, recommendations = [] }) {
  if (!diagnosis) return null

  const risk = RISK_COLORS[diagnosis.risk_level] || RISK_COLORS.medium

  // 보유 섹터명 집합 (정규화 — 공백 제거 비교)
  const sectorAnalysis = diagnosis.sector_analysis || []
  const heldNames = new Set(sectorAnalysis.map((s) => (s.sector || '').trim()))
  // 미보유 추천 섹터 (포트폴리오에 없는 신규 편입 추천)
  const newEntries = (recommendations || []).filter(
    (r) => r.sector && !heldNames.has(r.sector.trim()),
  )

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="bg-gray-50 px-4 py-2.5 text-sm font-semibold text-gray-700 border-b border-gray-200">
        포트폴리오 진단
      </div>
      <div className="p-4 space-y-4">
        {/* 상단: 점수 + 위험도 + 요약 */}
        <div className="flex items-start gap-4">
          <ScoreGauge score={diagnosis.total_score || 0} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold border ${risk.bg} ${risk.text} ${risk.border}`}>
                위험도: {risk.label}
              </span>
            </div>
            <p className="text-sm text-gray-700 leading-relaxed">{diagnosis.summary}</p>
          </div>
        </div>

        {/* 집중도 위험 */}
        {diagnosis.concentration_risk && (
          <div className="text-sm">
            <span className="font-medium text-gray-600">집중도: </span>
            <span className="text-gray-700">{diagnosis.concentration_risk}</span>
          </div>
        )}

        {/* 통화 노출 */}
        {diagnosis.currency_exposure && (
          <div className="text-sm">
            <span className="font-medium text-gray-600">통화 분산: </span>
            <span className="text-gray-700">{diagnosis.currency_exposure}</span>
          </div>
        )}

        {/* 섹터 분석 — 좌: 파이차트 / 우: 평가 리스트 */}
        {diagnosis.sector_analysis && diagnosis.sector_analysis.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">섹터 분석</h4>
            <div className="flex flex-col md:flex-row gap-4 items-center md:items-start">
              <div className="w-full md:w-1/2">
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie
                      data={diagnosis.sector_analysis}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={85}
                      dataKey="weight_pct"
                      nameKey="sector"
                      stroke="none"
                      label={({ sector, weight_pct }) => `${sector} ${weight_pct}%`}
                      labelLine={false}
                    >
                      {diagnosis.sector_analysis.map((_, i) => (
                        <Cell key={i} fill={SECTOR_COLORS[i % SECTOR_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip content={<SectorTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="w-full md:w-1/2 space-y-3">
                {/* 보유 섹터 — 편중/적정/부족 색상 배지 */}
                <div>
                  <h5 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wide mb-1.5">
                    보유 섹터 ({sectorAnalysis.length})
                  </h5>
                  <div className="space-y-1.5">
                    {sectorAnalysis.map((s, i) => {
                      const cls = classifyAssessment(s.assessment)
                      return (
                        <div key={i} className="flex items-start gap-2 text-sm">
                          <span
                            className="w-3 h-3 mt-1 rounded-full shrink-0"
                            style={{ backgroundColor: SECTOR_COLORS[i % SECTOR_COLORS.length] }}
                          />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-baseline gap-1.5 flex-wrap">
                              <span className="font-medium text-gray-700 whitespace-nowrap">{s.sector}</span>
                              <span className="text-xs text-gray-500">{s.weight_pct}%</span>
                              <span
                                className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${cls.bg} ${cls.text} ${cls.border} whitespace-nowrap`}
                                title={s.assessment}
                              >
                                {cls.icon} {cls.tag}
                              </span>
                            </div>
                            {s.assessment && (
                              <div className="text-xs text-gray-500 leading-relaxed mt-0.5">{s.assessment}</div>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* 신규 편입 추천 (포트폴리오 미보유) */}
                {newEntries.length > 0 && (
                  <div className="border-t border-gray-100 pt-2.5">
                    <h5 className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wide mb-1.5 flex items-center gap-1">
                      ⭐ 신규 편입 추천 ({newEntries.length})
                      <span className="text-[10px] font-normal text-gray-400 normal-case">— 현재 미보유</span>
                    </h5>
                    <div className="space-y-1.5">
                      {newEntries.map((rec, i) => {
                        const timing = TIMING_STYLES[rec.entry_timing] || TIMING_STYLES.this_month
                        return (
                          <div key={i} className="flex items-start gap-2 text-sm">
                            <span className="w-3 h-3 mt-1 rounded-full shrink-0 border-2 border-dashed border-emerald-400 bg-emerald-50" />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-baseline gap-1.5 flex-wrap">
                                <span className="font-medium text-emerald-700 whitespace-nowrap">{rec.sector}</span>
                                {rec.target_weight_pct != null && (
                                  <span className="text-[10px] text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200 whitespace-nowrap">
                                    목표 {rec.target_weight_pct}%
                                  </span>
                                )}
                                <span className={`text-[10px] px-1.5 py-0.5 rounded ${timing.bg} ${timing.text} whitespace-nowrap`}>
                                  {timing.label}
                                </span>
                              </div>
                              {rec.rationale && (
                                <div className="text-xs text-gray-500 leading-relaxed mt-0.5 line-clamp-2">{rec.rationale}</div>
                              )}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
