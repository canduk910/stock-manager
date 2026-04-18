/**
 * 백테스트 결과 패널 — 수익률 곡선 + 매매 시그널 마커 + 거래 내역 + 추가 메트릭.
 */
import { useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceDot } from 'recharts'
import MetricsCard from './MetricsCard'

/**
 * MCP 중첩 메트릭 (basic/risk/trading) → 플랫 메트릭으로 변환.
 */
function flattenMetrics(raw) {
  if (!raw) return null
  // 이미 플랫 형태 (total_return_pct 키가 있으면)
  if (raw.total_return_pct != null) return raw
  // MCP 중첩 형태
  const basic = raw.basic || {}
  const risk = raw.risk || {}
  const trading = raw.trading || {}
  return {
    total_return_pct: basic.total_return,
    cagr: basic.annual_return,
    max_drawdown: basic.max_drawdown != null ? -Math.abs(basic.max_drawdown) : null,
    sharpe_ratio: risk.sharpe_ratio,
    sortino_ratio: risk.sortino_ratio,
    win_rate: trading.win_rate,
    profit_factor: trading.profit_loss_ratio,
    total_trades: trading.total_orders,
  }
}

/**
 * equity_curve 오브젝트 {date: value} → 배열 [{date, equity}] 변환.
 */
function normalizeEquityCurve(raw) {
  if (!raw) return []
  if (Array.isArray(raw)) return raw
  // {date: value} 형태
  return Object.entries(raw).map(([date, equity]) => ({ date, equity }))
}

export default function BacktestResultPanel({ result }) {
  if (!result) return null

  const rawMetrics = result.metrics || result.result?.metrics || result.result_json?.result?.metrics
  const metrics = flattenMetrics(rawMetrics)
  const rawCurve = result.equity_curve || result.result?.equity_curve || result.result_json?.result?.equity_curve
  const equityCurve = normalizeEquityCurve(rawCurve)
  const rawTrades = result.trades || result.result?.trades || result.result_json?.result?.trades || []
  const resultParams = result.params || result.result?.params || result.result_json?.params

  // 거래 내역 전처리: 매도 수익률 계산
  const processedTrades = useMemo(() => {
    let lastBuyPrice = null
    return rawTrades.map((t) => {
      const isBuy = (t.direction || t.side || '').toLowerCase() === 'buy'
      const date = t.date || t.entry_date || t.timestamp || t.time || '-'
      if (isBuy) {
        lastBuyPrice = t.price
        return { ...t, _isBuy: true, _date: date }
      } else {
        const profitPct = t.profit_pct ?? t.return_pct ??
          (lastBuyPrice && t.price ? ((t.price - lastBuyPrice) / lastBuyPrice * 100) : null)
        return { ...t, _isBuy: false, _profitPct: profitPct, _date: date }
      }
    })
  }, [rawTrades])

  // 수익률 곡선 위 매매 시그널 마커
  const tradeMarkers = useMemo(() => {
    return rawTrades.map((t) => {
      const date = t.date || t.entry_date || t.timestamp || t.time
      if (!date) return null
      const isBuy = (t.direction || t.side || '').toLowerCase() === 'buy'
      const point = equityCurve.find((e) => e.date === date)
      if (!point) return null
      return { date: point.date, equity: point.equity, isBuy }
    }).filter(Boolean)
  }, [rawTrades, equityCurve])

  return (
    <div className="space-y-4">
      {/* 메트릭 카드 */}
      <MetricsCard metrics={metrics} />

      {/* 추가 메트릭 */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {metrics.cagr != null && (
            <div className="bg-white rounded-lg border p-3 text-center">
              <div className="text-xs text-gray-500">CAGR</div>
              <div className="text-lg font-semibold">{metrics.cagr?.toFixed(1)}%</div>
            </div>
          )}
          {metrics.sortino_ratio != null && (
            <div className="bg-white rounded-lg border p-3 text-center">
              <div className="text-xs text-gray-500">Sortino</div>
              <div className="text-lg font-semibold">{metrics.sortino_ratio?.toFixed(2)}</div>
            </div>
          )}
          {metrics.profit_factor != null && (
            <div className="bg-white rounded-lg border p-3 text-center">
              <div className="text-xs text-gray-500">Profit Factor</div>
              <div className="text-lg font-semibold">{metrics.profit_factor?.toFixed(2)}</div>
            </div>
          )}
          {metrics.total_trades != null && (
            <div className="bg-white rounded-lg border p-3 text-center">
              <div className="text-xs text-gray-500">총 거래 수</div>
              <div className="text-lg font-semibold">{metrics.total_trades}</div>
            </div>
          )}
        </div>
      )}

      {/* 사용된 파라미터 */}
      {resultParams && Object.keys(resultParams).length > 0 && (
        <div className="bg-gray-50 rounded-lg border p-3">
          <p className="text-xs font-medium text-gray-500 mb-1">사용된 파라미터</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(resultParams).map(([k, v]) => (
              <span key={k} className="text-xs bg-white border rounded px-2 py-0.5">
                <span className="text-gray-500">{k}:</span> <span className="font-mono">{v}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 수익률 곡선 + 매매 시그널 마커 */}
      {equityCurve.length > 0 && (
        <div className="bg-white rounded-lg border p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-3">수익률 곡선</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={equityCurve}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v.toLocaleString()}`} />
              <Tooltip
                labelFormatter={(v) => v}
                formatter={(v) => [v.toLocaleString(), '순자산']}
              />
              <Line type="monotone" dataKey="equity" stroke="#2563eb" dot={false} strokeWidth={1.5} />
              {tradeMarkers.map((m, i) => (
                <ReferenceDot
                  key={i}
                  x={m.date}
                  y={m.equity}
                  r={4}
                  fill={m.isBuy ? '#dc2626' : '#2563eb'}
                  stroke="white"
                  strokeWidth={1.5}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
          {tradeMarkers.length > 0 && (
            <div className="flex gap-4 text-xs text-gray-500 mt-2 justify-end">
              <span className="flex items-center gap-1">
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-600" /> 매수
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-blue-600" /> 매도
              </span>
            </div>
          )}
        </div>
      )}

      {/* 거래 내역 */}
      {processedTrades.length > 0 && (
        <div className="bg-white rounded-lg border p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-3">거래 내역 ({processedTrades.length}건)</h3>
          <div className="overflow-x-auto max-h-64 overflow-y-auto">
            <table className="w-full text-xs">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-3 py-2 text-left">날짜</th>
                  <th className="px-3 py-2 text-left">방향</th>
                  <th className="px-3 py-2 text-right">가격</th>
                  <th className="px-3 py-2 text-right">수량</th>
                  <th className="px-3 py-2 text-right">수익률</th>
                </tr>
              </thead>
              <tbody>
                {processedTrades.map((t, i) => {
                  const profitPct = t._isBuy ? null : t._profitPct
                  return (
                    <tr key={i} className="border-t">
                      <td className="px-3 py-1.5">{t._date}</td>
                      <td className="px-3 py-1.5">
                        <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                          t._isBuy
                            ? 'bg-red-50 text-red-700'
                            : 'bg-blue-50 text-blue-700'
                        }`}>
                          {t._isBuy ? 'Buy' : 'Sell'}
                        </span>
                      </td>
                      <td className="px-3 py-1.5 text-right">{t.price?.toLocaleString() || '-'}</td>
                      <td className="px-3 py-1.5 text-right">{t.quantity || t.qty || '-'}</td>
                      <td className={`px-3 py-1.5 text-right ${
                        profitPct != null ? (profitPct >= 0 ? 'text-red-600' : 'text-blue-600') : ''
                      }`}>
                        {profitPct != null ? `${profitPct >= 0 ? '+' : ''}${profitPct.toFixed(1)}%` : '-'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
