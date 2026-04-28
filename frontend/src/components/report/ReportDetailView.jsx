/**
 * 보고서 상세 뷰.
 *
 * Props:
 *   report     — 현재 표시할 보고서 (report_json 포함)
 *   altReport  — 다른 시장 보고서 (KR↔US). 있으면 토글 표시
 *   market     — 현재 선택된 시장 ('KR'|'US')
 *   onMarketChange(m) — KR/US 전환 콜백
 *   loading, error — 로딩/에러 상태
 *
 * 매크로 카드(체제+지수)는 공유, 섹터 추천은 market별 전환.
 */
import { Link } from 'react-router-dom'
import SectorConceptTabs from './SectorConceptTabs'
import LoadingSpinner from '../common/LoadingSpinner'
import ErrorAlert from '../common/ErrorAlert'

const REGIME_COLORS = {
  accumulation: { bg: 'bg-green-50',  border: 'border-green-300',  text: 'text-green-800',  badge: 'bg-green-100 text-green-800' },
  selective:    { bg: 'bg-yellow-50', border: 'border-yellow-300', text: 'text-yellow-800', badge: 'bg-yellow-100 text-yellow-800' },
  cautious:     { bg: 'bg-orange-50', border: 'border-orange-300', text: 'text-orange-800', badge: 'bg-orange-100 text-orange-800' },
  defensive:    { bg: 'bg-red-50',    border: 'border-red-300',    text: 'text-red-800',    badge: 'bg-red-100 text-red-800' },
}

const GRADE_COLORS = {
  A:   'bg-green-100 text-green-800',
  'B+': 'bg-blue-100 text-blue-800',
  B:   'bg-yellow-100 text-yellow-800',
  C:   'bg-orange-100 text-orange-800',
  D:   'bg-red-100 text-red-800',
}

function fmtPrice(val) {
  if (val == null) return '-'
  return Number(val).toLocaleString()
}

export default function ReportDetailView({ report, altReport, market, onMarketChange, loading, error }) {
  if (loading) return <div className="py-6"><LoadingSpinner /></div>
  if (error) return <ErrorAlert message={error} />
  if (!report) return null

  const rj = report.report_json
  const isV2 = rj?.version >= 2

  if (!isV2) {
    return (
      <div className="p-4 bg-gray-50 rounded-lg">
        <pre className="whitespace-pre-wrap text-sm text-gray-700">{report.report_markdown}</pre>
      </div>
    )
  }

  const regime = rj.regime_data || {}
  const snapshot = rj.macro_snapshot || {}
  const rc = REGIME_COLORS[regime.regime] || REGIME_COLORS.selective

  // 현재 선택된 market의 섹터/추천 데이터
  const activeReport = (market && altReport && report.market !== market) ? altReport : report
  const activeRj = activeReport?.report_json || rj
  const sectorRecs = (activeRj.sector_recommendations || {})
  const recommendations = activeRj.recommendations || []
  const hasAlt = !!altReport

  return (
    <div className="space-y-4">
      {/* 매크로 체제 카드 (공유) */}
      <div className={`${rc.bg} border ${rc.border} rounded-lg p-4`}>
        <div className="flex items-center gap-3 mb-3">
          <span className="text-lg font-bold text-gray-900">{report.date}</span>
          <span className={`px-3 py-1 rounded-full text-sm font-bold ${rc.badge}`}>
            {regime.regime}
          </span>
          <span className={`text-sm ${rc.text}`}>{regime.regime_desc}</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-center">
          {regime.vix != null && (
            <div>
              <div className="text-xs text-gray-500">VIX</div>
              <div className="text-lg font-bold text-gray-900">{Number(regime.vix).toFixed(1)}</div>
            </div>
          )}
          {regime.buffett_ratio != null && (
            <div>
              <div className="text-xs text-gray-500">Buffett</div>
              <div className="text-lg font-bold text-gray-900">{Number(regime.buffett_ratio).toFixed(2)}</div>
            </div>
          )}
          {regime.fear_greed_score != null && (
            <div>
              <div className="text-xs text-gray-500">F&G</div>
              <div className="text-lg font-bold text-gray-900">{Math.round(regime.fear_greed_score)}</div>
            </div>
          )}
        </div>

        {(snapshot.indices || []).length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 mt-3 pt-3 border-t border-gray-200/50">
            {snapshot.indices.map((idx, i) => (
              <div key={i} className="text-center">
                <div className="text-xs text-gray-500">{idx.name}</div>
                <div className="text-sm font-semibold text-gray-800">
                  {idx.price != null ? Number(idx.price).toLocaleString(undefined, { maximumFractionDigits: 0 }) : '-'}
                </div>
                {idx.change_pct != null && (
                  <div className={`text-xs font-medium ${idx.change_pct > 0 ? 'text-red-600' : idx.change_pct < 0 ? 'text-blue-600' : 'text-gray-500'}`}>
                    {idx.change_pct > 0 ? '+' : ''}{Number(idx.change_pct).toFixed(1)}%
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* KR/US 토글 (altReport 존재 시만) */}
      {hasAlt && onMarketChange && (
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-600">시장 선택</span>
          <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
            {['KR', 'US'].map((m) => (
              <button
                key={m}
                onClick={() => onMarketChange(m)}
                className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  market === m
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {m === 'KR' ? '🇰🇷 한국' : '🇺🇸 미국'}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 섹터 추천 */}
      {(sectorRecs.concepts || []).length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="text-base font-bold text-gray-900 mb-3">탑픽 섹터 추천</h3>
          <SectorConceptTabs concepts={sectorRecs.concepts} market={market || report.market} />
        </div>
      )}

      {/* 파이프라인 추천 종목 */}
      {recommendations.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="text-base font-bold text-gray-900 mb-3">
            매수 추천 <span className="text-sm font-normal text-gray-500">({recommendations.length}건)</span>
          </h3>
          <div className="space-y-3">
            {recommendations.map((rec, i) => (
              <div key={i} className="border border-gray-100 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${GRADE_COLORS[rec.safety_grade] || 'bg-gray-100'}`}>
                    {rec.safety_grade}
                  </span>
                  <Link to={`/detail/${rec.code}`} className="text-sm font-semibold text-gray-900 hover:text-blue-600">
                    {rec.name}
                  </Link>
                  <span className="text-xs text-gray-400">{rec.code}</span>
                  {rec.discount_rate != null && (
                    <span className="text-xs text-green-600 ml-auto">할인율 {rec.discount_rate.toFixed(0)}%</span>
                  )}
                </div>
                <div className="flex gap-4 text-xs text-gray-600">
                  <span>진입 {fmtPrice(rec.entry_price)}</span>
                  <span>손절 {fmtPrice(rec.stop_loss)}</span>
                  <span>익절 {fmtPrice(rec.take_profit)}</span>
                  {rec.risk_reward != null && <span>R:R {rec.risk_reward.toFixed(1)}</span>}
                </div>
                {rec.reasoning && <p className="text-xs text-gray-500 mt-1">{rec.reasoning}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {recommendations.length === 0 && (sectorRecs.concepts || []).length === 0 && (
        <div className="text-center py-4 text-gray-400 text-sm">
          추천 데이터가 없습니다.
        </div>
      )}
    </div>
  )
}
