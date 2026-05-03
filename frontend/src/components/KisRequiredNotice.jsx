/**
 * KIS 자격증명 미등록/검증만료 시 자산관리 라우트(/portfolio, /order, /balance, /tax)에서 표시.
 */
import { useNavigate } from 'react-router-dom'

export default function KisRequiredNotice() {
  const navigate = useNavigate()
  return (
    <div className="max-w-xl mx-auto mt-12 p-8 bg-white border border-amber-200 rounded-lg shadow-sm">
      <div className="flex items-start gap-3">
        <span className="text-3xl">🔒</span>
        <div className="flex-1">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">
            KIS API 자격증명이 필요합니다
          </h2>
          <p className="text-sm text-gray-600 leading-relaxed mb-4">
            잔고 / 매매 / 양도세 / 포트폴리오 자문 메뉴는 본인의 한국투자증권 OpenAPI 자격증명이
            필요합니다. 등록 후 즉시 검증되며, 자격증명은 AES-GCM으로 암호화되어 저장됩니다.
          </p>
          <button
            type="button"
            onClick={() => navigate('/settings/kis')}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 transition-colors"
          >
            KIS 자격증명 등록하기 →
          </button>
        </div>
      </div>
    </div>
  )
}
