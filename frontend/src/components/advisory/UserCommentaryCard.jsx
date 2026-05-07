/**
 * UserCommentaryCard — 사용자 가설 양면 평가 카드 (2026-05-07).
 *
 * 보고서 응답에 user_commentary_evaluation 필드가 있을 때만 렌더.
 * 헤더: 사용자 의견 원문(인용) + overall_stance 배지
 * 좌(👍 동의 녹색) / 우(👎 반박 빨강) 2컬럼 + 항목별 strength 1~10 게이지
 * 하단: summary 1~3문장
 * 모바일: 1컬럼 스택
 *
 * Props:
 *   evaluation: {
 *     user_comment, overall_stance,
 *     agree_points: [{point, evidence, strength}],
 *     disagree_points: [{point, evidence, strength}],
 *     summary
 *   } | null
 */

const STANCE_META = {
  strong_agree: {
    label: '강한 동의',
    cls: 'bg-green-100 text-green-800 border-green-400',
  },
  agree: {
    label: '동의',
    cls: 'bg-lime-100 text-lime-800 border-lime-400',
  },
  balanced: {
    label: '균형',
    cls: 'bg-gray-100 text-gray-700 border-gray-400',
  },
  disagree: {
    label: '반박',
    cls: 'bg-amber-100 text-amber-800 border-amber-400',
  },
  strong_disagree: {
    label: '강한 반박',
    cls: 'bg-red-100 text-red-800 border-red-400',
  },
}

function StanceBadge({ stance }) {
  const meta = STANCE_META[stance] || STANCE_META.balanced
  return (
    <span
      className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold border ${meta.cls}`}
    >
      {meta.label}
    </span>
  )
}

function StrengthGauge({ strength, side }) {
  const pct = Math.min(100, Math.max(0, ((strength || 0) / 10) * 100))
  const barColor =
    side === 'agree' ? 'bg-green-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-200 rounded-full h-1.5 overflow-hidden">
        <div className={`h-1.5 ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-600 shrink-0 tabular-nums">
        {strength}/10
      </span>
    </div>
  )
}

function PointItem({ item, side }) {
  return (
    <div className="border border-gray-200 rounded-md p-2.5 bg-white">
      <p className="text-sm font-semibold text-gray-800 mb-1">{item.point}</p>
      {item.evidence && (
        <p className="text-xs text-gray-600 leading-relaxed mb-1.5">
          {item.evidence}
        </p>
      )}
      <StrengthGauge strength={item.strength} side={side} />
    </div>
  )
}

function SideColumn({ side, points }) {
  const isAgree = side === 'agree'
  const headerCls = isAgree
    ? 'bg-green-50 text-green-800 border-green-200'
    : 'bg-red-50 text-red-800 border-red-200'
  const icon = isAgree ? '👍' : '👎'
  const title = isAgree ? '동의 근거' : '반박 근거'

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div
        className={`px-3 py-2 text-sm font-semibold border-b ${headerCls}`}
      >
        {icon} {title}{' '}
        <span className="text-xs font-normal opacity-70">
          ({points?.length || 0})
        </span>
      </div>
      <div className="p-3 space-y-2 bg-gray-50">
        {points && points.length > 0 ? (
          points.map((p, i) => <PointItem key={i} item={p} side={side} />)
        ) : (
          <p className="text-xs text-gray-400 text-center py-4">
            제시된 {isAgree ? '동의' : '반박'} 근거 없음
          </p>
        )}
      </div>
    </div>
  )
}

export default function UserCommentaryCard({ evaluation }) {
  if (!evaluation) return null

  const {
    user_comment: userComment,
    overall_stance: overallStance,
    agree_points: agreePoints = [],
    disagree_points: disagreePoints = [],
    summary,
  } = evaluation

  return (
    <div className="border-2 border-blue-200 rounded-lg overflow-hidden bg-blue-50/30">
      {/* 헤더: 사용자 의견 원문 + stance 배지 */}
      <div className="px-4 py-3 bg-blue-50 border-b border-blue-200">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold text-blue-700 mb-1">
              💬 사용자 가설 — 양면 평가
            </p>
            {userComment && (
              <blockquote className="text-sm text-gray-700 italic border-l-2 border-blue-300 pl-2 leading-relaxed whitespace-pre-wrap">
                "{userComment}"
              </blockquote>
            )}
          </div>
          <StanceBadge stance={overallStance} />
        </div>
      </div>

      {/* 본문: 좌/우 2컬럼 (모바일은 1컬럼 스택) */}
      <div className="p-3">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <SideColumn side="agree" points={agreePoints} />
          <SideColumn side="disagree" points={disagreePoints} />
        </div>

        {/* summary 하단 */}
        {summary && (
          <div className="mt-3 p-3 bg-white border border-gray-200 rounded-md">
            <p className="text-xs font-semibold text-gray-500 mb-1">평가 요약</p>
            <p className="text-sm text-gray-800 leading-relaxed">{summary}</p>
          </div>
        )}
      </div>
    </div>
  )
}
