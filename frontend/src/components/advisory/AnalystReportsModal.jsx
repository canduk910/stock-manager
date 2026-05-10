/**
 * 증권사별 목표가 + 리포트 모달.
 *
 * 본문은 AnalystReportsTable 공용 컴포넌트 재사용.
 * 데이터 흐름은 GPT 호출 0건 (네이버 리서치 스크래핑 / yfinance 등급).
 *
 * Props: { code, market, currentPrice, onClose }
 */
import AnalystReportsTable from './AnalystReportsTable'

export default function AnalystReportsModal({ code, market = 'KR', currentPrice, onClose }) {
  const handleBackdrop = (e) => {
    if (e.target === e.currentTarget) onClose()
  }
  const isKR = market === 'KR'

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={handleBackdrop}>
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-3 border-b">
          <h3 className="text-base font-bold text-gray-900">
            {isKR ? '📊 증권사 목표가' : '📊 Analyst Ratings'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
        </div>
        <div className="overflow-y-auto flex-1 px-5 py-3">
          <AnalystReportsTable code={code} market={market} currentPrice={currentPrice} />
        </div>
      </div>
    </div>
  )
}
