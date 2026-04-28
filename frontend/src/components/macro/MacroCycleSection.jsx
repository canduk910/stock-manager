import LoadingSpinner from '../common/LoadingSpinner'
import ErrorAlert from '../common/ErrorAlert'

const PHASES = ['recovery', 'expansion', 'overheating', 'contraction']
const PHASE_LABELS = {
  recovery: '회복기',
  expansion: '확장기',
  overheating: '과열기',
  contraction: '수축기',
}
const PHASE_COLORS = {
  recovery: { bg: 'bg-emerald-100', text: 'text-emerald-700', active: 'bg-emerald-600' },
  expansion: { bg: 'bg-blue-100', text: 'text-blue-700', active: 'bg-blue-600' },
  overheating: { bg: 'bg-amber-100', text: 'text-amber-700', active: 'bg-amber-600' },
  contraction: { bg: 'bg-red-100', text: 'text-red-700', active: 'bg-red-600' },
}

function PhaseCard({ phase, isActive }) {
  const colors = PHASE_COLORS[phase] || PHASE_COLORS.recovery
  return (
    <div
      className={`rounded-lg p-3 text-center font-semibold text-sm transition-all ${
        isActive
          ? `${colors.active} text-white shadow-md scale-105`
          : `${colors.bg} ${colors.text} opacity-60`
      }`}
    >
      {PHASE_LABELS[phase] || phase}
    </div>
  )
}

function IndicatorBar({ label, signal, score, weight }) {
  const pct = Math.min(Math.abs((score || 0) * (weight || 0)) * 100, 100)
  const barColor = score > 0 ? 'bg-emerald-500' : score < 0 ? 'bg-red-500' : 'bg-gray-400'
  return (
    <div className="rounded-lg border bg-white p-3 shadow-sm">
      <div className="text-xs font-medium text-gray-500 mb-1">{label}</div>
      <div className="text-sm font-semibold text-gray-900 mb-2 truncate">{signal || '-'}</div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

const SCORE_LABELS = {
  yield_curve: '장단기 금리차',
  credit_spread: '크레딧 스프레드',
  vix: 'VIX',
  sector_rotation: '섹터 로테이션',
  dollar: '달러',
}

export default function MacroCycleSection({ data, loading, error }) {
  if (loading) return <LoadingSpinner message="경기 사이클 로딩 중..." />
  if (error) return <ErrorAlert message={error} />
  if (!data) return null

  // API 응답: { cycle: {...}, updated_at, errors }
  const cycle = data.cycle || data
  const { phase, phase_label, phase_desc, confidence, scores, leader_sectors } = cycle

  return (
    <section>
      <h2 className="text-lg font-semibold text-gray-900 mb-3">경기 사이클</h2>
      <div className="rounded-lg border bg-white p-5 shadow-sm space-y-5">
        {/* 4단계 순환 다이어그램 */}
        <div className="grid grid-cols-4 gap-2 items-center">
          {PHASES.map((p, i) => (
            <div key={p} className="flex items-center">
              <div className="flex-1">
                <PhaseCard phase={p} isActive={phase === p} />
              </div>
              {i < PHASES.length - 1 && (
                <div className="text-gray-300 text-lg font-bold mx-1 shrink-0">&rarr;</div>
              )}
            </div>
          ))}
        </div>

        {/* 현재 국면 설명 */}
        {phase_label && (
          <div className="text-center bg-gray-50 rounded-lg p-4">
            <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">현재 경기 국면</div>
            <span
              className={`inline-block px-5 py-2 rounded-full text-lg font-bold text-white ${
                PHASE_COLORS[phase]?.active || 'bg-gray-500'
              }`}
            >
              {phase_label}
            </span>
            {phase_desc && <p className="text-sm text-gray-600 mt-2">{phase_desc}</p>}
          </div>
        )}

        {/* 신뢰도 바 */}
        {confidence != null && (
          <div>
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>신뢰도</span>
              <span>{confidence}%</span>
            </div>
            <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full bg-blue-500 transition-all"
                style={{ width: `${Math.min(confidence, 100)}%` }}
              />
            </div>
          </div>
        )}

        {/* 5개 지표별 breakdown */}
        {scores && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            {Object.entries(scores).map(([key, item]) => (
              <IndicatorBar
                key={key}
                label={SCORE_LABELS[key] || key}
                signal={item?.signal}
                score={item?.score}
                weight={item?.weight}
              />
            ))}
          </div>
        )}

        {/* 주도 섹터 태그 */}
        {leader_sectors?.length > 0 && (
          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-sm font-medium text-gray-500">주도 섹터:</span>
            {leader_sectors.map((s) => (
              <span
                key={s}
                className="inline-block px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-xs font-medium"
              >
                {s}
              </span>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
