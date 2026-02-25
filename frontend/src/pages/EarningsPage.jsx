import { useState, useEffect } from 'react'
import { useEarnings } from '../hooks/useEarnings'
import FilingsTable from '../components/earnings/FilingsTable'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorAlert from '../components/common/ErrorAlert'
import EmptyState from '../components/common/EmptyState'

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

function fmtDate8(s) {
  if (!s || s.length !== 8) return s || ''
  return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`
}

export default function EarningsPage() {
  const [startDate, setStartDate] = useState(todayStr())
  const [endDate, setEndDate] = useState(todayStr())
  const [filterText, setFilterText] = useState('')
  const [market, setMarket] = useState('KR')
  const { data, loading, error, load } = useEarnings()

  useEffect(() => {
    const today = todayStr().replace(/-/g, '')
    load(today, today, 'KR')
  }, []) // 첫 마운트 시 오늘 날짜로 조회

  const handleSearch = () => {
    setFilterText('')
    load(startDate.replace(/-/g, ''), endDate.replace(/-/g, ''), market)
  }

  const filteredFilings = () => {
    if (!data?.filings) return []
    const q = filterText.trim().toLowerCase()
    if (!q) return data.filings
    return data.filings.filter(
      (f) =>
        f.corp_name?.toLowerCase().includes(q) ||
        f.stock_code?.toLowerCase().includes(q)
    )
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSearch()
  }

  // 날짜 범위 표시 텍스트
  const dateRangeText = () => {
    if (!data) return ''
    const s = fmtDate8(data.start_date)
    const e = fmtDate8(data.end_date)
    return s === e ? s : `${s} ~ ${e}`
  }

  const marketLabel = data?.market === 'US' ? '미국 SEC' : '국내 DART'

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">공시 조회</h1>

      {/* 검색 패널 */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
        {/* 시장 선택 탭 */}
        <div className="flex gap-1">
          {[
            { value: 'KR', label: '국내 (DART)' },
            { value: 'US', label: '미국 (SEC EDGAR)' },
          ].map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setMarket(value)}
              className={`px-4 py-1.5 text-sm rounded-lg font-medium transition-colors ${
                market === value
                  ? 'bg-blue-600 text-white'
                  : 'border border-gray-300 text-gray-600 hover:bg-gray-50'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-gray-500">시작 날짜</span>
            <input
              type="date"
              value={startDate}
              max={endDate}
              onChange={(e) => setStartDate(e.target.value)}
              onKeyDown={handleKeyDown}
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </label>
          <span className="text-gray-400 mb-1.5">~</span>
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-gray-500">종료 날짜</span>
            <input
              type="date"
              value={endDate}
              min={startDate}
              onChange={(e) => setEndDate(e.target.value)}
              onKeyDown={handleKeyDown}
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
          </label>
          {/* 단축 버튼 */}
          <div className="flex gap-1 mb-0.5">
            {[
              { label: '오늘', days: 0 },
              { label: '1주', days: 6 },
              { label: '1개월', days: 29 },
            ].map(({ label, days }) => (
              <button
                key={label}
                onClick={() => {
                  const end = new Date()
                  const start = new Date()
                  start.setDate(start.getDate() - days)
                  setStartDate(start.toISOString().slice(0, 10))
                  setEndDate(end.toISOString().slice(0, 10))
                }}
                className="px-2.5 py-1 text-xs border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-600 whitespace-nowrap"
              >
                {label}
              </button>
            ))}
          </div>
          <button
            onClick={handleSearch}
            disabled={loading}
            className="px-5 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold rounded-lg text-sm transition-colors mb-0.5"
          >
            {loading ? '조회 중...' : '조회'}
          </button>
        </div>

        {market === 'US' && (
          <p className="text-xs text-gray-400">
            미국 SEC EDGAR에서 10-K (연간보고서) 및 10-Q (분기보고서)를 조회합니다.
          </p>
        )}
      </div>

      {loading && <LoadingSpinner />}
      <ErrorAlert message={error} />

      {data && !loading && (
        <>
          {/* 필터 바 */}
          <div className="flex items-center gap-3">
            <input
              type="text"
              placeholder="종목명 또는 종목코드 검색"
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
            {filterText && (
              <button
                onClick={() => setFilterText('')}
                className="text-xs text-gray-400 hover:text-gray-600"
              >
                초기화
              </button>
            )}
            <p className="text-sm text-gray-500 ml-auto">
              {filterText
                ? <><span className="font-semibold text-gray-800">{filteredFilings().length}</span> / {data.total}건</>
                : <><span className="font-semibold text-gray-800">{data.total}건</span>의 정기보고서 제출</>
              }
              {dateRangeText() && ` (${dateRangeText()})`}
              <span className="ml-2 text-gray-400 text-xs">· {marketLabel}</span>
            </p>
          </div>

          {filteredFilings().length === 0 ? (
            <EmptyState message={filterText ? `'${filterText}'에 해당하는 종목이 없습니다.` : '해당 기간에 제출된 정기보고서가 없습니다.'} />
          ) : (
            <FilingsTable filings={filteredFilings()} market={data?.market || 'KR'} />
          )}
        </>
      )}
    </div>
  )
}
