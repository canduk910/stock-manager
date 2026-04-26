import { useScreener } from '../hooks/useScreener'
import FilterPanel from '../components/screener/FilterPanel'
import StockTable from '../components/screener/StockTable'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorAlert from '../components/common/ErrorAlert'
import EmptyState from '../components/common/EmptyState'

const PRESET_LABELS = {
  greenblatt: 'Greenblatt Magic Formula',
  neff: 'Neff Total Return',
  seo: '서준식 기대수익률',
}

const REGIME_STYLES = {
  defensive:    { bg: 'bg-red-50', border: 'border-red-300', badge: 'bg-red-100 text-red-700' },
  cautious:     { bg: 'bg-amber-50', border: 'border-amber-300', badge: 'bg-amber-100 text-amber-700' },
  selective:    { bg: 'bg-green-50', border: 'border-green-300', badge: 'bg-green-100 text-green-700' },
  accumulation: { bg: 'bg-blue-50', border: 'border-blue-300', badge: 'bg-blue-100 text-blue-700' },
}

const REGIME_MSG = {
  defensive:    '방어 체제 — 신규 매수 자제, 현금 비중 확대',
  cautious:     '신중 체제 — 최우량 저평가주만 선별',
  selective:    '선별 체제 — 표준 기준 적극 매수',
  accumulation: '축적 체제 — 관대한 기준 적극 매수',
}

export default function ScreenerPage() {
  const { data, loading, error, search } = useScreener()

  const regime = data?.regime
  const rs = regime ? REGIME_STYLES[regime.regime] || {} : null
  const hasGuru = data?.stocks?.some(s => s.guru_scores != null)

  const loadingMsg = data?.preset === 'greenblatt' || data?.preset === 'neff'
    ? 'DART 재무데이터 수집 중... (30개 종목 기준 1~2분)'
    : '전종목 데이터 수집 중... (첫 조회 시 수십 초 소요)'

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">종목 스크리너</h1>

      {/* 체제 배너 */}
      {regime && rs && (
        <div className={`rounded-xl border px-5 py-3 flex items-center justify-between ${rs.bg} ${rs.border}`}>
          <div className="flex items-center gap-3">
            <span className={`px-3 py-1 rounded-full text-xs font-bold ${rs.badge}`}>
              {regime.regime}
            </span>
            <span className="text-sm text-gray-600">{REGIME_MSG[regime.regime]}</span>
          </div>
          <div className="flex items-center gap-4 text-xs text-gray-500">
            {regime.fear_greed_score != null && (
              <span>F&G <strong>{Math.round(regime.fear_greed_score)}</strong></span>
            )}
            {regime.vix != null && (
              <span>VIX <strong>{Number(regime.vix).toFixed(1)}</strong></span>
            )}
            {regime.buffett_ratio != null && (
              <span>Buffett <strong>{Number(regime.buffett_ratio).toFixed(2)}</strong></span>
            )}
          </div>
        </div>
      )}

      <div className="grid grid-cols-[300px_1fr] gap-6 items-start">
        <FilterPanel onSearch={search} loading={loading} />

        <div className="space-y-3">
          {loading && <LoadingSpinner message={loadingMsg} />}
          <ErrorAlert message={error} />

          {data && !loading && (
            <>
              <div className="flex items-center gap-3">
                <p className="text-sm text-gray-500">
                  <span className="font-semibold text-gray-800">{data.total.toLocaleString()}종목</span> 조회됨
                  {data.date && ` (${data.date.slice(0, 4)}-${data.date.slice(4, 6)}-${data.date.slice(6)})`}
                </p>
                {data.preset && (
                  <span className="px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700">
                    {PRESET_LABELS[data.preset] || data.preset}
                  </span>
                )}
              </div>
              {data.stocks.length === 0 ? (
                <EmptyState message="조건에 맞는 종목이 없습니다." />
              ) : (
                <StockTable stocks={data.stocks} hasGuru={hasGuru} />
              )}
            </>
          )}

          {!data && !loading && !error && (
            <EmptyState message="필터를 설정하고 '조회하기'를 눌러주세요." />
          )}
        </div>
      </div>
    </div>
  )
}
