import { useEffect } from 'react'
import { useBalance } from '../hooks/useBalance'
import { usePortfolioAdvisor } from '../hooks/usePortfolioAdvisor'
import AdvisorPanel from '../components/advisor/AdvisorPanel'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorAlert from '../components/common/ErrorAlert'

export default function AdvisorPage({ notify }) {
  const { data: balanceData, loading: balLoading, error: balError, load: loadBalance } = useBalance()
  const advisor = usePortfolioAdvisor()

  useEffect(() => {
    loadBalance()
    advisor.loadHistory()
  }, [])

  const isKeyMissing = balError && (balError.includes('설정되지 않았습니다') || balError.includes('503'))

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">AI 투자자문</h1>

      {/* 잔고 로딩 */}
      {balLoading && <LoadingSpinner message="잔고 데이터 로딩 중..." />}

      {/* 잔고 에러 */}
      {balError && !balLoading && (
        isKeyMissing ? (
          <div className="rounded-xl border border-amber-300 bg-amber-50 p-5 text-sm text-amber-800 space-y-1">
            <p className="font-semibold">KIS API 키가 설정되지 않았습니다</p>
            <p>{balError}</p>
            <p className="text-xs text-amber-600 mt-2">
              .env 파일에 KIS_APP_KEY, KIS_APP_SECRET, KIS_ACNT_NO, KIS_ACNT_PRDT_CD_STK를 설정하면 AI 자문을 사용할 수 있습니다.
            </p>
          </div>
        ) : (
          <ErrorAlert message={balError} />
        )
      )}

      {/* 잔고 로드 완료 → 자문 패널 */}
      {balanceData && !balLoading && (
        <AdvisorPanel
          balanceData={balanceData}
          notify={notify}
          advisor={advisor}
          showHistory={true}
        />
      )}

      {/* 이력만 있고 잔고 없는 경우에도 이력 표시 */}
      {!balanceData && !balLoading && advisor.history.length > 0 && (
        <div className="border border-gray-200 rounded-xl p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">이전 자문 이력</h2>
          <div className="space-y-2">
            {advisor.history.map(h => (
              <button
                key={h.id}
                onClick={() => advisor.loadById(h.id)}
                className="block w-full text-left px-3 py-2 rounded-lg hover:bg-gray-50 text-sm text-gray-600 border border-gray-100"
              >
                <span className="font-medium">{h.generated_at.slice(0, 16).replace('T', ' ')}</span>
                <span className="text-gray-400 ml-2">· {h.model}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
