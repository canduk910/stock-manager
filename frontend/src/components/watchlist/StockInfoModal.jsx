import { useEffect, useState } from 'react'
import { useStockInfo } from '../../hooks/useWatchlist'

function fmtPrice(v, currency = 'KRW') {
  if (v == null) return '-'
  if (currency === 'USD') return `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  return v.toLocaleString() + '원'
}

function fmtFinVal(v, currency = 'KRW') {
  if (v == null) return '-'
  if (currency === 'USD') return `$${v.toLocaleString()}M`
  return v.toLocaleString() + '억'
}

function fmtPct(v) {
  if (v == null) return '-'
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(1)}%`
}

function growthColor(v) {
  if (v == null) return 'text-gray-400'
  return v > 0 ? 'text-red-600' : v < 0 ? 'text-blue-600' : 'text-gray-500'
}

function ChangeCell({ change, changePct, currency = 'KRW' }) {
  if (changePct == null) return <span className="text-gray-400">-</span>
  const up = changePct > 0
  const down = changePct < 0
  const color = up ? 'text-red-600' : down ? 'text-blue-600' : 'text-gray-600'
  const sign = up ? '+' : ''
  const changeStr = currency === 'USD'
    ? `$${Math.abs(change ?? 0).toFixed(2)}`
    : (change != null ? Math.abs(change).toLocaleString() + '원' : '')
  const changeSign = change != null ? (change >= 0 ? '+' : '-') : sign
  return (
    <span className={color}>
      {changeSign}{changeStr} ({sign}{changePct?.toFixed(2)}%)
    </span>
  )
}

export default function StockInfoModal({ code, name, market = 'KR', onClose, onMemoSave }) {
  const { data, loading, error, load } = useStockInfo()
  const [editingMemo, setEditingMemo] = useState(false)
  const [memoVal, setMemoVal] = useState('')

  useEffect(() => {
    if (code) load(code, market)
  }, [code, market])

  useEffect(() => {
    if (data?.memo != null) setMemoVal(data.memo)
  }, [data])

  // ESC 키로 닫기
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const handleMemoSave = async () => {
    await onMemoSave(code, memoVal, market)
    setEditingMemo(false)
  }

  const b = data?.basic || {}
  const currency = b.currency || (market === 'US' ? 'USD' : 'KRW')
  const unitLabel = currency === 'USD' ? 'M USD' : '억원'

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 헤더 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h2 className="text-lg font-bold text-gray-900">{name}</h2>
            <span className="text-xs text-gray-400 font-mono">{code}</span>
            {market !== 'KR' && (
              <span className="ml-2 text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded font-medium">
                {market}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 text-xl leading-none"
          >
            ✕
          </button>
        </div>

        <div className="px-6 py-5 space-y-6">
          {loading && (
            <div className="text-center py-8">
              <div className="inline-block w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-2" />
              <p className="text-sm text-gray-400">조회 중...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 text-red-700 rounded-lg px-4 py-3 text-sm">{error}</div>
          )}

          {data && !loading && (
            <>
              {/* 기본정보 카드 */}
              <div className="grid grid-cols-2 gap-3">
                <InfoCard label="현재가" value={fmtPrice(b.price, currency)} />
                <InfoCard
                  label="전일대비"
                  value={<ChangeCell change={b.change} changePct={b.change_pct} currency={currency} />}
                />
                <InfoCard label="시가총액" value={b.market_cap != null ? `${b.market_cap.toLocaleString()} ${currency === 'USD' ? 'M USD' : '억'}` : '-'} />
                {currency === 'KRW' && <InfoCard label="상장주식수" value={b.shares?.toLocaleString() ?? '-'} />}
                <InfoCard label="PER" value={b.per != null ? `${Math.floor(b.per)}배` : '-'} />
                <InfoCard label="PBR" value={b.pbr != null ? `${Math.floor(b.pbr)}배` : '-'} />
                <InfoCard label="52주 고가" value={fmtPrice(b.high_52, currency)} />
                <InfoCard label="52주 저가" value={fmtPrice(b.low_52, currency)} />
                <InfoCard label="시장/거래소" value={b.market ?? '-'} />
                <InfoCard label="업종" value={b.sector ?? '-'} />
              </div>

              {/* 재무 테이블 */}
              {data.financials_3y && data.financials_3y.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">
                    재무 요약 (단위: {unitLabel})
                    {currency === 'USD' && (
                      <span className="ml-2 text-xs text-gray-400 font-normal">yfinance 기준 · 최대 4년</span>
                    )}
                  </h3>
                  <div className="overflow-x-auto rounded-lg border border-gray-200">
                    <table className="min-w-full text-sm">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 sticky left-0 bg-gray-50">항목</th>
                          {data.financials_3y.map((f) => (
                            <th key={f.year} className="px-4 py-2 text-right text-xs font-semibold text-gray-500 min-w-[72px]">
                              {f.dart_url ? (
                                <a
                                  href={f.dart_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-blue-600 hover:underline"
                                  title="DART 사업보고서 열기"
                                >
                                  {f.year}
                                </a>
                              ) : (
                                f.year
                              )}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        <FinRow label="매출액" rows={data.financials_3y} field="revenue" yoyField="yoy_revenue" />
                        <FinRow label="영업이익" rows={data.financials_3y} field="operating_profit" yoyField="yoy_op" />
                        <FinRow label="당기순이익" rows={data.financials_3y} field="net_income" />
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* 메모 */}
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-sm font-semibold text-gray-700">메모</h3>
                  {!editingMemo && (
                    <button
                      onClick={() => setEditingMemo(true)}
                      className="text-xs text-gray-400 hover:text-blue-500"
                    >
                      수정
                    </button>
                  )}
                </div>
                {editingMemo ? (
                  <div className="flex gap-2">
                    <input
                      autoFocus
                      value={memoVal}
                      onChange={(e) => setMemoVal(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') handleMemoSave(); if (e.key === 'Escape') setEditingMemo(false) }}
                      className="flex-1 border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                    />
                    <button onClick={handleMemoSave} className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">저장</button>
                    <button onClick={() => setEditingMemo(false)} className="px-3 py-1.5 border border-gray-300 text-sm rounded-lg hover:bg-gray-50">취소</button>
                  </div>
                ) : (
                  <p className="text-sm text-gray-600 bg-gray-50 rounded-lg px-3 py-2 min-h-[36px]">
                    {data.memo || <span className="text-gray-300">메모 없음</span>}
                  </p>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function InfoCard({ label, value }) {
  return (
    <div className="bg-gray-50 rounded-lg px-4 py-3">
      <p className="text-xs text-gray-400 mb-0.5">{label}</p>
      <p className="text-sm font-semibold text-gray-800">{value}</p>
    </div>
  )
}

function FinRow({ label, rows, field, yoyField }) {
  return (
    <tr className="border-t border-gray-100">
      <td className="px-4 py-2 text-gray-700 font-medium">{label}</td>
      {rows.map((f, i) => (
        <td key={f.year} className="px-4 py-2 text-right">
          <div className="font-medium">{f[field] != null ? f[field].toLocaleString() : '-'}</div>
          {yoyField && i > 0 && f[yoyField] != null && (
            <div className={`text-xs ${growthColor(f[yoyField])}`}>
              {fmtPct(f[yoyField])}
            </div>
          )}
        </td>
      ))}
    </tr>
  )
}
