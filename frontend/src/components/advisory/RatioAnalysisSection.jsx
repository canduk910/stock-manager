/**
 * 4축 재무비율 평가 (활동성/성장성/수익성/안정성) — REQ-SCREEN-03
 *
 * RadarChart(4축 0~100) 1장 + 축별 진단 카드 4개(점수 게이지 + 진단 문구 +
 * 기여 비율 펼침). FundamentalPanel 현금흐름표 뒤 최하단에 렌더.
 *
 * 데이터 출처: data.fundamental.ratio_analysis (services/financial_ratios.py).
 *   추가 외부 호출 0 — 기존 fundamental 응답 재가공 결과.
 *
 * 안전 규칙(§D-7): 매매 액션 문구 미표시. 진단은 서술형(신호/우려/관찰) 전용.
 */
import { useState } from 'react'
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  ResponsiveContainer, Tooltip,
} from 'recharts'

// 축 키 → 한글 라벨 (강의 4유형 순서 = activity → growth → profitability → stability)
const AXIS_ORDER = ['activity', 'growth', 'profitability', 'stability']
const AXIS_LABEL = {
  activity: '활동성',
  growth: '성장성',
  profitability: '수익성',
  stability: '안정성',
}

// 비율 키 → 한글 라벨 (기여 비율 펼침용)
const RATIO_LABEL = {
  total_asset_turnover: '총자산회전율',
  receivables_turnover: '매출채권회전율',
  inventory_turnover: '재고자산회전율',
  payables_turnover: '매입채무회전율',
  revenue_growth: '매출액 증가율',
  operating_income_growth: '영업이익 증가율',
  net_income_growth: '순이익 증가율',
  total_asset_growth: '총자산 증가율',
  oi_margin: '영업이익률',
  interest_coverage: '이자보상비율',
  roe: 'ROE',
  roa: 'ROA',
  debt_ratio: '부채비율',
  equity_ratio: '자기자본비율',
  debt_dependency: '차입금의존도',
  current_ratio: '유동비율',
}

// 등급 → 색상 토큰 (§D-4). N/A는 회색.
const GRADE_STYLE = {
  '우수': { text: 'text-green-700', bg: 'bg-green-50', border: 'border-green-200', bar: 'bg-green-500' },
  '양호': { text: 'text-teal-700', bg: 'bg-teal-50', border: 'border-teal-200', bar: 'bg-teal-500' },
  '보통': { text: 'text-yellow-700', bg: 'bg-yellow-50', border: 'border-yellow-200', bar: 'bg-yellow-500' },
  '주의': { text: 'text-orange-700', bg: 'bg-orange-50', border: 'border-orange-200', bar: 'bg-orange-500' },
  '위험': { text: 'text-red-700', bg: 'bg-red-50', border: 'border-red-200', bar: 'bg-red-500' },
  'N/A': { text: 'text-gray-500', bg: 'bg-gray-50', border: 'border-gray-200', bar: 'bg-gray-300' },
}

function gradeStyle(grade) {
  return GRADE_STYLE[grade] || GRADE_STYLE['N/A']
}

function SectionTitle({ children }) {
  return (
    <h3 className="text-sm font-semibold text-gray-700 mt-6 mb-2 border-b border-gray-200 pb-1">
      {children}
    </h3>
  )
}

function fmtRatioValue(key, value) {
  if (value == null) return '-'
  // 회전율은 '회', 증가율/마진/비율은 '%' or '배' — 단순 숫자 + 단위 휴리스틱
  if (key.endsWith('_turnover')) return `${value.toFixed(2)}회`
  if (key === 'interest_coverage') return `${value.toFixed(2)}배`
  return `${value.toFixed(1)}%`
}

// ── 축 진단 카드 ──────────────────────────────────────────────────────────
function AxisCard({ axisKey, axis }) {
  const [open, setOpen] = useState(false)
  const label = AXIS_LABEL[axisKey]
  const applicable = axis?.applicable
  const grade = axis?.grade || 'N/A'
  const score = axis?.score
  const st = gradeStyle(applicable ? grade : 'N/A')
  const ratios = axis?.ratios || {}
  const ratioKeys = Object.keys(ratios)

  return (
    <div className={`border rounded-lg p-3 ${st.border} ${st.bg}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-semibold text-gray-800">{label}</span>
        {applicable ? (
          <span className={`text-xs font-bold ${st.text}`}>
            {grade} · {score != null ? score.toFixed(0) : '-'}점
          </span>
        ) : (
          <span
            className="text-xs font-bold text-gray-500 px-1.5 py-0.5 rounded bg-gray-200"
            title={axis?.na_reason || '적용 불가'}
          >
            N/A
          </span>
        )}
      </div>

      {/* 점수 게이지 */}
      {applicable && score != null && (
        <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden mb-2">
          <div className={`h-full ${st.bar}`} style={{ width: `${Math.max(0, Math.min(100, score))}%` }} />
        </div>
      )}

      {/* 진단 문구 (서술형, 매매 명령 금지) */}
      <p className="text-xs text-gray-600 leading-snug min-h-[2rem]">
        {axis?.diagnosis || (applicable ? '' : (axis?.na_reason || '해당 업종 적용 불가(N/A)'))}
      </p>

      {/* 기여 비율 펼침 */}
      {applicable && ratioKeys.length > 0 && (
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="mt-2 text-[11px] text-gray-500 hover:text-gray-700 underline"
        >
          {open ? '기여 비율 접기' : '기여 비율 펼침'}
        </button>
      )}
      {open && (
        <table className="w-full mt-2 text-[11px]">
          <tbody>
            {ratioKeys.map((key) => {
              const r = ratios[key] || {}
              return (
                <tr key={key} className="border-t border-gray-100">
                  <td className="py-1 text-gray-600">{RATIO_LABEL[key] || key}</td>
                  <td className="py-1 text-right text-gray-800">{fmtRatioValue(key, r.value)}</td>
                  <td className="py-1 text-right text-gray-500 w-10">
                    {r.points != null ? `${r.points}점` : '데이터 없음'}
                  </td>
                  <td className="py-1 text-right text-gray-400 w-14">
                    {r.trend_pct != null ? `${r.trend_pct > 0 ? '+' : ''}${r.trend_pct.toFixed(1)}%` : ''}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </div>
  )
}

// ── 메인 ──────────────────────────────────────────────────────────────────
export default function RatioAnalysisSection({ ratioAnalysis }) {
  const ra = ratioAnalysis || null

  // EmptyState: ratio_analysis 부재 또는 overall_score None
  if (!ra || ra.overall_score == null) {
    return (
      <>
        <SectionTitle>4축 재무비율 평가</SectionTitle>
        <div className="border border-gray-200 rounded-lg p-6 text-center text-sm text-gray-500 bg-gray-50">
          재무비율 데이터 부족 — 평가를 표시할 수 없습니다.
        </div>
      </>
    )
  }

  const axes = ra.axes || {}
  // RadarChart 데이터: N/A 축은 점수 0이 아니라 null (회색 처리, 0 아님)
  const radarData = AXIS_ORDER.map((key) => {
    const ax = axes[key] || {}
    return {
      axis: AXIS_LABEL[key],
      score: ax.applicable && ax.score != null ? ax.score : null,
    }
  })

  const overallGrade = ra.overall_grade || 'N/A'
  const overallStyle = gradeStyle(overallGrade)

  return (
    <>
      <SectionTitle>4축 재무비율 평가</SectionTitle>

      {/* 종합 점수 배지 */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-gray-500">
          활동성 · 성장성 · 수익성 · 안정성 (각 25~100점)
        </span>
        <span className={`text-sm font-bold px-2 py-0.5 rounded ${overallStyle.bg} ${overallStyle.text} border ${overallStyle.border}`}>
          종합 {overallGrade} · {ra.overall_score.toFixed(0)}점
        </span>
      </div>

      {/* RadarChart — 최저 점수 25(1점×25)이므로 도메인 floor를 25로 보정(bug_014).
          §D-3 '최저 1점' 채점 정책은 불변, 차트 시각 표현만 0~24 dead zone 제거. */}
      <div className="w-full h-64">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={radarData} outerRadius="70%">
            <PolarGrid />
            <PolarAngleAxis dataKey="axis" tick={{ fontSize: 12, fill: '#4b5563' }} />
            <PolarRadiusAxis domain={[25, 100]} tick={{ fontSize: 10, fill: '#9ca3af' }} angle={90} />
            <Radar
              name="점수"
              dataKey="score"
              stroke="#3b82f6"
              fill="#3b82f6"
              fillOpacity={0.4}
              connectNulls={false}
            />
            <Tooltip
              formatter={(v) => (v == null ? 'N/A' : `${Number(v).toFixed(0)}점`)}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[11px] text-gray-400 mb-2 text-right">
        ※ 각 축 최저 25점(비율당 최저 1점). 레이더 차트 기준선은 25점입니다.
      </p>

      {/* 축별 진단 카드 4개 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
        {AXIS_ORDER.map((key) => (
          <AxisCard key={key} axisKey={key} axis={axes[key]} />
        ))}
      </div>
    </>
  )
}
