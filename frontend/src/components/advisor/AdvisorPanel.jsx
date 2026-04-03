import { Link } from 'react-router-dom'
import { usePortfolioAdvisor } from '../../hooks/usePortfolioAdvisor'
import LoadingSpinner from '../common/LoadingSpinner'
import ErrorAlert from '../common/ErrorAlert'
import DiagnosisCard from './DiagnosisCard'
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
            {/* 시장 코멘트 */}
            {analysis.market_context && (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-700">
                {analysis.market_context}
              </div>
            )}

            <DiagnosisCard diagnosis={analysis.diagnosis} />
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
            <Link to="/advisor" className="text-xs text-indigo-500 hover:text-indigo-700">
              AI자문 페이지에서 이력 보기 →
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
