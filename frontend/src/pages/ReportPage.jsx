import { useEffect, useState } from 'react'
import { useReports, useReportDetail, useRecommendations, usePerformance, useRegimes } from '../hooks/useReport'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorAlert from '../components/common/ErrorAlert'
import EmptyState from '../components/common/EmptyState'

const TABS = [
  { key: 'reports', label: '일일 보고서' },
  { key: 'recommendations', label: '추천 이력' },
  { key: 'performance', label: '성과 통계' },
]

const MARKET_FILTERS = [
  { key: '', label: '전체' },
  { key: 'KR', label: '한국' },
  { key: 'US', label: '미국' },
]

const STATUS_FILTERS = [
  { key: '', label: '전체' },
  { key: 'recommended', label: '추천' },
  { key: 'approved', label: '승인' },
  { key: 'ordered', label: '주문' },
  { key: 'closed', label: '종료' },
]

const REGIME_COLORS = {
  accumulation: 'bg-green-100 text-green-800',
  selective: 'bg-yellow-100 text-yellow-800',
  cautious: 'bg-orange-100 text-orange-800',
  defensive: 'bg-red-100 text-red-800',
}

const GRADE_COLORS = {
  A: 'bg-green-100 text-green-800',
  'B+': 'bg-blue-100 text-blue-800',
  B: 'bg-yellow-100 text-yellow-800',
  C: 'bg-orange-100 text-orange-800',
  D: 'bg-red-100 text-red-800',
}

function RegimeBadge({ regime }) {
  if (!regime) return null
  const cls = REGIME_COLORS[regime] || 'bg-gray-100 text-gray-800'
  return <span className={`px-2 py-0.5 rounded text-xs font-medium ${cls}`}>{regime}</span>
}

function GradeBadge({ grade }) {
  if (!grade) return <span className="text-gray-400">-</span>
  const cls = GRADE_COLORS[grade] || 'bg-gray-100 text-gray-800'
  return <span className={`px-2 py-0.5 rounded text-xs font-bold ${cls}`}>{grade}</span>
}

function PnlCell({ value }) {
  if (value == null) return <span className="text-gray-400">-</span>
  const cls = value > 0 ? 'text-red-600' : value < 0 ? 'text-blue-600' : 'text-gray-600'
  return <span className={`font-medium ${cls}`}>{value > 0 ? '+' : ''}{value.toFixed(2)}%</span>
}

// ── 일일 보고서 탭 ──────────────────────────────────────────

function ReportsTab() {
  const reports = useReports()
  const detail = useReportDetail()
  const [market, setMarket] = useState('')
  const [selectedId, setSelectedId] = useState(null)

  useEffect(() => { reports.load(market || undefined) }, [market])

  const handleView = (id) => {
    setSelectedId(id)
    detail.load(id)
  }

  if (reports.loading) return <LoadingSpinner />
  if (reports.error) return <ErrorAlert message={reports.error} />

  const items = reports.data?.items || []

  return (
    <div className="space-y-4">
      {/* 필터 */}
      <div className="flex gap-2">
        {MARKET_FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setMarket(f.key)}
            className={`px-3 py-1 text-sm rounded ${market === f.key ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {items.length === 0 ? (
        <EmptyState message="보고서가 없습니다. AI 분석을 실행하면 자동으로 생성됩니다." />
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="px-4 py-3 text-left">날짜</th>
                <th className="px-4 py-3 text-left">시장</th>
                <th className="px-4 py-3 text-left">체제</th>
                <th className="px-4 py-3 text-right">후보</th>
                <th className="px-4 py-3 text-right">추천</th>
                <th className="px-4 py-3 text-center">Telegram</th>
                <th className="px-4 py-3 text-center">상세</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono">{r.date}</td>
                  <td className="px-4 py-2">{r.market}</td>
                  <td className="px-4 py-2"><RegimeBadge regime={r.regime} /></td>
                  <td className="px-4 py-2 text-right">{r.candidates_count}</td>
                  <td className="px-4 py-2 text-right font-medium">{r.recommended_count}</td>
                  <td className="px-4 py-2 text-center">{r.telegram_sent ? '  O' : '-'}</td>
                  <td className="px-4 py-2 text-center">
                    <button
                      onClick={() => handleView(r.id)}
                      className="text-blue-600 hover:underline text-xs"
                    >
                      보기
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 보고서 상세 모달 */}
      {selectedId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setSelectedId(null)}>
          <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full mx-4 max-h-[80vh] overflow-y-auto p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold">보고서 상세</h3>
              <button onClick={() => setSelectedId(null)} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
            </div>
            {detail.loading ? (
              <LoadingSpinner />
            ) : detail.error ? (
              <ErrorAlert message={detail.error} />
            ) : detail.data ? (
              <div className="prose prose-sm max-w-none">
                <pre className="whitespace-pre-wrap text-sm bg-gray-50 p-4 rounded-lg">{detail.data.report_markdown}</pre>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  )
}

// ── 추천 이력 탭 ────────────────────────────────────────────

function RecommendationsTab() {
  const recs = useRecommendations()
  const [market, setMarket] = useState('')
  const [status, setStatus] = useState('')

  useEffect(() => {
    recs.load(market || undefined, status || undefined)
  }, [market, status])

  if (recs.loading) return <LoadingSpinner />
  if (recs.error) return <ErrorAlert message={recs.error} />

  const items = recs.data?.items || []

  return (
    <div className="space-y-4">
      <div className="flex gap-4 flex-wrap">
        <div className="flex gap-2">
          {MARKET_FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setMarket(f.key)}
              className={`px-3 py-1 text-sm rounded ${market === f.key ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setStatus(f.key)}
              className={`px-3 py-1 text-sm rounded ${status === f.key ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {items.length === 0 ? (
        <EmptyState message="추천 이력이 없습니다." />
      ) : (
        <div className="bg-white rounded-lg shadow overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="px-3 py-3 text-left">날짜</th>
                <th className="px-3 py-3 text-left">시장</th>
                <th className="px-3 py-3 text-left">종목</th>
                <th className="px-3 py-3 text-center">등급</th>
                <th className="px-3 py-3 text-right">진입가</th>
                <th className="px-3 py-3 text-right">수량</th>
                <th className="px-3 py-3 text-right">할인율</th>
                <th className="px-3 py-3 text-right">R:R</th>
                <th className="px-3 py-3 text-center">상태</th>
                <th className="px-3 py-3 text-right">실현손익</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-mono text-xs">{(r.created_at || '').slice(0, 10)}</td>
                  <td className="px-3 py-2">{r.market}</td>
                  <td className="px-3 py-2 font-medium">{r.name} <span className="text-gray-400 text-xs">({r.code})</span></td>
                  <td className="px-3 py-2 text-center"><GradeBadge grade={r.safety_grade} /></td>
                  <td className="px-3 py-2 text-right font-mono">{r.entry_price?.toLocaleString()}</td>
                  <td className="px-3 py-2 text-right">{r.recommended_qty}</td>
                  <td className="px-3 py-2 text-right">{r.discount_rate != null ? `${r.discount_rate.toFixed(0)}%` : '-'}</td>
                  <td className="px-3 py-2 text-right">{r.risk_reward != null ? r.risk_reward.toFixed(1) : '-'}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      r.status === 'closed' ? 'bg-gray-200' :
                      r.status === 'ordered' ? 'bg-blue-100 text-blue-800' :
                      r.status === 'approved' ? 'bg-green-100 text-green-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right"><PnlCell value={r.realized_pnl_pct} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ── 성과 통계 탭 ────────────────────────────────────────────

function PerformanceTab() {
  const perf = usePerformance()
  const regimes = useRegimes()
  const [market, setMarket] = useState('')

  useEffect(() => {
    perf.load(market || undefined)
    regimes.load()
  }, [market])

  return (
    <div className="space-y-6">
      <div className="flex gap-2">
        {MARKET_FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setMarket(f.key)}
            className={`px-3 py-1 text-sm rounded ${market === f.key ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* 성과 요약 카드 */}
      {perf.loading ? <LoadingSpinner /> : perf.error ? <ErrorAlert message={perf.error} /> : perf.data ? (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatCard label="총 종료" value={perf.data.total} />
          <StatCard label="승리" value={perf.data.wins} color="text-red-600" />
          <StatCard label="패배" value={perf.data.losses} color="text-blue-600" />
          <StatCard label="승률" value={`${perf.data.win_rate}%`} color={perf.data.win_rate >= 50 ? 'text-red-600' : 'text-blue-600'} />
          <StatCard label="평균 손익" value={`${perf.data.avg_pnl > 0 ? '+' : ''}${perf.data.avg_pnl}%`} color={perf.data.avg_pnl > 0 ? 'text-red-600' : 'text-blue-600'} />
        </div>
      ) : (
        <EmptyState message="종료된 추천이 없어 성과를 계산할 수 없습니다." />
      )}

      {/* 체제 이력 */}
      <div>
        <h3 className="text-lg font-bold text-gray-900 mb-3">매크로 체제 이력</h3>
        {regimes.loading ? <LoadingSpinner /> : regimes.error ? <ErrorAlert message={regimes.error} /> : (
          <div className="bg-white rounded-lg shadow overflow-x-auto">
            {regimes.data?.length === 0 ? (
              <EmptyState message="체제 이력이 없습니다." />
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-600">
                  <tr>
                    <th className="px-4 py-3 text-left">날짜</th>
                    <th className="px-4 py-3 text-left">체제</th>
                    <th className="px-4 py-3 text-right">VIX</th>
                    <th className="px-4 py-3 text-right">버핏지수</th>
                    <th className="px-4 py-3 text-right">공포탐욕</th>
                    <th className="px-4 py-3 text-right">KOSPI</th>
                    <th className="px-4 py-3 text-right">S&P 500</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {(regimes.data || []).slice(0, 30).map((r) => (
                    <tr key={r.id} className="hover:bg-gray-50">
                      <td className="px-4 py-2 font-mono">{r.date}</td>
                      <td className="px-4 py-2"><RegimeBadge regime={r.regime} /></td>
                      <td className="px-4 py-2 text-right">{r.vix?.toFixed(1) ?? '-'}</td>
                      <td className="px-4 py-2 text-right">{r.buffett_ratio?.toFixed(2) ?? '-'}</td>
                      <td className="px-4 py-2 text-right">{r.fear_greed_score?.toFixed(0) ?? '-'}</td>
                      <td className="px-4 py-2 text-right">{r.kospi?.toLocaleString() ?? '-'}</td>
                      <td className="px-4 py-2 text-right">{r.sp500?.toLocaleString() ?? '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, color = 'text-gray-900' }) {
  return (
    <div className="bg-white rounded-lg shadow p-4 text-center">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
    </div>
  )
}

// ── 메인 페이지 ─────────────────────────────────────────────

export default function ReportPage() {
  const [tab, setTab] = useState('reports')

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">투자 보고서</h1>

      {/* 탭 네비게이션 */}
      <div className="flex gap-1 border-b border-gray-200">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* 탭 콘텐츠 */}
      {tab === 'reports' && <ReportsTab />}
      {tab === 'recommendations' && <RecommendationsTab />}
      {tab === 'performance' && <PerformanceTab />}
    </div>
  )
}
