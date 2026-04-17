/**
 * AI자문 탭 — OpenAI GPT-4o 리포트 표시.
 *
 * DetailPage > 종합리포트 > AI자문 서브탭에서 렌더링된다.
 *
 * 구조 (위→아래):
 *   1) v2 등급 카드 (hasV2=true일 때만 표시):
 *      - SafetyGradeBadge: A(진녹)/B+(연녹)/B(황)/C(주)/D(적) 대형 배지
 *      - ScoreBar 3개: 등급점수(28점)/복합점수(100점)/체제정합성(100점)
 *      - Value Trap 경고 배너 (value_trap_warning=true 시 적색)
 *      - recommendation 배지: ENTER(빨강)/HOLD(황)/SKIP(회)
 *   2) 종합투자의견: 등급 배지(매수/중립/매도) + 요약 + 근거
 *   3) 전략별 평가: 변동성돌파/안전마진/추세추종 3컬럼 카드
 *      - 안전마진: Graham Number + 할인율 표시
 *   4) 기술적 시그널: MACD/RSI/Stoch 해석 + 거래량/BB
 *   5) 포지션 가이드: 진입가/손절가/익절가/리스크보상비율/분할매수
 *   6) 리스크 요인 + 투자 포인트
 *
 * v1 하위호환: schema_version !== 'v2' 또는 grade 부재 시 v2 카드 전체 숨김
 */

function GradeBadge({ grade }) {
  const map = {
    '매수': 'bg-red-100 text-red-700 border-red-400',
    '중립': 'bg-gray-100 text-gray-700 border-gray-400',
    '매도': 'bg-blue-100 text-blue-700 border-blue-400',
    '관망': 'bg-yellow-100 text-yellow-700 border-yellow-400',
  }
  const cls = map[grade] || 'bg-gray-100 text-gray-600 border-gray-300'
  return (
    <span className={`inline-block px-3 py-0.5 rounded-full text-sm font-bold border ${cls}`}>
      {grade}
    </span>
  )
}

function fmtPrice(val) {
  if (val == null) return '-'
  return Number(val).toLocaleString()
}

function PosGuideCard({ label, value, sub, color = 'gray' }) {
  const colorMap = {
    red: 'text-red-600 bg-red-50 border-red-200',
    blue: 'text-blue-600 bg-blue-50 border-blue-200',
    green: 'text-green-600 bg-green-50 border-green-200',
    yellow: 'text-yellow-600 bg-yellow-50 border-yellow-200',
    gray: 'text-gray-700 bg-gray-50 border-gray-200',
  }
  const cls = colorMap[color] || colorMap.gray
  return (
    <div className={`border rounded-lg p-3 ${cls}`}>
      <p className="text-xs font-medium opacity-70 mb-1">{label}</p>
      <p className="text-lg font-bold">{value}</p>
      {sub && <p className="text-xs mt-1 opacity-70 leading-relaxed">{sub}</p>}
    </div>
  )
}

function Section({ title, icon, children }) {
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="bg-gray-50 px-4 py-2.5 text-sm font-semibold text-gray-700 border-b border-gray-200">
        {icon} {title}
      </div>
      <div className="p-4">{children}</div>
    </div>
  )
}

// Phase 3: v2 등급 배지 컴포넌트
function SafetyGradeBadge({ grade }) {
  const gradeMap = {
    'A': 'bg-emerald-100 text-emerald-800 border-emerald-400',
    'B+': 'bg-green-100 text-green-700 border-green-400',
    'B': 'bg-yellow-100 text-yellow-700 border-yellow-400',
    'C': 'bg-orange-100 text-orange-700 border-orange-400',
    'D': 'bg-red-100 text-red-700 border-red-400',
  }
  const cls = gradeMap[grade] || 'bg-gray-100 text-gray-600 border-gray-300'
  return (
    <span className={`inline-flex items-center justify-center w-12 h-12 rounded-full text-xl font-black border-2 ${cls}`}>
      {grade}
    </span>
  )
}

// Phase 3: 점수 게이지 바
function ScoreBar({ label, value, max, colorClass = 'bg-blue-500' }) {
  if (value == null) return null
  const pct = Math.min(100, Math.max(0, (value / max) * 100))
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-600">
        <span>{label}</span>
        <span className="font-semibold">{value}/{max}</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div className={`h-2.5 rounded-full ${colorClass}`} style={{ width: `${pct}%` }}></div>
      </div>
    </div>
  )
}

export default function AIReportPanel({ report, history = [], loading, error, onGenerate, onSelectHistory }) {
  const reportData = report?.report || {}
  const generatedAt = report?.generated_at
  const model = report?.model

  const opinion = reportData['종합투자의견'] || reportData.opinion || {}
  const strategies = reportData['전략별평가'] || {}
  const technical = reportData['기술적시그널'] || reportData.technical_signal || {}
  const risks = reportData['리스크요인'] || reportData.risk_factors || []
  const points = reportData['투자포인트'] || reportData.investment_points || []
  const posGuide = reportData['포지션가이드'] || {}

  // Phase 3 v2 필드 (부재 시 null → 카드 숨김)
  const safetyGrade = report?.grade || reportData['종목등급']
  const gradeScore = report?.grade_score ?? reportData['등급점수']
  const compositeScore = report?.composite_score ?? reportData['복합점수']
  const regimeAlignment = report?.regime_alignment ?? reportData['체제정합성점수']
  const valueTrapWarning = report?.value_trap_warning ?? reportData['Value_Trap_경고']
  const valueTrapReasons = reportData['Value_Trap_근거'] || []
  const schemaVersion = report?.schema_version || reportData['schema_version']
  const hasV2 = !!safetyGrade && schemaVersion === 'v2'

  // 원문 fallback
  const rawText = reportData.raw

  return (
    <div className="space-y-4">
      {/* 액션 바 */}
      <div className="flex items-center justify-between gap-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
        <div className="flex items-center gap-3 min-w-0">
          {history.length > 1 ? (
            <select
              value={report?.id ?? ''}
              onChange={e => onSelectHistory && onSelectHistory(Number(e.target.value))}
              className="text-xs border border-gray-300 rounded px-2 py-1 bg-white text-gray-700 max-w-[260px]"
            >
              {history.map(h => (
                <option key={h.id} value={h.id}>
                  {h.generated_at.slice(0, 16).replace('T', ' ')} · {h.model}
                </option>
              ))}
            </select>
          ) : (
            <span className="text-xs text-gray-500">
              {generatedAt
                ? `생성: ${generatedAt.slice(0, 16).replace('T', ' ')} · ${model || ''}`
                : '아직 생성된 리포트가 없습니다.'}
            </span>
          )}
          {history.length > 1 && (
            <span className="text-xs text-gray-400">({history.length}개)</span>
          )}
        </div>
        <button
          onClick={onGenerate}
          disabled={loading}
          className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium shrink-0"
        >
          {loading ? '분석 중...' : 'AI 분석 생성'}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Phase 3: v2 종목 등급 카드 (grade 필드 부재 시 숨김) */}
      {hasV2 && (
        <div className="border border-gray-200 rounded-lg p-4 space-y-3">
          {/* Value Trap 경고 배너 */}
          {valueTrapWarning && (
            <div className="p-3 bg-red-50 border border-red-300 rounded-lg">
              <p className="text-sm font-bold text-red-700 mb-1">Value Trap 경고</p>
              {valueTrapReasons.length > 0 && (
                <ul className="text-xs text-red-600 list-disc list-inside space-y-0.5">
                  {valueTrapReasons.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              )}
            </div>
          )}

          <div className="flex items-center gap-4">
            <SafetyGradeBadge grade={safetyGrade} />
            <div className="flex-1 space-y-2">
              <ScoreBar label="등급 점수" value={gradeScore} max={28} colorClass={
                gradeScore >= 24 ? 'bg-emerald-500' : gradeScore >= 20 ? 'bg-green-500' : gradeScore >= 16 ? 'bg-yellow-500' : gradeScore >= 12 ? 'bg-orange-500' : 'bg-red-500'
              } />
              <ScoreBar label="복합 점수" value={compositeScore != null ? Math.round(compositeScore) : null} max={100} colorClass="bg-blue-500" />
              <ScoreBar label="체제 정합성" value={regimeAlignment != null ? Math.round(regimeAlignment) : null} max={100} colorClass="bg-purple-500" />
            </div>
          </div>

          {/* 등급팩터 + recommendation */}
          {posGuide['등급팩터'] != null && (
            <div className="flex gap-2 text-xs">
              <span className="px-2 py-0.5 bg-gray-100 rounded">등급팩터: {posGuide['등급팩터']}</span>
              {posGuide.recommendation && (
                <span className={`px-2 py-0.5 rounded font-semibold ${
                  posGuide.recommendation === 'ENTER' ? 'bg-green-100 text-green-700' :
                  posGuide.recommendation === 'SKIP' ? 'bg-red-100 text-red-700' :
                  'bg-yellow-100 text-yellow-700'
                }`}>{posGuide.recommendation}</span>
              )}
            </div>
          )}
        </div>
      )}

      {loading && (
        <div className="text-center py-10 text-gray-400 text-sm">
          <div className="animate-spin inline-block w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mb-2" />
          <p>GPT가 분석 중입니다... (10~30초 소요)</p>
        </div>
      )}

      {/* 원문 fallback */}
      {!loading && rawText && (
        <div className="p-4 bg-gray-50 border border-gray-200 rounded text-xs text-gray-700 whitespace-pre-wrap">
          {rawText}
        </div>
      )}

      {/* 종합 투자 의견 */}
      {!loading && !rawText && opinion.등급 && (
        <Section title="종합 투자 의견" icon="📊">
          <div className="flex items-center gap-3 mb-3">
            <GradeBadge grade={opinion.등급} />
            <p className="text-sm text-gray-700">{opinion.요약}</p>
          </div>
          {Array.isArray(opinion.근거) && opinion.근거.length > 0 && (
            <ul className="space-y-1 text-sm text-gray-600 pl-2">
              {opinion.근거.map((g, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-blue-500 font-bold shrink-0">{i + 1}.</span>
                  <span>{g}</span>
                </li>
              ))}
            </ul>
          )}
        </Section>
      )}

      {/* 전략별 평가 */}
      {!loading && !rawText && Object.keys(strategies).length > 0 && (
        <Section title="전략별 평가" icon="🎯">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">

            {/* 변동성 돌파 */}
            {strategies['변동성돌파']?.신호 && (() => {
              const s = strategies['변동성돌파']
              return (
                <div className="border border-gray-200 rounded-lg p-3 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-gray-600">변동성 돌파</span>
                    <GradeBadge grade={s.신호} />
                  </div>
                  {s.목표가 != null && (
                    <p className="text-xs text-gray-500">
                      목표가(K=0.5): <span className="font-semibold text-gray-800">
                        {Number(s.목표가).toLocaleString()}
                      </span>
                    </p>
                  )}
                  <p className="text-xs text-gray-600 leading-relaxed">{s.근거}</p>
                </div>
              )
            })()}

            {/* 안전마진 */}
            {strategies['안전마진']?.신호 && (() => {
              const s = strategies['안전마진']
              return (
                <div className="border border-gray-200 rounded-lg p-3 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-gray-600">안전마진</span>
                    <GradeBadge grade={s.신호} />
                  </div>
                  {s.graham_number != null && (
                    <p className="text-xs text-gray-500">
                      안전마진가격: <span className="font-semibold text-gray-800">
                        {Number(s.graham_number).toLocaleString()}
                      </span>
                    </p>
                  )}
                  {s.할인율 != null && (
                    <p className="text-xs text-gray-500">
                      할인율: <span className={`font-semibold ${s.할인율 > 0 ? 'text-red-600' : 'text-blue-600'}`}>
                        {s.할인율 > 0 ? '+' : ''}{s.할인율}%
                      </span>
                    </p>
                  )}
                  <p className="text-xs text-gray-600 leading-relaxed">{s.근거}</p>
                </div>
              )
            })()}

            {/* 추세추종 */}
            {strategies['추세추종']?.신호 && (() => {
              const s = strategies['추세추종']
              return (
                <div className="border border-gray-200 rounded-lg p-3 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-gray-600">추세추종</span>
                    <GradeBadge grade={s.신호} />
                  </div>
                  {s.추세강도 && (
                    <p className="text-xs text-gray-500">
                      추세강도: <span className="font-semibold text-gray-800">{s.추세강도}</span>
                    </p>
                  )}
                  <p className="text-xs text-gray-600 leading-relaxed">{s.근거}</p>
                </div>
              )
            })()}

          </div>
        </Section>
      )}

      {/* 기술적 시그널 */}
      {!loading && !rawText && technical.신호 && (
        <Section title="기술적 시그널" icon="📈">
          <div className="flex items-center gap-3 mb-3">
            <GradeBadge grade={technical.신호} />
            <p className="text-sm text-gray-700">{technical.해석}</p>
          </div>
          {technical.지표별 && (
            <div className="grid grid-cols-3 gap-2 mt-2">
              {Object.entries(technical.지표별).map(([k, v]) => (
                <div key={k} className="bg-gray-50 rounded p-2 text-xs">
                  <span className="font-semibold text-gray-600 uppercase">{k}</span>
                  <p className="text-gray-700 mt-0.5">{v}</p>
                </div>
              ))}
            </div>
          )}
        </Section>
      )}

      {/* 리스크 요인 */}
      {!loading && !rawText && Array.isArray(risks) && risks.length > 0 && (
        <Section title="리스크 요인" icon="⚠️">
          <ul className="space-y-2">
            {risks.map((r, i) => (
              <li key={i} className="flex gap-3 text-sm">
                <span className="shrink-0 w-5 h-5 rounded-full bg-orange-100 text-orange-700 text-xs flex items-center justify-center font-bold">
                  {i + 1}
                </span>
                <div>
                  <span className="font-semibold text-gray-700">{r.요인 || r.factor}</span>
                  {(r.설명 || r.description) && (
                    <p className="text-gray-500 text-xs mt-0.5">{r.설명 || r.description}</p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* 투자 포인트 */}
      {!loading && !rawText && Array.isArray(points) && points.length > 0 && (
        <Section title="투자 포인트" icon="💡">
          <ul className="space-y-2">
            {points.map((p, i) => (
              <li key={i} className="flex gap-3 text-sm">
                <span className="shrink-0 w-5 h-5 rounded-full bg-green-100 text-green-700 text-xs flex items-center justify-center font-bold">
                  {i + 1}
                </span>
                <div>
                  <span className="font-semibold text-gray-700">{p.포인트 || p.point}</span>
                  {(p.설명 || p.description) && (
                    <p className="text-gray-500 text-xs mt-0.5">{p.설명 || p.description}</p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* 포지션 가이드 */}
      {!loading && !rawText && posGuide['추천진입가'] != null && (() => {
        const rr = posGuide['리스크보상비율']
        return (
          <Section title="포지션 가이드" icon="🎯">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <PosGuideCard
                label="추천 진입가"
                value={fmtPrice(posGuide['추천진입가'])}
                sub={posGuide['진입가근거']}
              />
              <PosGuideCard
                label="손절가"
                value={fmtPrice(posGuide['손절가'])}
                sub={posGuide['손절근거']}
                color="blue"
              />
              <PosGuideCard
                label="1차 익절가"
                value={fmtPrice(posGuide['1차익절가'])}
                sub={posGuide['익절근거']}
                color="red"
              />
              <PosGuideCard
                label="R:R 비율"
                value={rr != null ? Number(rr).toFixed(1) : '-'}
                sub={rr != null ? (rr >= 2 ? '양호 (2.0 이상)' : '주의 (2.0 미만)') : ''}
                color={rr != null ? (rr >= 2 ? 'green' : 'yellow') : 'gray'}
              />
            </div>
            {posGuide['분할매수제안'] && (
              <p className="text-xs text-gray-600 mt-3 p-2 bg-gray-50 rounded">
                분할매수: {posGuide['분할매수제안']}
              </p>
            )}
          </Section>
        )
      })()}

      {/* 리포트 없음 안내 */}
      {!loading && !rawText && !opinion.등급 && !error && (
        <div className="text-center py-8 text-gray-400 text-sm">
          <p className="text-2xl mb-2">🤖</p>
          <p>아직 생성된 AI 리포트가 없습니다.</p>
          <p className="text-xs mt-1">데이터를 새로고침한 후 "AI 분석 생성" 버튼을 클릭하세요.</p>
        </div>
      )}
    </div>
  )
}
