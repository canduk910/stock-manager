import { useState, useEffect } from 'react'
import { useEarnings } from '../hooks/useEarnings'
import FilingsTable from '../components/earnings/FilingsTable'
import LoadingSpinner from '../components/common/LoadingSpinner'
import ErrorAlert from '../components/common/ErrorAlert'
import EmptyState from '../components/common/EmptyState'

// DART pblntf_ty 카테고리 — ValueScreener 자문(2026-05-10) 기반
// Default ON 4종 (가치투자 안전마진 평가 필수): A 정기 + B 주요사항 + D 지분 + F 외부감사
const CATEGORY_OPTIONS = [
  { code: 'A', label: '정기공시', defaultOn: true,  hint: '사업/반기/분기' },
  { code: 'B', label: '주요사항보고', defaultOn: true, hint: '유증·CB·자사주·합병·감자' },
  { code: 'D', label: '지분공시', defaultOn: true, hint: '5%룰·임원·주요주주' },
  { code: 'F', label: '외부감사관련', defaultOn: true, hint: '감사의견 — Value Trap 신호' },
  { code: 'C', label: '발행공시', defaultOn: false, hint: '증권신고서' },
  { code: 'E', label: '기타공시', defaultOn: false, hint: '정관변경·분할' },
  { code: 'I', label: '거래소공시', defaultOn: false, hint: '단일판매·공급계약·배당' },
]
const DEFAULT_ON = CATEGORY_OPTIONS.filter(c => c.defaultOn).map(c => c.code)

function localDateStr(d = new Date()) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function todayStr() {
  return localDateStr()
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
  const [categories, setCategories] = useState(DEFAULT_ON)
  const { data, loading, error, load } = useEarnings()

  useEffect(() => {
    const today = todayStr().replace(/-/g, '')
    load(today, today, 'KR', DEFAULT_ON)
  }, []) // 첫 마운트 시 오늘 날짜 + default ON 카테고리로 조회

  const handleSearch = () => {
    setFilterText('')
    const cats = market === 'KR' ? categories : null  // US는 카테고리 무시
    load(startDate.replace(/-/g, ''), endDate.replace(/-/g, ''), market, cats)
  }

  const toggleCategory = (code) => {
    setCategories(prev => prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code])
  }
  const restoreDefaults = () => setCategories(DEFAULT_ON)

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
                  setStartDate(localDateStr(start))
                  setEndDate(localDateStr(end))
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

        {/* KR 한정: 카테고리 다중 체크박스 (Phase 2A, ValueScreener 자문) */}
        {market === 'KR' && (
          <div className="border-t border-gray-100 pt-3 space-y-2">
            <div className="flex items-center gap-3">
              <span className="text-xs font-medium text-gray-500">공시 카테고리</span>
              <button
                onClick={restoreDefaults}
                className="text-xs text-gray-400 hover:text-blue-600"
              >
                기본값 복원 (A·B·D·F)
              </button>
              <span className="ml-auto text-xs text-gray-400">
                선택 {categories.length} / {CATEGORY_OPTIONS.length}
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {CATEGORY_OPTIONS.map(({ code, label, hint, defaultOn }) => {
                const active = categories.includes(code)
                return (
                  <label
                    key={code}
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs cursor-pointer border transition-colors ${
                      active
                        ? 'bg-blue-50 border-blue-300 text-blue-700'
                        : 'bg-white border-gray-200 text-gray-500 hover:border-gray-300'
                    }`}
                    title={hint}
                  >
                    <input
                      type="checkbox"
                      checked={active}
                      onChange={() => toggleCategory(code)}
                      className="w-3.5 h-3.5 accent-blue-600"
                    />
                    <span className="font-medium">{label}</span>
                    {defaultOn && <span className="text-[10px] text-blue-500">★</span>}
                  </label>
                )
              })}
            </div>
            <p className="text-[11px] text-gray-400">
              ★ ValueScreener 권고: 정기공시·주요사항·지분·외부감사는 안전마진 평가에 필수.
              발행/기타/거래소 공시는 의도 시 추가 선택.
            </p>
          </div>
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
