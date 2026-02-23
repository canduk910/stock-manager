import { useState } from 'react'

const DEFAULT_FILTERS = {
  date: '',
  market: '',
  sort_by: 'mktcap',
  sort_order: 'desc',
  top: 50,
  per_min: '',
  per_max: '',
  pbr_max: '',
  roe_min: '',
  include_negative: false,
  earnings_only: false,
}

const SORT_FIELDS = [
  { value: 'mktcap', label: '시가총액' },
  { value: 'per', label: 'PER' },
  { value: 'pbr', label: 'PBR' },
  { value: 'roe', label: 'ROE' },
]

export default function FilterPanel({ onSearch, loading }) {
  const [filters, setFilters] = useState(DEFAULT_FILTERS)

  const set = (key, value) => setFilters((prev) => ({ ...prev, [key]: value }))

  const handleSubmit = (e) => {
    e.preventDefault()
    const params = {}
    if (filters.date) params.date = filters.date
    if (filters.market) params.market = filters.market
    // 정렬: "mktcap desc" 형태로 조합
    params.sort_by = `${filters.sort_by} ${filters.sort_order}`
    if (filters.top) params.top = Number(filters.top)
    if (filters.per_min !== '') params.per_min = Number(filters.per_min)
    if (filters.per_max !== '') params.per_max = Number(filters.per_max)
    if (filters.pbr_max !== '') params.pbr_max = Number(filters.pbr_max)
    if (filters.roe_min !== '') params.roe_min = Number(filters.roe_min)
    if (filters.include_negative) params.include_negative = true
    if (filters.earnings_only) params.earnings_only = true
    onSearch(params)
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
      <h2 className="font-semibold text-gray-800">필터 설정</h2>

      {/* 날짜 & 시장 */}
      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-500">날짜</span>
          <input
            type="date"
            value={filters.date}
            onChange={(e) => set('date', e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-500">시장</span>
          <select
            value={filters.market}
            onChange={(e) => set('market', e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            <option value="">전체</option>
            <option value="KOSPI">KOSPI</option>
            <option value="KOSDAQ">KOSDAQ</option>
          </select>
        </label>
      </div>

      {/* PER 범위 */}
      <div className="flex flex-col gap-1">
        <span className="text-xs font-medium text-gray-500">PER 범위</span>
        <div className="flex items-center gap-2">
          <input
            type="number"
            placeholder="최소"
            value={filters.per_min}
            onChange={(e) => set('per_min', e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-full focus:outline-none focus:ring-2 focus:ring-blue-400"
            step="0.1"
          />
          <span className="text-gray-400 text-sm">~</span>
          <input
            type="number"
            placeholder="최대"
            value={filters.per_max}
            onChange={(e) => set('per_max', e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-full focus:outline-none focus:ring-2 focus:ring-blue-400"
            step="0.1"
          />
        </div>
      </div>

      {/* PBR 최대 & ROE 최소 */}
      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-500">PBR 최대</span>
          <input
            type="number"
            placeholder="예: 1.5"
            value={filters.pbr_max}
            onChange={(e) => set('pbr_max', e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            step="0.1"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-500">ROE 최소 (%)</span>
          <input
            type="number"
            placeholder="예: 10"
            value={filters.roe_min}
            onChange={(e) => set('roe_min', e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            step="0.1"
          />
        </label>
      </div>

      {/* 정렬 기준 */}
      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-500">정렬 기준</span>
          <select
            value={filters.sort_by}
            onChange={(e) => set('sort_by', e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            {SORT_FIELDS.map((f) => (
              <option key={f.value} value={f.value}>{f.label}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-500">정렬 방향</span>
          <select
            value={filters.sort_order}
            onChange={(e) => set('sort_order', e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            <option value="asc">오름차순 (asc)</option>
            <option value="desc">내림차순 (desc)</option>
          </select>
        </label>
      </div>

      {/* 상위 N개 */}
      <label className="flex flex-col gap-1">
        <span className="text-xs font-medium text-gray-500">상위 N개</span>
        <input
          type="number"
          value={filters.top}
          onChange={(e) => set('top', e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          min="1"
          max="500"
        />
      </label>

      {/* 체크박스 옵션 */}
      <div className="flex flex-col gap-2">
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.include_negative}
            onChange={(e) => set('include_negative', e.target.checked)}
            className="rounded"
          />
          적자기업(PER 음수) 포함
        </label>
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.earnings_only}
            onChange={(e) => set('earnings_only', e.target.checked)}
            className="rounded"
          />
          당일 실적발표 종목만
        </label>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold rounded-lg text-sm transition-colors"
      >
        {loading ? '조회 중...' : '조회하기'}
      </button>
    </form>
  )
}
