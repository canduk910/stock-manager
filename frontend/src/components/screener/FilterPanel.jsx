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
  drop_from_high: '',
  include_negative: false,
  earnings_only: false,
  preset: '',
  regime_aware: true,
  guru_top: 30,
}

const PRESETS = [
  { value: '', label: '기본 스크리닝', desc: null },
  { value: 'greenblatt', label: 'Greenblatt Magic Formula',
    desc: 'ROIC + Earnings Yield 합산 순위', dart: true },
  { value: 'neff', label: 'Neff Total Return',
    desc: '(EPS CAGR + 배당) / PER', dart: true },
  { value: 'seo', label: '서준식 기대수익률',
    desc: 'ROE / PBR (빠른 조회)', dart: false },
]

const SORT_FIELDS = [
  { value: 'mktcap', label: '시가총액' },
  { value: 'per', label: 'PER' },
  { value: 'pbr', label: 'PBR' },
  { value: 'roe', label: 'ROE' },
  { value: 'seo_return', label: '기대수익률' },
]

const inputCls = 'border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400'

export default function FilterPanel({ onSearch, loading }) {
  const [filters, setFilters] = useState(DEFAULT_FILTERS)

  const set = (key, value) => setFilters((prev) => ({ ...prev, [key]: value }))

  const selectedPreset = PRESETS.find(p => p.value === filters.preset)

  const handleSubmit = (e) => {
    e.preventDefault()
    const params = {}
    if (filters.date) params.date = filters.date
    if (filters.market) params.market = filters.market
    params.sort_by = `${filters.sort_by} ${filters.sort_order}`
    if (filters.top) params.top = Number(filters.top)
    if (filters.per_min !== '') params.per_min = Number(filters.per_min)
    if (filters.per_max !== '') params.per_max = Number(filters.per_max)
    if (filters.pbr_max !== '') params.pbr_max = Number(filters.pbr_max)
    if (filters.roe_min !== '') params.roe_min = Number(filters.roe_min)
    if (filters.drop_from_high !== '') params.drop_from_high = Number(filters.drop_from_high)
    if (filters.include_negative) params.include_negative = true
    if (filters.earnings_only) params.earnings_only = true
    if (filters.preset) {
      params.preset = filters.preset
      params.include_guru = filters.preset === 'greenblatt' || filters.preset === 'neff'
      if (params.include_guru) params.guru_top = Number(filters.guru_top) || 30
    }
    if (filters.regime_aware) params.regime_aware = true
    onSearch(params)
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
      <h2 className="font-semibold text-gray-800">필터 설정</h2>

      {/* 구루 프리셋 */}
      <div className="flex flex-col gap-1">
        <span className="text-xs font-medium text-gray-500">투자 전략</span>
        <select
          value={filters.preset}
          onChange={(e) => set('preset', e.target.value)}
          className={`${inputCls} font-medium`}
        >
          {PRESETS.map(p => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
        {selectedPreset?.desc && (
          <p className="text-xs text-gray-400 mt-0.5">{selectedPreset.desc}</p>
        )}
        {selectedPreset?.dart && (
          <p className="text-xs text-amber-600 mt-0.5">DART 재무 조회 필요 (1~2분 소요)</p>
        )}
      </div>

      {/* 체제 연계 토글 */}
      <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
        <input type="checkbox" checked={filters.regime_aware} onChange={(e) => set('regime_aware', e.target.checked)} className="rounded" />
        체제 연계 (시장 상황 반영)
      </label>

      {/* DART 분석 대상 수 */}
      {(filters.preset === 'greenblatt' || filters.preset === 'neff') && (
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-500">분석 대상 종목 수</span>
          <input type="number" value={filters.guru_top} onChange={(e) => set('guru_top', e.target.value)}
            min="10" max="100" className={inputCls} />
          <span className="text-xs text-gray-400">DART API 호출량 = 종목수 x 2</span>
        </label>
      )}

      {/* 날짜 & 시장 */}
      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-500">날짜</span>
          <input type="date" value={filters.date} onChange={(e) => set('date', e.target.value)} className={inputCls} />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-500">시장</span>
          <select value={filters.market} onChange={(e) => set('market', e.target.value)} className={inputCls}>
            <option value="">전체</option>
            <option value="KOSPI">KOSPI</option>
            <option value="KOSDAQ">KOSDAQ</option>
          </select>
        </label>
      </div>

      {/* PER 범위 */}
      <div className="flex flex-col gap-1">
        <span className="text-xs font-medium text-gray-500">PER 범위 <span className="text-gray-400">(수익 대비 주가)</span></span>
        <div className="flex items-center gap-2">
          <input type="number" placeholder="최소 (예: 5)" value={filters.per_min}
            onChange={(e) => set('per_min', e.target.value)} className={`${inputCls} w-full`} step="0.1" />
          <span className="text-gray-400 text-sm">~</span>
          <input type="number" placeholder="최대 (예: 15)" value={filters.per_max}
            onChange={(e) => set('per_max', e.target.value)} className={`${inputCls} w-full`} step="0.1" />
        </div>
      </div>

      {/* PBR & ROE & 52주 하락률 */}
      <div className="grid grid-cols-3 gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-500">PBR 최대</span>
          <input type="number" placeholder="예: 1.5" value={filters.pbr_max}
            onChange={(e) => set('pbr_max', e.target.value)} className={inputCls} step="0.1" />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-500">ROE 최소(%)</span>
          <input type="number" placeholder="예: 10" value={filters.roe_min}
            onChange={(e) => set('roe_min', e.target.value)} className={inputCls} step="0.1" />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-500">52주 하락(%)</span>
          <input type="number" placeholder="예: -30" value={filters.drop_from_high}
            onChange={(e) => set('drop_from_high', e.target.value)} className={inputCls} step="5" />
        </label>
      </div>

      {/* 정렬 */}
      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-500">정렬 기준</span>
          <select value={filters.sort_by} onChange={(e) => set('sort_by', e.target.value)} className={inputCls}>
            {SORT_FIELDS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-500">정렬 방향</span>
          <select value={filters.sort_order} onChange={(e) => set('sort_order', e.target.value)} className={inputCls}>
            <option value="asc">오름차순</option>
            <option value="desc">내림차순</option>
          </select>
        </label>
      </div>

      {/* 상위 N개 */}
      <label className="flex flex-col gap-1">
        <span className="text-xs font-medium text-gray-500">상위 N개</span>
        <input type="number" value={filters.top} onChange={(e) => set('top', e.target.value)}
          className={inputCls} min="1" max="500" />
      </label>

      {/* 체크박스 */}
      <div className="flex flex-col gap-2">
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input type="checkbox" checked={filters.include_negative} onChange={(e) => set('include_negative', e.target.checked)} className="rounded" />
          적자기업(PER 음수) 포함
        </label>
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input type="checkbox" checked={filters.earnings_only} onChange={(e) => set('earnings_only', e.target.checked)} className="rounded" />
          당일 실적발표 종목만
        </label>
      </div>

      <button type="submit" disabled={loading}
        className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold rounded-lg text-sm transition-colors">
        {loading ? '조회 중...' : '조회하기'}
      </button>
    </form>
  )
}
