import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useBalance } from '../hooks/useBalance'
import { listAccounts } from '../api/me'
import PortfolioSummary from '../components/balance/PortfolioSummary'
import HoldingsTable from '../components/balance/HoldingsTable'
import OverseasHoldingsTable from '../components/balance/OverseasHoldingsTable'
import FuturesTable from '../components/balance/FuturesTable'
import LoadingSpinner from '../components/common/LoadingSpinner'
import EmptyState from '../components/common/EmptyState'

/**
 * R9 (KIS 멀티 계좌): 상단 탭 [전체|라벨1|라벨2|...].
 * - 전체 클릭 → 모든 계좌 합산 (account_label=null).
 * - 라벨 클릭 → 단독 조회.
 * 합산 모드에서 종목 row 에 보유 계좌 메타("accounts": ['주식','연금'])가 표시됨.
 * partial_failure 메타는 상단 노란 경고 배너로 노출.
 *
 * 탭 목록은 GET /api/me/kis 로 별도 fetch (마운트 시 1회) — 단독 모드 응답은
 * accounts 메타에 해당 계좌 1개만 들어있어 탭이 사라지는 문제 방지.
 */
const ALL_TAB = '__ALL__'

export default function BalancePage({ notify }) {
  const { data, loading, error, load } = useBalance()
  const [activeTab, setActiveTab] = useState(ALL_TAB)
  const [accountTabs, setAccountTabs] = useState([])

  useEffect(() => {
    listAccounts()
      .then((res) => setAccountTabs((res.accounts || []).map((a) => a.label)))
      .catch(() => setAccountTabs([]))
  }, [])

  useEffect(() => {
    load(activeTab === ALL_TAB ? null : activeTab)
  }, [activeTab, load])

  const isKeyMissing = error && (error.includes('설정되지 않았습니다') || error.includes('503'))

  const aggregateSummary = useMemo(() => {
    if (activeTab !== ALL_TAB) return null
    if (accountTabs.length === 0) return null
    return `${accountTabs.length}계좌 합산 (${accountTabs.join(', ')})`
  }, [accountTabs, activeTab])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">잔고 조회</h1>
        <button
          onClick={() => load(activeTab === ALL_TAB ? null : activeTab)}
          disabled={loading}
          className="px-4 py-1.5 bg-gray-800 hover:bg-gray-900 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
        >
          새로고침
        </button>
      </div>

      {/* 탭 — 계좌 0개면 미렌더 */}
      {accountTabs.length > 0 && (
        <div className="flex flex-wrap gap-1 border-b border-gray-200">
          <TabButton
            label="전체"
            active={activeTab === ALL_TAB}
            onClick={() => setActiveTab(ALL_TAB)}
          />
          {accountTabs.map((lbl) => (
            <TabButton
              key={lbl}
              label={lbl}
              active={activeTab === lbl}
              onClick={() => setActiveTab(lbl)}
            />
          ))}
        </div>
      )}

      {loading && <LoadingSpinner />}

      {aggregateSummary && (
        <div className="text-xs text-gray-500">{aggregateSummary}</div>
      )}

      {data?.partial_failure && data.partial_failure.length > 0 && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
          <p className="font-semibold mb-1">일부 계좌 조회 실패 — 나머지는 정상 표시:</p>
          <ul className="list-disc list-inside space-y-0.5">
            {data.partial_failure.map((msg, i) => <li key={i}>{msg}</li>)}
          </ul>
        </div>
      )}

      {error && (
        isKeyMissing ? (
          <div className="rounded-xl border border-amber-300 bg-amber-50 p-5 text-sm text-amber-800 space-y-1">
            <p className="font-semibold">KIS API 키가 설정되지 않았습니다</p>
            <p>{error}</p>
            <p className="text-xs text-amber-600 mt-2">
              <Link to="/settings/kis" className="underline">/settings/kis</Link> 에서 KIS 자격증명을 등록하세요.
            </p>
          </div>
        ) : (
          <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-700">
            <span className="font-semibold">오류: </span>{error}
          </div>
        )
      )}

      {data && !loading && (
        <div className="space-y-8">
          <PortfolioSummary data={data} />

          {/* 국내주식 */}
          <div>
            <h2 className="text-lg font-semibold text-gray-800 mb-3">국내주식</h2>
            {(!data.stock_list || data.stock_list.length === 0) ? (
              <EmptyState message="보유 중인 국내주식이 없습니다." />
            ) : (
              <HoldingsTable stocks={data.stock_list} />
            )}
          </div>

          {/* 해외주식 */}
          {data.overseas_list && data.overseas_list.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-gray-800 mb-3">해외주식</h2>
              <OverseasHoldingsTable stocks={data.overseas_list} />
            </div>
          )}

          {/* 국내선물옵션 */}
          {data.fno_enabled && (
            <div>
              <h2 className="text-lg font-semibold text-gray-800 mb-3">국내선물옵션</h2>
              {data.futures_list && data.futures_list.length > 0 ? (
                <FuturesTable positions={data.futures_list} />
              ) : (
                <EmptyState message="보유 중인 선물옵션이 없습니다." />
              )}
            </div>
          )}

          {/* 포트폴리오 분석 링크 */}
          <div className="text-center py-3">
            <Link to="/portfolio" className="text-sm text-indigo-500 hover:text-indigo-700 font-medium">
              포트폴리오에서 AI 자문 보기 →
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}

function TabButton({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
        active
          ? 'border-blue-600 text-blue-700'
          : 'border-transparent text-gray-600 hover:text-gray-800'
      }`}
    >
      {label}
    </button>
  )
}
