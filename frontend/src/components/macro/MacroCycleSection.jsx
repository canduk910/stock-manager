import { useState } from 'react'
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

const REGIME_LABELS = {
  accumulation: '적극 매수',
  selective: '선별 매수',
  cautious: '신중',
  defensive: '방어',
}
const REGIME_COLORS = {
  accumulation: { bg: 'bg-emerald-100', text: 'text-emerald-700', active: 'bg-emerald-600' },
  selective: { bg: 'bg-blue-100', text: 'text-blue-700', active: 'bg-blue-600' },
  cautious: { bg: 'bg-amber-100', text: 'text-amber-700', active: 'bg-amber-600' },
  defensive: { bg: 'bg-red-100', text: 'text-red-700', active: 'bg-red-600' },
}

// ── 툴팁 컴포넌트 ─────────────────────────────────────────────

function InfoTooltip({ children, content, wide }) {
  const [show, setShow] = useState(false)
  return (
    <div
      className="relative inline-block"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      {show && (
        <div className={`absolute z-50 left-1/2 -translate-x-1/2 top-full mt-2 rounded-lg bg-gray-900 text-white text-xs leading-relaxed p-4 shadow-xl pointer-events-none text-left ${wide ? 'w-[22rem] sm:w-[26rem]' : 'w-72 sm:w-80'}`}>
          <div className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-gray-900 rotate-45" />
          {content}
        </div>
      )}
    </div>
  )
}

const CYCLE_TOOLTIP = (
  <>
    <div className="font-semibold mb-2">경기 사이클 국면 판단</div>
    <p className="mb-2">5개 매크로 지표의 가중합산으로 현재 경기가 어느 단계에 있는지 판단합니다.</p>
    <table className="w-full text-xs mb-2">
      <thead><tr className="border-b border-gray-700"><th className="text-left py-1">지표</th><th className="text-right py-1">가중치</th></tr></thead>
      <tbody>
        <tr><td className="py-0.5">장단기 금리차 (수익률곡선)</td><td className="text-right">30%</td></tr>
        <tr><td className="py-0.5">하이일드 신용스프레드</td><td className="text-right">20%</td></tr>
        <tr><td className="py-0.5">VIX (변동성)</td><td className="text-right">20%</td></tr>
        <tr><td className="py-0.5">섹터 로테이션</td><td className="text-right">15%</td></tr>
        <tr><td className="py-0.5">달러 강도</td><td className="text-right">15%</td></tr>
      </tbody>
    </table>
    <div className="border-t border-gray-700 pt-2 space-y-1">
      <div><span className="text-emerald-400">회복기</span>: 수익률곡선 정상화, VIX 하락, 스프레드 축소</div>
      <div><span className="text-blue-400">확장기</span>: 양의 수익률곡선, 낮은 VIX, 좁은 스프레드</div>
      <div><span className="text-amber-400">과열기</span>: 수익률곡선 평탄화, VIX 저점, 방어 전환</div>
      <div><span className="text-red-400">수축기</span>: 수익률곡선 역전, VIX 급등, 스프레드 확대</div>
    </div>
  </>
)

const REGIME_TOOLTIP = (
  <>
    <div className="font-semibold mb-2">투자 체제 판단</div>
    <p className="mb-2">시장 심리와 밸류에이션으로 현재 어떤 투자 전략을 취해야 하는지 판단합니다.</p>
    <div className="mb-2">
      <div className="font-medium mb-1">입력 지표:</div>
      <div>- <span className="text-yellow-300">버핏지수</span> (시총/GDP): 시장 전체의 고평가/저평가</div>
      <div>- <span className="text-yellow-300">공포탐욕지수</span>: VIX+모멘텀+시장폭 종합 심리</div>
      <div>- <span className="text-yellow-300">VIX &gt; 35</span>: 강제 극단적 공포 오버라이드</div>
    </div>
    <div className="mb-2">
      버핏지수(4단계) x 공포탐욕(5단계) = 20칸 매트릭스에서 체제를 결정합니다.
    </div>
    <div className="border-t border-gray-700 pt-2 space-y-1">
      <div><span className="text-emerald-400">적극 매수</span>: 저평가+공포 구간. 현금 25%, 주식 최대 75%</div>
      <div><span className="text-blue-400">선별 매수</span>: 적정+중립 구간. 현금 35%, 주식 최대 65%</div>
      <div><span className="text-amber-400">신중</span>: 고평가 또는 탐욕 구간. 현금 50%, 주식 최대 50%</div>
      <div><span className="text-red-400">방어</span>: 극단적 고평가+탐욕. 현금 75%, 신규 매수 금지</div>
    </div>
  </>
)

// ── 서브 컴포넌트 ─────────────────────────────────────────────

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

function IndicatorCard({ label, signal }) {
  return (
    <div className="rounded-lg border bg-gray-50 px-3 py-2">
      <div className="text-xs text-gray-500 mb-0.5">{label}</div>
      <div className="text-sm font-semibold text-gray-900 truncate">{signal || '-'}</div>
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

const FG_LABELS = {
  extreme_fear: '극단적 공포',
  fear: '공포',
  neutral: '중립',
  greed: '탐욕',
  extreme_greed: '극단적 탐욕',
}
const BUFFETT_LABELS = {
  low: '저평가',
  normal: '적정',
  high: '고평가',
  extreme: '극단적 고평가',
}

function RegimeDetail({ regime }) {
  if (!regime) return null
  const r = regime.regime
  const colors = REGIME_COLORS[r] || REGIME_COLORS.cautious

  return (
    <div className="flex-1 rounded-lg border bg-white p-4 shadow-sm">
      <div className="text-sm font-medium text-gray-600 mb-2 text-center">
        <InfoTooltip content={REGIME_TOOLTIP} wide>
          <span className="cursor-help border-b border-dashed border-gray-400 inline-flex items-center gap-1">
            현재 투자 체제
            <svg className="w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <circle cx="12" cy="12" r="10" /><path d="M12 16v-4m0-4h.01" />
            </svg>
          </span>
        </InfoTooltip>
      </div>
      <div className="text-center mb-3">
        <span
          className={`inline-block px-5 py-2 rounded-full text-lg font-bold text-white ${colors.active}`}
        >
          {REGIME_LABELS[r] || r}
        </span>
      </div>
      <p className="text-xs text-gray-500 text-center mb-3">심리 / 밸류에이션 기반</p>
      <div className="space-y-1.5 text-xs">
        {regime.fear_greed_score != null && (
          <div className="flex justify-between">
            <span className="text-gray-500">공포탐욕</span>
            <span className="font-medium text-gray-700">
              {Math.round(regime.fear_greed_score)} ({FG_LABELS[regime.fg_level] || regime.fg_level})
            </span>
          </div>
        )}
        {regime.buffett_ratio != null && (
          <div className="flex justify-between">
            <span className="text-gray-500">버핏지수</span>
            <span className="font-medium text-gray-700">
              {regime.buffett_ratio > 10
                ? `${Math.round(regime.buffett_ratio)}%`
                : `${Math.round(regime.buffett_ratio * 100)}%`
              } ({BUFFETT_LABELS[regime.buffett_level] || regime.buffett_level})
            </span>
          </div>
        )}
        {regime.vix != null && (
          <div className="flex justify-between">
            <span className="text-gray-500">VIX</span>
            <span className="font-medium text-gray-700">{regime.vix.toFixed(1)}</span>
          </div>
        )}
      </div>
    </div>
  )
}

function DivergenceNote({ phase, regime }) {
  if (!phase || !regime) return null
  const isExpansive = phase === 'recovery' || phase === 'expansion'
  const isDefensive = regime === 'cautious' || regime === 'defensive'
  const isContractive = phase === 'overheating' || phase === 'contraction'
  const isAccumulative = regime === 'accumulation' || regime === 'selective'

  if (isExpansive && isDefensive) {
    return (
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800">
        <span className="font-semibold">경기 국면과 투자 체제가 다릅니다.</span>{' '}
        경기 흐름(금리·달러·섹터)은 양호하나, 시장 밸류에이션(버핏지수)이나 심리(공포탐욕)가 과열 수준입니다.
        경기는 좋지만 주가가 이미 많이 올라 조심해야 하는 구간일 수 있습니다.
      </div>
    )
  }
  if (isContractive && isAccumulative) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800">
        <span className="font-semibold">경기 국면과 투자 체제가 다릅니다.</span>{' '}
        경기 지표(금리·신용스프레드)는 둔화 신호를 보이지만, 시장 밸류에이션이 저평가 구간이거나 심리가 위축되어 매수 기회일 수 있습니다.
      </div>
    )
  }
  return null
}

// ── 메인 ─────────────────────────────────────────────────────

export default function MacroCycleSection({ data, loading, error }) {
  if (loading) return <LoadingSpinner message="경기 사이클 로딩 중..." />
  if (error) return <ErrorAlert message={error} />
  if (!data) return null

  const cycle = data.cycle || data
  const regime = data.regime || null
  const { phase, phase_label, phase_desc, confidence, scores, leader_sectors } = cycle

  const phaseColors = PHASE_COLORS[phase] || PHASE_COLORS.recovery

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

        {/* 경기 국면 + 투자 체제 나란히 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* 경기 국면 */}
          <div className="flex-1 rounded-lg border bg-white p-4 shadow-sm">
            <div className="text-sm font-medium text-gray-600 mb-2 text-center">
              <InfoTooltip content={CYCLE_TOOLTIP}>
                <span className="cursor-help border-b border-dashed border-gray-400 inline-flex items-center gap-1">
                  현재 경기 국면
                  <svg className="w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <circle cx="12" cy="12" r="10" /><path d="M12 16v-4m0-4h.01" />
                  </svg>
                </span>
              </InfoTooltip>
            </div>
            <div className="text-center mb-3">
              <span
                className={`inline-block px-5 py-2 rounded-full text-lg font-bold text-white ${phaseColors.active}`}
              >
                {phase_label}
              </span>
            </div>
            <p className="text-xs text-gray-500 text-center mb-3">경기 흐름 기반 (5개 지표)</p>
            {phase_desc && <p className="text-xs text-gray-600 text-center">{phase_desc}</p>}
          </div>

          {/* 투자 체제 */}
          <RegimeDetail regime={regime} />
        </div>

        {/* 괴리 설명 */}
        <DivergenceNote phase={phase} regime={regime?.regime} />

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

        {/* 5개 지표 요약 */}
        {scores && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
            {Object.entries(scores).map(([key, item]) => (
              <IndicatorCard key={key} label={SCORE_LABELS[key] || key} signal={item?.signal} />
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
