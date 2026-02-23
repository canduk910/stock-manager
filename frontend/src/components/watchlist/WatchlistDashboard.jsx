import { useState } from 'react'

// ── 포맷 유틸 ────────────────────────────────────────────────────────────────

function fmtPrice(v) {
  return v != null ? v.toLocaleString() : '-'
}
function fmtAwk(v) {
  return v != null ? v.toLocaleString() : '-'
}
function fmtPct(v, digits = 1) {
  return v != null ? `${v.toFixed(digits)}%` : '-'
}

function ChangeCell({ change, changePct }) {
  if (changePct == null) return <span className="text-gray-400">-</span>
  const up = changePct > 0
  const down = changePct < 0
  const color = up ? 'text-red-600' : down ? 'text-blue-600' : 'text-gray-600'
  const arrow = up ? '▲' : down ? '▼' : ''
  const sign = up ? '+' : ''
  return (
    <span className={`font-medium ${color}`}>
      {arrow} {sign}{fmtPrice(change)} ({sign}{fmtPct(changePct, 2)})
    </span>
  )
}

// ── CSV 다운로드 ──────────────────────────────────────────────────────────────

function downloadCsv(stocks) {
  const headers = [
    '종목코드','종목명','현재가','전일대비(원)','전일대비(%)','시가총액(억)',
    '매출액(억)','영업이익(억)','당기순이익(억)','영업이익률(%)','보고서기준','메모',
  ]
  const rows = stocks.map((s) => [
    s.code, s.name, s.price ?? '', s.change ?? '', s.change_pct ?? '',
    s.market_cap ?? '', s.revenue ?? '', s.operating_profit ?? '',
    s.net_income ?? '', s.oi_margin ?? '', s.report_date ?? '', s.memo ?? '',
  ])
  const csv = [headers, ...rows].map((r) => r.map(String).join(',')).join('\n')
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `watchlist_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// ── 인라인 메모 편집 셀 ───────────────────────────────────────────────────────

function MemoCell({ code, memo, onSave }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(memo || '')
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave(code, val)
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

// ── 메인 대시보드 컴포넌트 ───────────────────────────────────────────────────

export default function WatchlistDashboard({
  stocks,
  loading,
  totalCount,
  onRefresh,
  onDelete,
  onMemoSave,
  onShowInfo,
}) {
  const [confirmCode, setConfirmCode] = useState(null)

  const handleDeleteClick = (code) => setConfirmCode(code)
  const handleDeleteConfirm = async () => {
    if (!confirmCode) return
    await onDelete(confirmCode)
    setConfirmCode(null)
  }

  if (!stocks && !loading) return null

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
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {[
                  '종목코드','종목명','현재가','전일대비','시가총액(억)',
                  '매출액(억)','영업이익(억)','순이익(억)','영업이익률','보고서기준','메모','',
                ].map((h) => (
                  <th key={h} className="px-3 py-2.5 text-left text-xs font-semibold text-gray-600 whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {stocks.map((s) => (
                <tr key={s.code} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-3 py-2.5 text-gray-500 font-mono text-xs">{s.code}</td>
                  <td className="px-3 py-2.5">
                    <button
                      onClick={() => onShowInfo(s.code, s.name)}
                      className="font-medium text-blue-700 hover:underline text-left"
                    >
                      {s.name}
                    </button>
                  </td>
                  <td className="px-3 py-2.5 text-right font-medium">{fmtPrice(s.price)}</td>
                  <td className="px-3 py-2.5 text-right whitespace-nowrap">
                    <ChangeCell change={s.change} changePct={s.change_pct} />
                  </td>
                  <td className="px-3 py-2.5 text-right">{fmtAwk(s.market_cap)}</td>
                  <td className="px-3 py-2.5 text-right">{fmtAwk(s.revenue)}</td>
                  <td className="px-3 py-2.5 text-right">{fmtAwk(s.operating_profit)}</td>
                  <td className="px-3 py-2.5 text-right">{fmtAwk(s.net_income)}</td>
                  <td className="px-3 py-2.5 text-right">{fmtPct(s.oi_margin)}</td>
                  <td className="px-3 py-2.5 text-center text-xs text-gray-500">{s.report_date || '-'}</td>
                  <td className="px-3 py-2.5">
                    <MemoCell code={s.code} memo={s.memo} onSave={onMemoSave} />
                  </td>
                  <td className="px-3 py-2.5">
                    <button
                      onClick={() => handleDeleteClick(s.code)}
                      className="text-xs text-gray-400 hover:text-red-500 transition-colors"
                      title="삭제"
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 삭제 확인 팝업 */}
      {confirmCode && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 w-80">
            <p className="font-semibold text-gray-800 mb-1">관심종목 삭제</p>
            <p className="text-sm text-gray-500 mb-4">
              <strong>{confirmCode}</strong> 종목을 관심종목에서 삭제할까요?
            </p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setConfirmCode(null)}
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
