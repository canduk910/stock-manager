import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  DndContext,
  closestCenter,
  PointerSensor,
  TouchSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

// ── 포맷 유틸 ────────────────────────────────────────────────────────────────

function fmtPrice(v, currency = 'KRW') {
  if (v == null) return '-'
  if (currency === 'USD') return `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  return v.toLocaleString()
}

function fmtFinVal(v, currency = 'KRW') {
  if (v == null) return '-'
  if (currency === 'USD') return `$${v.toLocaleString()}M`
  return v.toLocaleString()
}

function fmtCap(v, currency = 'KRW') {
  if (v == null) return '-'
  if (currency === 'USD') return `$${v.toLocaleString()}M`
  return v.toLocaleString()
}

function fmtPct(v, digits = 1) {
  return v != null ? `${v.toFixed(digits)}%` : '-'
}

function ChangeCell({ change, changePct, currency = 'KRW' }) {
  if (changePct == null) return <span className="text-gray-400">-</span>
  const up = changePct > 0
  const down = changePct < 0
  const color = up ? 'text-red-600' : down ? 'text-blue-600' : 'text-gray-600'
  const arrow = up ? '▲' : down ? '▼' : ''
  const sign = up ? '+' : ''
  const changeStr = currency === 'USD'
    ? `$${Math.abs(change ?? 0).toFixed(2)}`
    : (change != null ? Math.abs(change).toLocaleString() : '')
  const changeSign = change != null ? (change >= 0 ? '+' : '-') : sign
  return (
    <span className={`font-medium ${color}`}>
      {arrow} {changeSign}{changeStr} ({sign}{fmtPct(changePct, 2)})
    </span>
  )
}

function MarketBadge({ market }) {
  if (!market || market === 'KR') return null
  return (
    <span className="ml-1 text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded font-medium">
      {market}
    </span>
  )
}

// ── CSV 다운로드 ──────────────────────────────────────────────────────────────

function downloadCsv(stocks) {
  const headers = [
    '종목코드','시장','종목명','현재가','통화','전일대비(%)','시가총액',
    '매출액','영업이익','당기순이익','영업이익률(%)','보고서기준','메모',
  ]
  const rows = stocks.map((s) => [
    s.code, s.market ?? 'KR', s.name, s.price ?? '', s.currency ?? 'KRW',
    s.change_pct ?? '', s.market_cap ?? '', s.revenue ?? '', s.operating_profit ?? '',
    s.net_income ?? '', s.oi_margin ?? '', s.report_date ?? '', s.memo ?? '',
  ])
  const csv = [headers, ...rows].map((r) => r.map(String).join(',')).join('\n')
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const d = new Date()
  const dateStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  a.download = `watchlist_${dateStr}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// ── 인라인 메모 편집 셀 ───────────────────────────────────────────────────────

function MemoCell({ code, market, memo, onSave }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(memo || '')
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave(code, val, market)
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  if (editing) {
    return (
      <div className="flex gap-1 items-center min-w-32">
        <input
          autoFocus
          value={val}
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') setEditing(false) }}
          className="border border-gray-300 rounded px-2 py-0.5 text-xs w-32 focus:outline-none focus:ring-1 focus:ring-blue-400"
        />
        <button onClick={handleSave} disabled={saving} className="text-xs text-blue-600 hover:underline">저장</button>
        <button onClick={() => setEditing(false)} className="text-xs text-gray-400 hover:underline">취소</button>
      </div>
    )
  }

  return (
    <div className="flex gap-1 items-center group">
      <span className="text-xs text-gray-500 max-w-32 truncate">{memo || '-'}</span>
      <button
        onClick={() => { setVal(memo || ''); setEditing(true) }}
        className="opacity-0 group-hover:opacity-100 text-xs text-gray-400 hover:text-blue-500 transition-opacity"
        title="메모 수정"
      >
        ✏
      </button>
    </div>
  )
}

// ── 드래그 가능한 테이블 행 ───────────────────────────────────────────────────

function SortableRow({ id, stock, onDelete, onMemoSave, onShowInfo }) {
  const navigate = useNavigate()
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    position: 'relative',
    zIndex: isDragging ? 50 : 'auto',
  }

  const currency = stock.currency || 'KRW'
  const mkt = stock.market || 'KR'

  return (
    <tr ref={setNodeRef} style={style} className="border-b border-gray-100 hover:bg-gray-50">
      {/* 드래그 핸들 */}
      <td className="px-2 py-2.5 text-center" {...attributes} {...listeners}>
        <span className="cursor-grab active:cursor-grabbing text-gray-300 hover:text-gray-500 select-none">⠿</span>
      </td>
      <td className="px-3 py-2.5 font-mono text-xs">
        <button
          onClick={() => onShowInfo && onShowInfo(stock.code, stock.name, mkt)}
          className="text-blue-600 hover:underline hover:text-blue-800"
          title="재무 상세보기"
        >
          {stock.code}
        </button>
        <MarketBadge market={mkt !== 'KR' ? mkt : null} />
      </td>
      <td className="px-3 py-2.5">
        <button
          onClick={() => navigate(`/detail/${stock.code}`)}
          className="font-medium text-blue-700 hover:underline text-left"
        >
          {stock.name}
        </button>
      </td>
      <td className="px-3 py-2.5 text-right font-medium">{fmtPrice(stock.price, currency)}</td>
      <td className="px-3 py-2.5 text-right whitespace-nowrap">
        <ChangeCell change={stock.change} changePct={stock.change_pct} currency={currency} />
      </td>
      <td className="px-3 py-2.5 text-right text-xs">
        {fmtCap(stock.market_cap, currency)}
        {stock.market_cap != null && <span className="text-gray-400 ml-0.5">{currency === 'USD' ? 'M' : '억'}</span>}
      </td>
      <td className="px-3 py-2.5 text-right text-xs">
        {fmtFinVal(stock.revenue, currency)}
        {stock.revenue != null && <span className="text-gray-400 ml-0.5">{currency === 'USD' ? 'M' : '억'}</span>}
      </td>
      <td className="px-3 py-2.5 text-right text-xs">
        {fmtFinVal(stock.operating_profit, currency)}
        {stock.operating_profit != null && <span className="text-gray-400 ml-0.5">{currency === 'USD' ? 'M' : '억'}</span>}
      </td>
      <td className="px-3 py-2.5 text-right text-xs">
        {fmtFinVal(stock.net_income, currency)}
        {stock.net_income != null && <span className="text-gray-400 ml-0.5">{currency === 'USD' ? 'M' : '억'}</span>}
      </td>
      <td className="px-3 py-2.5 text-right">{fmtPct(stock.oi_margin)}</td>
      <td className="px-3 py-2.5 text-right">{stock.dividend_yield != null ? fmtPct(stock.dividend_yield, 2) : '-'}</td>
      <td className="px-3 py-2.5 text-center text-xs text-gray-500">{stock.report_date || '-'}</td>
      <td className="px-3 py-2.5">
        <MemoCell code={stock.code} market={mkt} memo={stock.memo} onSave={onMemoSave} />
      </td>
      <td className="px-3 py-2.5">
        <button
          onClick={() => onDelete(stock.code, mkt)}
          className="text-xs text-gray-400 hover:text-red-500 transition-colors"
          title="삭제"
        >
          ✕
        </button>
      </td>
    </tr>
  )
}

// ── 메인 대시보드 컴포넌트 ───────────────────────────────────────────────────

export default function WatchlistDashboard({
  stocks,
  loading,
  totalCount,
  onRefresh,
  onDelete,
  onMemoSave,
  onReorder,
  onShowInfo,
}) {
  const [confirmItem, setConfirmItem] = useState(null) // { code, market }

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 5 },
    }),
    useSensor(TouchSensor, {
      activationConstraint: { delay: 200, tolerance: 5 },
    }),
  )

  const handleDeleteClick = (code, market) => setConfirmItem({ code, market })
  const handleDeleteConfirm = async () => {
    if (!confirmItem) return
    await onDelete(confirmItem.code, confirmItem.market)
    setConfirmItem(null)
  }

  const handleDragEnd = useCallback((event) => {
    const { active, over } = event
    if (!over || active.id === over.id || !stocks) return

    const oldIndex = stocks.findIndex(s => `${s.market || 'KR'}:${s.code}` === active.id)
    const newIndex = stocks.findIndex(s => `${s.market || 'KR'}:${s.code}` === over.id)
    if (oldIndex === -1 || newIndex === -1) return

    const newOrder = arrayMove(stocks, oldIndex, newIndex)
    onReorder?.(newOrder)
  }, [stocks, onReorder])

  if (!stocks && !loading) return null

  const sortableIds = stocks?.map(s => `${s.market || 'KR'}:${s.code}`) ?? []

  return (
    <div className="space-y-3">
      {/* 툴바 */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          {loading
            ? <span className="animate-pulse">{totalCount}개 종목 조회 중...</span>
            : stocks
            ? <span><strong className="text-gray-800">{stocks.length}개</strong> 종목</span>
            : null}
        </p>
        <div className="flex gap-2">
          {stocks && stocks.length > 0 && (
            <button
              onClick={() => downloadCsv(stocks)}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-600"
            >
              CSV 다운로드
            </button>
          )}
          <button
            onClick={onRefresh}
            disabled={loading}
            className="px-3 py-1.5 text-sm bg-gray-800 hover:bg-gray-700 disabled:opacity-50 text-white rounded-lg transition-colors"
          >
            {loading ? '조회 중...' : '새로고침'}
          </button>
        </div>
      </div>

      {/* 로딩 */}
      {loading && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <div className="inline-block w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-3" />
          <p className="text-sm text-gray-500">{totalCount}개 종목 시세 및 재무 데이터 조회 중...</p>
          <p className="text-xs text-gray-400 mt-1">첫 조회는 수십 초가 걸릴 수 있습니다 (이후 캐시됨)</p>
        </div>
      )}

      {/* 테이블 */}
      {stocks && !loading && (
        <div className="overflow-x-auto rounded-xl border border-gray-200">
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={sortableIds} strategy={verticalListSortingStrategy}>
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    {[
                      '','종목코드','종목명','현재가','전일대비','시가총액',
                      '매출액','영업이익','순이익','영업이익률','배당수익률','보고서기준','메모','',
                    ].map((h, i) => (
                      <th key={`${h}-${i}`} className={`px-3 py-2.5 text-left text-xs font-semibold text-gray-600 whitespace-nowrap ${i === 0 ? 'w-8 px-2' : ''}`}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {stocks.map((s) => (
                    <SortableRow
                      key={`${s.market || 'KR'}:${s.code}`}
                      id={`${s.market || 'KR'}:${s.code}`}
                      stock={s}
                      onDelete={handleDeleteClick}
                      onMemoSave={onMemoSave}
                      onShowInfo={onShowInfo}
                    />
                  ))}
                </tbody>
              </table>
            </SortableContext>
          </DndContext>
        </div>
      )}

      {/* 삭제 확인 팝업 */}
      {confirmItem && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-80">
            <p className="font-semibold text-gray-800 mb-1">관심종목 삭제</p>
            <p className="text-sm text-gray-500 mb-4">
              <strong>{confirmItem.code}</strong> 종목을 관심종목에서 삭제할까요?
            </p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setConfirmItem(null)}
                className="px-4 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                취소
              </button>
              <button
                onClick={handleDeleteConfirm}
                className="px-4 py-1.5 text-sm bg-red-600 hover:bg-red-700 text-white rounded-lg"
              >
                삭제
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
