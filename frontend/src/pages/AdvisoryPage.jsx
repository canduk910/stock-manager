/**
 * AI자문 페이지
 * 왼쪽: 종목 목록 + 추가폼
 * 오른쪽: 탭 (기본적분석 | 기술적분석 | AI자문)
 */
import { useState, useEffect } from 'react'
import FundamentalPanel from '../components/advisory/FundamentalPanel'
import TechnicalPanel from '../components/advisory/TechnicalPanel'
import AIReportPanel from '../components/advisory/AIReportPanel'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorAlert from '../components/common/ErrorAlert'
import { useAdvisoryStocks, useAdvisoryData, useAdvisoryReport } from '../hooks/useAdvisory'

const TABS = [
  { key: 'fundamental', label: '기본적 분석' },
  { key: 'technical',   label: '기술적 분석' },
  { key: 'ai',          label: 'AI 자문' },
]

const MARKET_OPTIONS = [
  { value: 'KR', label: '국내 KRX' },
  { value: 'US', label: '미국 NYSE·NASDAQ' },
]

// ── 종목 추가 폼 ─────────────────────────────────────────────────────────
function AddForm({ onAdd }) {
  const [code, setCode] = useState('')
  const [market, setMarket] = useState('KR')
  const [memo, setMemo] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [err, setErr] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!code.trim()) return
    setSubmitting(true)
    setErr(null)
    try {
      await onAdd(code.trim(), market, memo.trim())
      setCode('')
      setMemo('')
    } catch (e) {
      setErr(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2 p-3 border border-gray-200 rounded-lg bg-gray-50">
      <p className="text-xs font-semibold text-gray-600">종목 추가</p>
      <select
        value={market}
        onChange={e => setMarket(e.target.value)}
        className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm bg-white"
      >
        {MARKET_OPTIONS.map(o => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
      <input
        value={code}
        onChange={e => setCode(e.target.value)}
        placeholder={market === 'KR' ? '종목코드 (예: 005930)' : '티커 (예: AAPL)'}
        className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
      />
      <input
        value={memo}
        onChange={e => setMemo(e.target.value)}
        placeholder="메모 (선택)"
        className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
      />
      {err && <p className="text-xs text-red-600">{err}</p>}
      <button
        type="submit"
        disabled={submitting || !code.trim()}
        className="w-full py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        {submitting ? '추가 중...' : '추가'}
      </button>
    </form>
  )
}

// ── 종목 목록 아이템 ──────────────────────────────────────────────────────
function StockItem({ stock, selected, onClick, onRemove }) {
  return (
    <div
      className={`flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer transition-colors ${
        selected ? 'bg-blue-600 text-white' : 'bg-white hover:bg-gray-50 border border-gray-200'
      }`}
      onClick={onClick}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-1.5">
          <span className={`text-sm font-medium truncate ${selected ? 'text-white' : 'text-gray-800'}`}>
            {stock.name}
          </span>
          <span className={`text-xs px-1 rounded ${
            selected ? 'bg-blue-500 text-blue-100' : 'bg-gray-100 text-gray-500'
          }`}>
            {stock.market}
          </span>
        </div>
        <div className={`text-xs mt-0.5 ${selected ? 'text-blue-200' : 'text-gray-400'}`}>
          {stock.code}
          {stock.updated_at && (
            <span className="ml-1.5">· {stock.updated_at.slice(0, 16).replace('T', ' ')}</span>
          )}
        </div>
      </div>
      <button
        onClick={e => { e.stopPropagation(); onRemove() }}
        className={`ml-2 text-xs px-1.5 py-0.5 rounded transition-colors ${
          selected ? 'text-blue-200 hover:text-white hover:bg-blue-500' : 'text-gray-400 hover:text-red-500'
        }`}
      >
        ✕
      </button>
    </div>
  )
}

// ── 메인 페이지 ───────────────────────────────────────────────────────────
export default function AdvisoryPage({ notify }) {
  const { stocks, loading: stocksLoading, load: loadStocks, add, remove } = useAdvisoryStocks()
  const { data, loading: dataLoading, error: dataError, load: loadData, refresh } = useAdvisoryData()
  const { report, loading: reportLoading, error: reportError, load: loadReport, generate } = useAdvisoryReport()

  const [selected, setSelected] = useState(null) // {code, market, name}
  const [activeTab, setActiveTab] = useState('fundamental')
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    loadStocks()
  }, [loadStocks])

  // 종목 선택 시 데이터 + 리포트 로드
  const handleSelect = (stock) => {
    setSelected(stock)
    loadData(stock.code, stock.market)
    loadReport(stock.code, stock.market)
  }

  const handleRemove = async (stock) => {
    if (!confirm(`${stock.name}(${stock.code})을 자문 종목에서 삭제하시겠습니까?`)) return
    try {
      await remove(stock.code, stock.market)
      if (selected?.code === stock.code && selected?.market === stock.market) {
        setSelected(null)
      }
      notify?.('종목이 삭제되었습니다.', 'success')
    } catch (e) {
      notify?.(e.message, 'error')
    }
  }

  const handleAdd = async (code, market, memo) => {
    await add(code, market, memo)
    notify?.('종목이 추가되었습니다.', 'success')
  }

  const handleRefresh = async () => {
    if (!selected) return
    setRefreshing(true)
    try {
      await refresh(selected.code, selected.market)
      // 목록 updated_at 갱신
      loadStocks()
      notify?.('데이터 새로고침 완료', 'success')
    } catch (e) {
      notify?.(e.message, 'error')
    } finally {
      setRefreshing(false)
    }
  }

  const handleGenerate = async () => {
    if (!selected) return
    try {
      await generate(selected.code, selected.market)
      notify?.('AI 리포트가 생성되었습니다.', 'success')
    } catch (e) {
      notify?.(e.message, 'error')
    }
  }

  return (
    <div className="flex gap-4 min-h-screen" style={{ minHeight: 'calc(100vh - 120px)' }}>
      {/* ── 왼쪽: 종목 목록 ── */}
      <aside className="w-56 shrink-0 flex flex-col gap-3">
        <h2 className="text-base font-bold text-gray-800">AI 자문</h2>
        <AddForm onAdd={handleAdd} />

        <div className="flex flex-col gap-1.5">
          {stocksLoading && <p className="text-xs text-gray-400 text-center py-2">로딩 중...</p>}
          {!stocksLoading && stocks.length === 0 && (
            <p className="text-xs text-gray-400 text-center py-4">등록된 종목 없음</p>
          )}
          {stocks.map(s => (
            <StockItem
              key={`${s.code}-${s.market}`}
              stock={s}
              selected={selected?.code === s.code && selected?.market === s.market}
              onClick={() => handleSelect(s)}
              onRemove={() => handleRemove(s)}
            />
          ))}
        </div>
      </aside>

      {/* ── 오른쪽: 탭 콘텐츠 ── */}
      <div className="flex-1 min-w-0">
        {!selected ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-400">
            <p className="text-3xl mb-3">📋</p>
            <p className="text-sm">왼쪽에서 종목을 선택하거나 추가하세요.</p>
          </div>
        ) : (
          <>
            {/* 헤더 */}
            <div className="flex items-center justify-between mb-3">
              <div>
                <span className="text-base font-bold text-gray-800">{selected.name}</span>
                <span className="ml-2 text-sm text-gray-500">{selected.code}</span>
                <span className="ml-1.5 text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">{selected.market}</span>
              </div>
              <button
                onClick={handleRefresh}
                disabled={refreshing || dataLoading}
                className="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 transition-colors"
              >
                {refreshing || dataLoading ? '수집 중...' : '새로고침'}
              </button>
            </div>

            {/* 탭 */}
            <div className="flex border-b border-gray-200 mb-4">
              {TABS.map(t => (
                <button
                  key={t.key}
                  onClick={() => setActiveTab(t.key)}
                  className={`px-4 py-2 text-sm font-medium transition-colors ${
                    activeTab === t.key
                      ? 'border-b-2 border-blue-600 text-blue-600'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* 탭 콘텐츠 */}
            {dataLoading && !refreshing ? (
              <div className="flex justify-center py-12">
                <LoadingSpinner />
              </div>
            ) : dataError ? (
              <div className="space-y-2">
                <ErrorAlert message={dataError} />
                <p className="text-xs text-gray-400">새로고침 버튼으로 데이터를 수집해주세요.</p>
              </div>
            ) : (
              <>
                {activeTab === 'fundamental' && (
                  <FundamentalPanel data={data} market={selected.market} />
                )}
                {activeTab === 'technical' && (
                  <TechnicalPanel data={data} />
                )}
                {activeTab === 'ai' && (
                  <AIReportPanel
                    report={report}
                    loading={reportLoading}
                    error={reportError}
                    onGenerate={handleGenerate}
                  />
                )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  )
}
