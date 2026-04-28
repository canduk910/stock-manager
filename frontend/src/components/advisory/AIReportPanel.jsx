/**
 * AI자문 탭 — OpenAI GPT-4o 리포트 표시.
 *
 * DetailPage > 종합리포트 > AI자문 서브탭에서 렌더링된다.
 *
 * 구조 (위→아래) — v3 통합 보고서:
 *   1) 등급 카드: SafetyGradeBadge + ScoreBar 3개 + Value Trap 경고
 *   2) 종합투자의견: 등급 배지(매수/중립/매도) + 요약 + 근거
 *   3) 재무건전성분석: risk_level 배지 + OCF/부채/이자보상
 *   4) 밸류에이션분석: 적정가치 + PER/PBR 밴드 + 업종대비 + PEG + 밸류에이션판단
 *   5) 매크로및산업분석: 시장체제해석 + 금리 + 섹터전망 + peak_out + 산업사이클
 *   6) 경영진트랙레코드: 자본배분 + M&A + 배당 + 지배구조
 *   7) 가치함정분석: 하락유형 + 근거 + 안전마진판단
 *   8) 최종매매전략: action + 진입가/손절가/적정가치/R:R/분할매수/업다운/worst_scenario
 *   9) 전략별 정량 평가: 변동성돌파/안전마진/추세추종
 *  10) 기술적시그널: MACD/RSI/Stoch
 *  11) 시나리오분석: 낙관/기본/비관
 *  12) 리스크요인 + 투자포인트
 *
 * v1/v2 하위호환: grade 부재 시 등급 카드 숨김, v3 섹션은 null 체크로 자연스럽게 숨김
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

function RiskBadge({ level }) {
  const colors = {
    '안전': 'bg-green-100 text-green-700',
    '주의': 'bg-yellow-100 text-yellow-700',
    '위험': 'bg-orange-100 text-orange-700',
    '심각': 'bg-red-100 text-red-700',
  }
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${colors[level] || 'bg-gray-100 text-gray-700'}`}>
      리스크: {level}
    </span>
  )
}

function CycleBadge({ phase }) {
  const colors = {
    '도입': 'bg-purple-100 text-purple-700',
    '성장': 'bg-green-100 text-green-700',
    '성숙': 'bg-blue-100 text-blue-700',
    '쇠퇴': 'bg-red-100 text-red-700',
    '불명': 'bg-gray-100 text-gray-700',
  }
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${colors[phase] || 'bg-gray-100 text-gray-700'}`}>
      산업사이클: {phase}
    </span>
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
  const scenarioAnalysis = reportData['시나리오분석'] || null
  const alternatives = reportData['관련투자대안'] || []

  // 등급 카드 필드 (부재 시 null → 카드 숨김)
  const safetyGrade = report?.grade || reportData['종목등급']
  const gradeScore = report?.grade_score ?? reportData['등급점수']
  const compositeScore = report?.composite_score ?? reportData['복합점수']
  const regimeAlignment = report?.regime_alignment ?? reportData['체제정합성점수']
  const valueTrapWarning = report?.value_trap_warning ?? reportData['Value_Trap_경고']
  const valueTrapReasons = reportData['Value_Trap_근거'] || []
  const hasV2 = !!safetyGrade

  // 통합 스키마 6대 분석 섹션 (각 섹션은 null 체크로 렌더 여부 결정)
  const financialHealth = reportData['재무건전성분석'] || null
  const valuationAnalysis = reportData['밸류에이션분석'] || null
  const macroIndustry = reportData['매크로및산업분석'] || null
  const managementTrack = reportData['경영진트랙레코드'] || null
  const valueTrapDeep = reportData['가치함정분석'] || null
  const tradingStrategy = reportData['최종매매전략'] || null

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

          {/* recommendation */}
          {tradingStrategy?.recommendation && (
            <div className="flex gap-2 text-xs">
              <span className={`px-2 py-0.5 rounded font-semibold ${
                tradingStrategy.recommendation === 'ENTER' ? 'bg-green-100 text-green-700' :
                tradingStrategy.recommendation === 'SKIP' ? 'bg-red-100 text-red-700' :
                'bg-yellow-100 text-yellow-700'
              }`}>{tradingStrategy.recommendation}</span>
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
        <Section title="종합 투자 의견" icon="">
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

      {/* 재무 건전성 분석 */}
      {!loading && !rawText && financialHealth && (
        <Section title="재무 건전성 분석" icon="">
          {financialHealth.risk_level && (
            <RiskBadge level={financialHealth.risk_level} />
          )}
          {financialHealth.ocf_vs_net_income && (
            <div className="mt-2">
              <p className="text-xs font-medium text-gray-600 mb-1">OCF vs 순이익 괴리</p>
              <p className="text-sm text-gray-700">{financialHealth.ocf_vs_net_income}</p>
            </div>
          )}
          {financialHealth.debt_ratio_analysis && (
            <div className="mt-2">
              <p className="text-xs font-medium text-gray-600 mb-1">부채비율 분석</p>
              <p className="text-sm text-gray-700">{financialHealth.debt_ratio_analysis}</p>
            </div>
          )}
          {financialHealth.interest_coverage_analysis && (
            <div className="mt-2">
              <p className="text-xs font-medium text-gray-600 mb-1">이자보상배율</p>
              <p className="text-sm text-gray-700">{financialHealth.interest_coverage_analysis}</p>
            </div>
          )}
          {financialHealth.summary && (
            <p className="mt-2 text-sm text-gray-800 font-medium bg-gray-50 p-2 rounded">{financialHealth.summary}</p>
          )}
        </Section>
      )}

      {/* 밸류에이션 분석 */}
      {!loading && !rawText && valuationAnalysis && (
        <Section title="밸류에이션 분석" icon="">
          {valuationAnalysis.적정가치 != null && (
            <div className="flex items-center gap-4 mb-2">
              <span className="text-lg font-bold text-gray-800">{fmtPrice(valuationAnalysis.적정가치)}</span>
              {valuationAnalysis.산출방법 && <span className="text-xs text-gray-500">({valuationAnalysis.산출방법})</span>}
            </div>
          )}
          {valuationAnalysis.per_band_position && (
            <div className="mt-2">
              <p className="text-xs font-medium text-gray-600 mb-1">PER 밴드 위치</p>
              <p className="text-sm text-gray-700">{valuationAnalysis.per_band_position}</p>
            </div>
          )}
          {valuationAnalysis.pbr_band_position && (
            <div className="mt-2">
              <p className="text-xs font-medium text-gray-600 mb-1">PBR 밴드 위치</p>
              <p className="text-sm text-gray-700">{valuationAnalysis.pbr_band_position}</p>
            </div>
          )}
          {valuationAnalysis.earnings_price_correlation && (
            <div className="mt-2">
              <p className="text-xs font-medium text-gray-600 mb-1">실적-주가 상관관계</p>
              <p className="text-sm text-gray-700">{valuationAnalysis.earnings_price_correlation}</p>
            </div>
          )}
          {valuationAnalysis.업종대비 && (
            <div className="mt-2">
              <p className="text-xs font-medium text-gray-600 mb-1">업종 대비</p>
              <p className="text-sm text-gray-700">{valuationAnalysis.업종대비}</p>
            </div>
          )}
          {valuationAnalysis.PEG분석 && (
            <div className="mt-2">
              <p className="text-xs font-medium text-gray-600 mb-1">PEG 분석</p>
              <p className="text-sm text-gray-700">{valuationAnalysis.PEG분석}</p>
            </div>
          )}
          {valuationAnalysis.밸류에이션판단 && (
            <p className="mt-2 text-sm font-medium bg-gray-50 p-2 rounded">{valuationAnalysis.밸류에이션판단}</p>
          )}
          {valuationAnalysis.historical_judgment && (
            <p className="mt-2 text-sm text-gray-800 font-medium bg-gray-50 p-2 rounded">{valuationAnalysis.historical_judgment}</p>
          )}
        </Section>
      )}

      {/* 매크로 및 산업 분석 */}
      {!loading && !rawText && macroIndustry && (
        <Section title="매크로 및 산업 분석" icon="">
          <div className="flex gap-2 mb-2">
            {macroIndustry.industry_cycle_phase && <CycleBadge phase={macroIndustry.industry_cycle_phase} />}
          </div>
          {macroIndustry.시장체제해석 && <p className="text-sm text-gray-700 mb-2">{macroIndustry.시장체제해석}</p>}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-2">
            {macroIndustry.금리영향 && (
              <div className="bg-blue-50 rounded-lg p-3">
                <p className="text-xs font-semibold text-blue-700 mb-1">금리 영향</p>
                <p className="text-xs text-gray-700">{macroIndustry.금리영향}</p>
              </div>
            )}
            {macroIndustry.섹터전망 && (
              <div className="bg-green-50 rounded-lg p-3">
                <p className="text-xs font-semibold text-green-700 mb-1">섹터 전망</p>
                <p className="text-xs text-gray-700">{macroIndustry.섹터전망}</p>
              </div>
            )}
            {macroIndustry.매크로리스크 && (
              <div className="bg-red-50 rounded-lg p-3">
                <p className="text-xs font-semibold text-red-700 mb-1">매크로 리스크</p>
                <p className="text-xs text-gray-700">{macroIndustry.매크로리스크}</p>
              </div>
            )}
          </div>
          {macroIndustry.peak_out_assessment && (
            <div className="mt-2">
              <p className="text-xs font-medium text-gray-600 mb-1">Peak-out 검증</p>
              <p className="text-sm text-gray-700">{macroIndustry.peak_out_assessment}</p>
            </div>
          )}
          {macroIndustry.macro_risk_factors?.length > 0 && (
            <div className="mt-2">
              <p className="text-xs font-medium text-gray-600 mb-1">매크로 리스크 요인</p>
              <ul className="list-disc list-inside text-sm text-gray-700">
                {macroIndustry.macro_risk_factors.map((f, i) => <li key={i}>{f}</li>)}
              </ul>
            </div>
          )}
          {macroIndustry.outlook && (
            <p className="mt-2 text-sm text-gray-800 font-medium bg-gray-50 p-2 rounded">{macroIndustry.outlook}</p>
          )}
        </Section>
      )}

      {/* 경영진 트랙 레코드 */}
      {!loading && !rawText && managementTrack && (
        <Section title="경영진 트랙 레코드" icon="">
          {managementTrack.capital_allocation_grade && (
            <div className="mb-2">
              <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                managementTrack.capital_allocation_grade === '우수' ? 'bg-green-100 text-green-700' :
                managementTrack.capital_allocation_grade === '양호' ? 'bg-blue-100 text-blue-700' :
                managementTrack.capital_allocation_grade === '보통' ? 'bg-yellow-100 text-yellow-700' :
                'bg-red-100 text-red-700'
              }`}>
                자본배분: {managementTrack.capital_allocation_grade}
              </span>
            </div>
          )}
          {managementTrack.ma_track_record && (
            <div>
              <p className="text-xs font-medium text-gray-600 mb-1">M&A 이력</p>
              <p className="text-sm text-gray-700">{managementTrack.ma_track_record}</p>
            </div>
          )}
          {managementTrack.dividend_policy && (
            <div className="mt-2">
              <p className="text-xs font-medium text-gray-600 mb-1">배당 정책</p>
              <p className="text-sm text-gray-700">{managementTrack.dividend_policy}</p>
            </div>
          )}
          {managementTrack.governance_assessment && (
            <p className="mt-2 text-sm text-gray-800 font-medium bg-gray-50 p-2 rounded">{managementTrack.governance_assessment}</p>
          )}
        </Section>
      )}

      {/* 가치함정 분석 */}
      {!loading && !rawText && valueTrapDeep && (
        <Section title="가치함정 분석" icon="">
          {valueTrapDeep.decline_type && (
            <div className="mb-2">
              <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                valueTrapDeep.decline_type === '구조적_쇠퇴' ? 'bg-red-100 text-red-700' :
                valueTrapDeep.decline_type === '일시적_악재' ? 'bg-yellow-100 text-yellow-700' :
                'bg-gray-100 text-gray-700'
              }`}>
                {valueTrapDeep.decline_type.replace('_', ' ')}
              </span>
            </div>
          )}
          {valueTrapDeep.evidence?.length > 0 && (
            <ul className="list-disc list-inside text-sm text-gray-700 mb-2">
              {valueTrapDeep.evidence.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          )}
          {valueTrapDeep.safety_margin_assessment && (
            <p className="text-sm text-gray-800 font-medium bg-gray-50 p-2 rounded">{valueTrapDeep.safety_margin_assessment}</p>
          )}
        </Section>
      )}

      {/* 최종 매매 전략 */}
      {!loading && !rawText && tradingStrategy && (
        <Section title="최종 매매 전략" icon="">
          {tradingStrategy.action && (
            <div className="mb-3">
              <span className={`inline-block px-3 py-1 rounded-full text-sm font-bold ${
                tradingStrategy.action.includes('매수') ? 'bg-red-100 text-red-700' :
                tradingStrategy.action === '관망' ? 'bg-yellow-100 text-yellow-700' :
                'bg-blue-100 text-blue-700'
              }`}>{tradingStrategy.action}</span>
              {tradingStrategy.recommendation && (
                <span className={`ml-2 px-2 py-0.5 rounded text-xs font-medium ${
                  tradingStrategy.recommendation === 'ENTER' ? 'bg-green-100 text-green-700' :
                  tradingStrategy.recommendation === 'HOLD' ? 'bg-yellow-100 text-yellow-700' :
                  'bg-red-100 text-red-700'
                }`}>{tradingStrategy.recommendation}</span>
              )}
            </div>
          )}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <PosGuideCard label="추천 진입가" value={fmtPrice(tradingStrategy.추천진입가 ?? tradingStrategy.entry_price)} sub={tradingStrategy.진입가근거} />
            <PosGuideCard label="손절가" value={fmtPrice(tradingStrategy.손절가 ?? tradingStrategy.stop_loss)} sub={tradingStrategy.손절근거} color="blue" />
            <PosGuideCard label="적정가치" value={fmtPrice(tradingStrategy.적정가치 ?? tradingStrategy.fair_value)} sub={tradingStrategy.적정가치산출 ?? tradingStrategy.fair_value_method} color="green" />
            {tradingStrategy.리스크보상비율 != null && (
              <PosGuideCard label="R:R 비율" value={Number(tradingStrategy.리스크보상비율).toFixed(1)}
                sub={tradingStrategy.리스크보상비율 >= 2 ? '양호 (2.0↑)' : '주의 (2.0↓)'}
                color={tradingStrategy.리스크보상비율 >= 2 ? 'green' : 'yellow'} />
            )}
          </div>
          {(tradingStrategy.upside_pct != null || tradingStrategy.downside_pct != null) && (
            <div className="flex gap-4 mt-3 text-sm">
              {tradingStrategy.upside_pct != null && <span className="text-red-600 font-medium">Upside: +{tradingStrategy.upside_pct}%</span>}
              {tradingStrategy.downside_pct != null && <span className="text-blue-600 font-medium">Downside: -{tradingStrategy.downside_pct}%</span>}
            </div>
          )}
          {tradingStrategy.worst_scenario && (
            <div className="bg-red-50 border border-red-100 rounded p-2 mt-3">
              <p className="text-xs font-medium text-red-600 mb-1">최악 시나리오</p>
              <p className="text-sm text-red-700">{tradingStrategy.worst_scenario}</p>
            </div>
          )}
          {tradingStrategy.분할매수제안 && (
            <p className="text-xs text-gray-600 mt-2 p-2 bg-gray-50 rounded">분할매수: {tradingStrategy.분할매수제안}</p>
          )}
          {tradingStrategy.position_sizing && (
            <p className="text-xs text-gray-600 mt-2 p-2 bg-gray-50 rounded">포지션: {tradingStrategy.position_sizing}</p>
          )}
        </Section>
      )}

      {/* 전략별 평가 */}
      {!loading && !rawText && Object.keys(strategies).length > 0 && (
        <Section title="전략별 평가" icon="">
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
        <Section title="기술적 시그널" icon="">
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

      {/* 시나리오 분석 */}
      {!loading && !rawText && scenarioAnalysis && (
        <Section title="시나리오 분석 (12개월)" icon="">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {['낙관', '기본', '비관'].map(key => {
              const s = scenarioAnalysis[key]
              if (!s) return null
              const colorMap = {
                '낙관': { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', label: 'Bull' },
                '기본': { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-700', label: 'Base' },
                '비관': { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', label: 'Bear' },
              }
              const c = colorMap[key]
              return (
                <div key={key} className={`border ${c.border} rounded-lg p-3 ${c.bg}`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className={`text-xs font-bold ${c.text}`}>{key} ({c.label})</span>
                    {s['확률'] != null && (
                      <span className="text-xs font-semibold text-gray-500">{s['확률']}%</span>
                    )}
                  </div>
                  {s['목표가'] != null && (
                    <p className={`text-lg font-bold ${c.text} mb-1`}>{fmtPrice(s['목표가'])}</p>
                  )}
                  <p className="text-xs text-gray-600 leading-relaxed">{s['근거']}</p>
                </div>
              )
            })}
          </div>
        </Section>
      )}

      {/* 리스크 요인 */}
      {!loading && !rawText && Array.isArray(risks) && risks.length > 0 && (
        <Section title="리스크 요인" icon="">
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
        <Section title="투자 포인트" icon="">
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

      {/* 관련 투자 대안 */}
      {!loading && !rawText && Array.isArray(alternatives) && alternatives.length > 0 && (
        <Section title="관련 투자 대안" icon="">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {alternatives.map((alt, i) => (
              <div key={i} className="flex gap-3 border border-gray-200 rounded-lg p-3">
                <span className={`shrink-0 px-2 py-0.5 h-fit rounded text-xs font-bold ${
                  alt['유형'] === 'ETF' ? 'bg-purple-100 text-purple-700' :
                  alt['유형'] === '원자재' ? 'bg-yellow-100 text-yellow-700' :
                  alt['유형'] === '채권' ? 'bg-blue-100 text-blue-700' :
                  alt['유형'] === '지수' ? 'bg-green-100 text-green-700' :
                  'bg-gray-100 text-gray-700'
                }`}>{alt['유형']}</span>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-gray-800">
                    {alt['종목명']}
                    {alt['코드'] && <span className="text-xs text-gray-400 ml-1">({alt['코드']})</span>}
                  </p>
                  <p className="text-xs text-gray-600 mt-0.5 leading-relaxed">{alt['사유']}</p>
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* 리포트 없음 안내 */}
      {!loading && !rawText && !opinion.등급 && !error && (
        <div className="text-center py-8 text-gray-400 text-sm">
          <p className="text-2xl mb-2">🤖</p>
          <p>아직 생성된 AI 리포트가 없습니다.</p>
          <p className="text-xs mt-1">"새로고침" 후 "AI분석 생성" 버튼을 클릭하세요.</p>
        </div>
      )}
    </div>
  )
}
