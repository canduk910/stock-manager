import { Link } from 'react-router-dom'
import { usePortfolioAdvisor } from '../../hooks/usePortfolioAdvisor'
import LoadingSpinner from '../common/LoadingSpinner'
import ErrorAlert from '../common/ErrorAlert'
import DiagnosisCard from './DiagnosisCard'
import SectorRecommendationCard from './SectorRecommendationCard'
import RebalanceCard from './RebalanceCard'
import TradeTable from './TradeTable'

export default function AdvisorPanel({ balanceData, notify, advisor: externalAdvisor, showHistory = false }) {
  // 외부에서 advisor 훅을 주입받거나 (AdvisorPage), 내부에서 생성 (BalancePage)
  const internalAdvisor = usePortfolioAdvisor()
  const advisor = externalAdvisor || internalAdvisor

  const { result, history, loading, error, analyze, loadById } = advisor
  const analysis = result?.data
  const cached = result?.cached
  const analyzedAt = result?.analyzed_at
  const reportId = result?.report_id

  const hasHoldings =
    (balanceData?.stock_list?.length > 0) ||
    (balanceData?.overseas_list?.length > 0)

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      {/* 헤더 */}
      <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-indigo-50 to-purple-50 border-b border-gray-200">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">AI 포트폴리오 자문</h2>
          <p className="text-xs text-gray-500 mt-0.5">OpenAI GPT 기반 포트폴리오 분석</p>
        </div>
        <div className="flex items-center gap-2">
          {/* 이력 드롭다운 (showHistory 모드에서만) */}
          {showHistory && history.length > 1 && (
            <select
              value={reportId ?? ''}
              onChange={e => loadById(Number(e.target.value))}
              className="text-xs border border-gray-300 rounded px-2 py-1 bg-white text-gray-700 max-w-[240px]"
            >
              {history.map(h => (
                <option key={h.id} value={h.id}>
                  {h.generated_at.slice(0, 16).replace('T', ' ')} · {h.model}
                </option>
              ))}
            </select>
          )}
          {/* 캐시 정보 */}
          {cached && analyzedAt && (
            <span className="text-xs text-gray-400">
              {analyzedAt.slice(11, 16)} 분석
            </span>
          )}
          {/* 새로 분석 버튼 (결과 표시 중일 때) */}
          {analysis && !loading && (
            <button
              onClick={() => analyze(balanceData, true)}
              disabled={loading}
              className="px-3 py-1.5 text-xs font-medium text-indigo-600 border border-indigo-300 rounded-lg hover:bg-indigo-50 disabled:opacity-50 transition-colors"
            >
              새로 분석
            </button>
          )}
          {/* 최초 분석 버튼 */}
          {!analysis && !loading && (
            <button
              onClick={() => analyze(balanceData)}
              disabled={!hasHoldings || loading}
              className="px-4 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              분석 받기
            </button>
          )}
        </div>
      </div>

      {/* 본문 */}
      <div className="p-4">
        {/* 보유 종목 없음 */}
        {!hasHoldings && !loading && !analysis && (
          <p className="text-sm text-gray-400 text-center py-6">
            보유 종목이 없어 자문을 받을 수 없습니다.
          </p>
        )}

        {/* 로딩 */}
        {loading && (
          <div className="py-8">
            <LoadingSpinner message="포트폴리오 분석 중... (10~20초)" />
          </div>
        )}

        {/* 에러 */}
        {error && !loading && <ErrorAlert message={error} />}

        {/* 결과 */}
        {analysis && !loading && (
          <div className="space-y-4">
            {/* 파싱 실패 안내 */}
            {analysis.raw && !analysis.diagnosis && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-700">
                AI 분석 결과를 표시할 수 없습니다. "새로 분석" 버튼을 클릭해 다시 시도해주세요.
              </div>
            )}

            {/* 시장 코멘트 */}
            {analysis.market_context && (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-700">
                {analysis.market_context}
              </div>
            )}

            {/* Phase 3: 개별 종목 리포트 연계 요약 카드 (portfolio_grade_weighted_avg 부재 시 숨김) */}
            {result?.data && (result?.weighted_grade_avg != null || result?.data?.portfolio_grade_weighted_avg != null) && (() => {
              const wga = result?.weighted_grade_avg ?? result?.data?.portfolio_grade_weighted_avg
              const regime = result?.regime ?? result?.data?.regime
              const gdist = result?.data?.grade_distribution || {}
              const belowB = (gdist['C'] || 0) + (gdist['D'] || 0)
              const gradeColor = wga >= 24 ? 'text-emerald-600' : wga >= 20 ? 'text-green-600' : wga >= 16 ? 'text-yellow-600' : wga >= 12 ? 'text-orange-600' : 'text-red-600'
              return (
                <div className="border border-indigo-200 rounded-lg p-3 bg-indigo-50/30 space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-indigo-700">개별 종목 리포트 연계</h4>
                    {regime && <span className="text-xs px-2 py-0.5 bg-indigo-100 text-indigo-600 rounded">{regime}</span>}
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-center">
                      <p className="text-xs text-gray-500">가중 평균 등급</p>
                      <p className={`text-2xl font-black ${gradeColor}`}>{wga?.toFixed(1)}</p>
                      <p className="text-xs text-gray-400">/28</p>
                    </div>
                    <div className="flex-1 flex gap-1 items-end h-8">
                      {['A','B+','B','C','D','unknown'].map(g => {
                        const cnt = gdist[g] || 0
                        const colors = { A: 'bg-emerald-400', 'B+': 'bg-green-400', B: 'bg-yellow-400', C: 'bg-orange-400', D: 'bg-red-400', unknown: 'bg-gray-300' }
                        return cnt > 0 ? (
                          <div key={g} className="flex flex-col items-center flex-1">
                            <span className="text-[10px] text-gray-500">{cnt}</span>
                            <div className={`w-full rounded-t ${colors[g]}`} style={{ height: `${Math.min(cnt * 8, 24)}px` }}></div>
                            <span className="text-[10px] text-gray-400">{g}</span>
                          </div>
                        ) : null
                      })}
                    </div>
                  </div>
                  {belowB > 0 && (
                    <p className="text-xs text-orange-600">C/D 등급 {belowB}개 종목 — 우선 정리 권고</p>
                  )}
                  {wga != null && wga < 16 && (
                    <p className="text-xs text-red-600 font-semibold">가중 평균 B 미만 — 신규 편입 전면 보류</p>
                  )}
                </div>
              )
            })()}

            <DiagnosisCard diagnosis={analysis.diagnosis} />
            <SectorRecommendationCard recommendations={analysis.sector_recommendations} />
            <RebalanceCard suggestions={analysis.rebalancing} />
            <TradeTable trades={analysis.trades} notify={notify} />

            {/* 면책 조항 */}
            <p className="text-xs text-gray-400 text-center pt-2">
              {analysis.disclaimer || 'AI 분석은 참고용이며, 투자 판단의 책임은 투자자 본인에게 있습니다.'}
            </p>
          </div>
        )}

        {/* 초기 안내 (분석 전, 보유종목 있을 때) */}
        {!analysis && !loading && !error && hasHoldings && (
          <p className="text-sm text-gray-400 text-center py-6">
            "분석 받기" 버튼을 클릭하면 보유 포트폴리오를 AI가 분석합니다.
          </p>
        )}

        {/* BalancePage에서: AI자문 페이지 링크 */}
        {!showHistory && (
          <div className="text-center pt-2">
            <Link to="/portfolio" className="text-xs text-indigo-500 hover:text-indigo-700">
              포트폴리오에서 이력 보기 →
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
