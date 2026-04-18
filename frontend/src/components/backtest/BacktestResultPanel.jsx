/**
 * 백테스트 결과 패널 — 수익률 곡선 + 거래 내역 + 추가 메트릭.
 */
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
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
  const trades = result.trades || result.result?.trades || result.result_json?.result?.trades || []

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

      {/* 수익률 곡선 */}
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
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* 거래 내역 */}
      {trades.length > 0 && (
        <div className="bg-white rounded-lg border p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-3">거래 내역 ({trades.length}건)</h3>
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
                {trades.map((t, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-3 py-1.5">{t.date || t.entry_date || '-'}</td>
                    <td className="px-3 py-1.5">
                      <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                        t.direction === 'BUY' || t.side === 'buy'
                          ? 'bg-red-50 text-red-700'
                          : 'bg-blue-50 text-blue-700'
                      }`}>
                        {t.direction || t.side || '-'}
                      </span>
                    </td>
                    <td className="px-3 py-1.5 text-right">{t.price?.toLocaleString() || '-'}</td>
                    <td className="px-3 py-1.5 text-right">{t.quantity || t.qty || '-'}</td>
                    <td className={`px-3 py-1.5 text-right ${
                      (t.profit_pct || 0) >= 0 ? 'text-red-600' : 'text-blue-600'
                    }`}>
                      {t.profit_pct != null ? `${t.profit_pct >= 0 ? '+' : ''}${t.profit_pct.toFixed(1)}%` : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
