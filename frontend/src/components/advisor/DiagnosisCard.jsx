import { PieChart, Pie, Cell } from 'recharts'

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

export default function DiagnosisCard({ diagnosis }) {
  if (!diagnosis) return null

  const risk = RISK_COLORS[diagnosis.risk_level] || RISK_COLORS.medium

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

        {/* 섹터 분석 */}
        {diagnosis.sector_analysis && diagnosis.sector_analysis.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">섹터 분석</h4>
            <div className="space-y-1.5">
              {diagnosis.sector_analysis.map((s, i) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <span className="w-20 text-gray-600 truncate">{s.sector}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-blue-500 h-2 rounded-full"
                      style={{ width: `${Math.min(s.weight_pct || 0, 100)}%` }}
                    />
                  </div>
                  <span className="w-12 text-right text-gray-500 text-xs">{s.weight_pct}%</span>
                  <span className="text-xs text-gray-500">{s.assessment}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
