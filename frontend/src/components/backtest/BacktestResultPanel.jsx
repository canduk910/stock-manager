/**
 * 백테스트 결과 패널 — 캔들+수익률 통합 차트 + 거래 내역 + 메트릭.
 *
 * Props:
 *   result  - MCP 백테스트 결과 객체
 *   symbol  - 종목 코드 (OHLCV 조회용)
 *   market  - 시장 코드 (기본 'KR')
 */
import { useState, useEffect, useMemo, useCallback } from 'react'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceArea, BarChart,
} from 'recharts'
import MetricsCard from './MetricsCard'
import { PARAM_KR } from './StrategySelector'
import AnnualReturnsTable from './AnnualReturnsTable'
import MonthlyReturnsHeatmap from './MonthlyReturnsHeatmap'
import PositionSummary from './PositionSummary'
import { fetchAdvisoryOhlcv } from '../../api/advisory'

// ── 유틸 ──────────────────────────────────────────────────────────────────

/** 원화 금액 소수점 절사 (원 단위). 비숫자는 그대로 반환. */
function floorKRW(v) {
  return typeof v === 'number' ? Math.floor(v) : v
}

/** UTC 타임스탬프 → KST 변환. 날짜만 있으면 그대로 반환. */
function toKST(dateStr) {
  if (!dateStr || dateStr === '-') return '-'
  if (!dateStr.includes('T')) return dateStr
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  const kst = new Date(d.getTime() + 9 * 60 * 60 * 1000)
  return kst.toISOString().slice(0, 16).replace('T', ' ')
}

function flattenMetrics(raw) {
  if (!raw) return null
  if (raw.total_return_pct != null) return raw
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

function normalizeEquityCurve(raw) {
  if (!raw) return []
  if (Array.isArray(raw)) return raw
  return Object.entries(raw).map(([date, equity]) => ({ date, equity }))
}

// ── 메인 컴포넌트 ──────────────────────────────────────────────────────────

export default function BacktestResultPanel({ result, symbol, market }) {
  if (!result) return null

  const rawMetrics = result.metrics || result.result?.metrics || result.result_json?.result?.metrics
  const metrics = flattenMetrics(rawMetrics)
  const rawCurve = result.equity_curve || result.result?.equity_curve || result.result_json?.result?.equity_curve
  const equityCurve = normalizeEquityCurve(rawCurve)
  const rawTrades = result.trades || result.result?.trades || result.result_json?.result?.trades || []
  const resultParams = result.params || result.params_json || result.result?.params || result.result_json?.params
  const resolvedSymbol = symbol || result.symbol || result.result_json?.symbol

  // ── OHLCV 별도 조회 ──────────────────────────────────────────────────
  const [ohlcvData, setOhlcvData] = useState(null)

  useEffect(() => {
    if (!resolvedSymbol || !equityCurve.length) { setOhlcvData(null); return }
    const firstDate = (equityCurve[0].date || '').slice(0, 10)
    const lastDate = (equityCurve[equityCurve.length - 1].date || '').slice(0, 10)
    if (!firstDate || !lastDate) return
    const days = Math.ceil((new Date(lastDate) - new Date(firstDate)) / 86400000) + 30
    const period = days > 365 ? `${Math.ceil(days / 365)}y` : `${days}d`

    let cancelled = false
    fetchAdvisoryOhlcv(resolvedSymbol, market || 'KR', '1d', period)
      .then((data) => {
        if (cancelled) return
        const ohlcv = (data.ohlcv || []).filter((d) => d.time >= firstDate && d.time <= lastDate)
        setOhlcvData({ ohlcv, indicators: data.indicators || {} })
      })
      .catch(() => { if (!cancelled) setOhlcvData(null) })
    return () => { cancelled = true }
  }, [resolvedSymbol, market, equityCurve])

  // ── 거래 전처리 ───────────────────────────────────────────────────────
  const processedTrades = useMemo(() => {
    let lastBuyPrice = null
    return rawTrades.map((t) => {
      const isBuy = (t.direction || t.side || '').toLowerCase() === 'buy'
      const date = toKST(t.date || t.entry_date || t.timestamp || t.time || '-')
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

  // ── 보유 구간 (OHLCV time 또는 equity date 기준) ────────────────────────
  const holdingRanges = useMemo(() => {
    // 차트에서 사용할 날짜 소스 결정
    const dateSource = ohlcvData?.ohlcv?.length
      ? ohlcvData.ohlcv.map((d) => d.time)
      : equityCurve.map((e) => (e.date || '').slice(0, 10))
    if (!dateSource.length || !rawTrades.length) return []

    const dateSet = new Set(dateSource)
    const sortedDates = [...dateSource].sort()
    const toChartDate = (rawDate) => {
      const nd = (rawDate || '').slice(0, 10)
      if (!nd) return null
      if (dateSet.has(nd)) return nd
      let closest = sortedDates[0]
      for (const cd of sortedDates) {
        if (cd <= nd) closest = cd
        else break
      }
      return closest
    }

    const ranges = []
    let buyDate = null
    let buyPrice = null
    for (const t of rawTrades) {
      const isBuy = (t.direction || t.side || '').toLowerCase() === 'buy'
      const rawDate = t.date || t.entry_date || t.timestamp || t.time
      if (!rawDate) continue
      if (isBuy) {
        buyDate = toChartDate(rawDate)
        buyPrice = t.price
      } else if (buyDate) {
        const sellDate = toChartDate(rawDate)
        if (sellDate) {
          const isProfit = buyPrice != null && t.price != null ? t.price > buyPrice : null
          ranges.push({ x1: buyDate, x2: sellDate, isProfit })
        }
        buyDate = null
        buyPrice = null
      }
    }
    if (buyDate) {
      ranges.push({ x1: buyDate, x2: sortedDates[sortedDates.length - 1], isProfit: null })
    }
    return ranges
  }, [rawTrades, ohlcvData, equityCurve])

  return (
    <div className="space-y-4">
      <MetricsCard metrics={metrics} />

      {/* 추가 메트릭 */}
      {metrics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
          {metrics.cagr != null && (
            <div className="bg-white rounded-lg border p-3 text-center">
              <div className="text-xs text-gray-500">연평균 수익률</div>
              <div className="text-lg font-semibold">{metrics.cagr?.toFixed(1)}%</div>
              <div className="text-[10px] text-gray-400 mt-0.5">매년 평균 수익 (복리 기준)</div>
            </div>
          )}
          {metrics.sortino_ratio != null && (
            <div className="bg-white rounded-lg border p-3 text-center">
              <div className="text-xs text-gray-500">소르티노 비율</div>
              <div className="text-lg font-semibold">{metrics.sortino_ratio?.toFixed(2)}</div>
              <div className="text-[10px] text-gray-400 mt-0.5">손실만 고려한 위험 대비 수익</div>
            </div>
          )}
          {metrics.profit_factor != null && (
            <div className="bg-white rounded-lg border p-3 text-center">
              <div className="text-xs text-gray-500">손익비</div>
              <div className="text-lg font-semibold">{metrics.profit_factor?.toFixed(2)}</div>
              <div className="text-[10px] text-gray-400 mt-0.5">총 이익 / 총 손실. 1 이상 = 이익 우세</div>
            </div>
          )}
          {metrics.total_trades != null && (
            <div className="bg-white rounded-lg border p-3 text-center">
              <div className="text-xs text-gray-500">총 거래 수</div>
              <div className="text-lg font-semibold">{metrics.total_trades}</div>
              <div className="text-[10px] text-gray-400 mt-0.5">백테스트 기간 내 전체 매매 횟수</div>
            </div>
          )}
        </div>
      )}

      {/* 사용된 파라미터 */}
      {resultParams && Object.keys(resultParams).length > 0 && (
        <div className="bg-gray-50 rounded-lg border p-3">
          <p className="text-xs font-medium text-gray-500 mb-1">사용된 파라미터</p>
          {Array.isArray(resultParams.indicators) ? (
            /* 빌더/커스텀 전략: 지표+조건+리스크 요약 */
            <div className="flex flex-wrap gap-2">
              {resultParams.indicators.map((ind, i) => {
                const id = (ind.id || '').toUpperCase()
                const p = ind.params || {}
                const paramStr = Object.values(p).join(',')
                return (
                  <span key={i} className="text-xs bg-white border rounded px-2 py-0.5">
                    <span className="text-gray-500">지표</span>{' '}
                    <span className="font-mono">{paramStr ? `${id}(${paramStr})` : id}</span>
                  </span>
                )
              })}
              {resultParams.entry_count != null && (
                <span className="text-xs bg-white border rounded px-2 py-0.5">
                  <span className="text-gray-500">진입</span> <span className="font-mono">{resultParams.entry_count}개</span>
                </span>
              )}
              {resultParams.exit_count != null && (
                <span className="text-xs bg-white border rounded px-2 py-0.5">
                  <span className="text-gray-500">청산</span> <span className="font-mono">{resultParams.exit_count}개</span>
                </span>
              )}
              {resultParams.risk?.stop_loss != null && (
                <span className="text-xs bg-white border rounded px-2 py-0.5">
                  <span className="text-gray-500">손절</span> <span className="font-mono">{resultParams.risk.stop_loss}%</span>
                </span>
              )}
              {resultParams.risk?.take_profit != null && (
                <span className="text-xs bg-white border rounded px-2 py-0.5">
                  <span className="text-gray-500">익절</span> <span className="font-mono">{resultParams.risk.take_profit}%</span>
                </span>
              )}
            </div>
          ) : (
            /* 프리셋 전략: 기존 PARAM_KR 매핑 */
            <div className="flex flex-wrap gap-2">
              {Object.entries(resultParams).map(([k, v]) => {
                const kr = PARAM_KR[k]
                const display = typeof v === 'object' ? JSON.stringify(v) : v
                return (
                  <span key={k} className="text-xs bg-white border rounded px-2 py-0.5" title={kr?.desc}>
                    <span className="text-gray-500">{kr?.label || k}</span>{' '}
                    <span className="font-mono">{display}</span>
                  </span>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* 차트: OHLCV 있으면 통합 차트, 없으면 수익률 곡선만 */}
      {equityCurve.length > 0 && (
        <div className="bg-white rounded-lg border p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-3">
            {ohlcvData?.ohlcv?.length ? '주가 + 수익률 곡선' : '수익률 곡선'}
          </h3>
          {ohlcvData?.ohlcv?.length ? (
            <CombinedChart ohlcvData={ohlcvData} equityCurve={equityCurve} holdingRanges={holdingRanges} />
          ) : (
            <EquityOnlyChart equityCurve={equityCurve} holdingRanges={holdingRanges} />
          )}
          {holdingRanges.length > 0 && <RangeLegend />}
        </div>
      )}

      {/* 포지션 요약 */}
      <PositionSummary trades={rawTrades} />

      {/* 연간 수익률 */}
      <AnnualReturnsTable equityCurve={equityCurve} />

      {/* 월별 수익률 히트맵 */}
      <MonthlyReturnsHeatmap equityCurve={equityCurve} />

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
                          t._isBuy ? 'bg-red-50 text-red-700' : 'bg-blue-50 text-blue-700'
                        }`}>
                          {t._isBuy ? 'Buy' : 'Sell'}
                        </span>
                      </td>
                      <td className="px-3 py-1.5 text-right">{t.price != null ? floorKRW(t.price).toLocaleString() : '-'}</td>
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

// ── 보유 구간 범례 ────────────────────────────────────────────────────────

function RangeLegend() {
  return (
    <div className="flex gap-4 text-xs text-gray-500 mt-2 justify-end">
      <span className="flex items-center gap-1">
        <span className="inline-block w-2.5 h-2.5 rounded-sm bg-red-600/20 border border-red-600/40" /> 수익 구간
      </span>
      <span className="flex items-center gap-1">
        <span className="inline-block w-2.5 h-2.5 rounded-sm bg-blue-600/20 border border-blue-600/40" /> 손실 구간
      </span>
      <span className="flex items-center gap-1">
        <span className="inline-block w-2.5 h-2.5 rounded-sm bg-gray-400/20 border border-gray-400/40" /> 보유 중
      </span>
    </div>
  )
}

// ── 수익률 곡선 전용 차트 (OHLCV 없을 때 fallback) ─────────────────────────

function EquityOnlyChart({ equityCurve, holdingRanges }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={equityCurve}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v) => (v || '').slice(5, 10)} />
        <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => floorKRW(v).toLocaleString()} />
        <Tooltip labelFormatter={(v) => v} formatter={(v) => [floorKRW(v).toLocaleString(), '순자산']} />
        <Line type="monotone" dataKey="equity" stroke="#2563eb" dot={false} strokeWidth={1.5} />
        {holdingRanges.map((r, i) => (
          <ReferenceArea key={i} x1={r.x1} x2={r.x2}
            fill={r.isProfit === null ? '#9ca3af' : r.isProfit ? '#dc2626' : '#2563eb'}
            fillOpacity={0.12}
            stroke={r.isProfit === null ? '#9ca3af' : r.isProfit ? '#dc2626' : '#2563eb'}
            strokeOpacity={0.35} strokeWidth={1}
          />
        ))}
      </ComposedChart>
    </ResponsiveContainer>
  )
}

// ── 통합 차트: 캔들 + 수익률 곡선 + 거래량 ─────────────────────────────────

function CombinedChart({ ohlcvData, equityCurve, holdingRanges }) {
  const ohlcv = ohlcvData.ohlcv
  const ma = ohlcvData.indicators?.ma || {}

  // equity_curve를 날짜 Map으로 변환
  const equityMap = useMemo(() => {
    const m = new Map()
    equityCurve.forEach((e) => m.set((e.date || '').slice(0, 10), e.equity))
    return m
  }, [equityCurve])

  // 차트 데이터 병합: OHLCV + equity + MA
  const chartData = useMemo(() =>
    ohlcv.map((d, i) => ({
      time: d.time,
      open: d.open, high: d.high, low: d.low, close: d.close, volume: d.volume,
      equity: equityMap.get((d.time || '').slice(0, 10)) ?? null,
      ma5: (ma.ma5 || [])[i],
      ma20: (ma.ma20 || [])[i],
    })),
  [ohlcv, equityMap, ma])

  // 가격 Y축 도메인
  const priceDomain = useMemo(() => {
    const vals = [
      ...ohlcv.map((d) => d.low).filter((v) => v != null),
      ...ohlcv.map((d) => d.high).filter((v) => v != null),
    ]
    if (!vals.length) return [0, 1]
    const minP = Math.min(...vals)
    const maxP = Math.max(...vals)
    const pad = (maxP - minP) * 0.05
    return [minP - pad, maxP + pad]
  }, [ohlcv])

  const [dMin, dMax] = priceDomain
  const dRange = dMax - dMin

  // 캔들 shape
  const candleShape = useCallback((props) => {
    const { x, width, background, payload } = props
    if (!payload || !background?.height) return null
    const chartTop = background.y
    const chartH = background.height
    if (dRange <= 0 || chartH <= 0) return null
    const toY = (v) => chartTop + chartH * (dMax - v) / dRange
    const { open, high, low, close } = payload
    if (open == null || close == null || high == null || low == null) return null
    const isUp = close >= open
    const color = isUp ? '#ef4444' : '#3b82f6'
    const cx = x + width / 2
    const bw = Math.max(width * 0.65, 1.5)
    const yH = toY(high), yL = toY(low), yO = toY(open), yC = toY(close)
    const yTop = Math.min(yO, yC), yBot = Math.max(yO, yC)
    return (
      <g>
        <line x1={cx} y1={yH} x2={cx} y2={yL} stroke={color} strokeWidth={1} />
        <rect x={cx - bw / 2} y={yTop} width={bw} height={Math.max(yBot - yTop, 1)} fill={color} />
      </g>
    )
  }, [dMax, dRange])

  // 거래량 shape
  const volumeShape = useCallback((props) => {
    const { x, y, width, height: h, payload } = props
    if (!payload) return null
    const isUp = (payload.close ?? 0) >= (payload.open ?? 0)
    return <rect x={x} y={y} width={Math.max(width, 1)} height={Math.max(h, 0)} fill={isUp ? '#ef4444' : '#3b82f6'} opacity={0.6} />
  }, [])

  const xInterval = Math.max(Math.floor(chartData.length / 10), 1)

  return (
    <>
      {/* 메인: 캔들 (좌축) + 수익률 곡선 (우축) + MA + 보유 구간 */}
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis dataKey="time" tick={{ fontSize: 9 }} interval={xInterval}
            tickFormatter={(v) => (v || '').slice(5, 10)} />
          {/* 좌축: 주가 */}
          <YAxis yAxisId="price" domain={priceDomain} tick={{ fontSize: 10 }} width={65}
            tickFormatter={(v) => floorKRW(v).toLocaleString()} />
          {/* 우축: 순자산 */}
          <YAxis yAxisId="equity" orientation="right" tick={{ fontSize: 10 }} width={75}
            tickFormatter={(v) => v >= 1e6 ? `${Math.floor(v / 1e4).toLocaleString()}만` : floorKRW(v).toLocaleString()} />
          <Tooltip content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const d = payload[0]?.payload
            if (!d) return null
            return (
              <div className="bg-white border border-gray-200 rounded shadow p-2 text-xs">
                <p className="text-gray-500 mb-1">{d.time}</p>
                <p>시: {floorKRW(d.open)?.toLocaleString()} 고: {floorKRW(d.high)?.toLocaleString()}</p>
                <p>저: {floorKRW(d.low)?.toLocaleString()}{' '}
                  <span className={d.close >= d.open ? 'text-red-600' : 'text-blue-600'}>
                    종: {floorKRW(d.close)?.toLocaleString()}
                  </span>
                </p>
                {d.equity != null && (
                  <p className="text-emerald-600 mt-1 border-t pt-1">순자산: {floorKRW(d.equity).toLocaleString()}</p>
                )}
              </div>
            )
          }} />
          {/* MA */}
          <Line yAxisId="price" type="monotone" dataKey="ma5" stroke="#f59e0b" strokeWidth={1} dot={false} name="MA5" />
          <Line yAxisId="price" type="monotone" dataKey="ma20" stroke="#8b5cf6" strokeWidth={1} dot={false} name="MA20" />
          {/* 캔들스틱 */}
          <Bar yAxisId="price" dataKey="close" background={{ fill: 'transparent' }}
            shape={candleShape} isAnimationActive={false} />
          {/* 수익률 곡선 (우축) */}
          <Line yAxisId="equity" type="monotone" dataKey="equity" stroke="#10b981"
            strokeWidth={2} dot={false} name="순자산" connectNulls />
          {/* 보유 구간 */}
          {holdingRanges.map((r, i) => (
            <ReferenceArea key={i} x1={r.x1} x2={r.x2} yAxisId="price"
              fill={r.isProfit === null ? '#9ca3af' : r.isProfit ? '#dc2626' : '#2563eb'}
              fillOpacity={0.1}
              stroke={r.isProfit === null ? '#9ca3af' : r.isProfit ? '#dc2626' : '#2563eb'}
              strokeOpacity={0.3} strokeWidth={1}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>

      {/* 거래량 */}
      <ResponsiveContainer width="100%" height={60}>
        <BarChart data={chartData} margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
          <XAxis dataKey="time" hide />
          <YAxis tick={{ fontSize: 9 }} width={65} tickFormatter={(v) => (v / 1000).toFixed(0) + 'K'} />
          <YAxis yAxisId="dummy" orientation="right" width={75} hide />
          <Bar dataKey="volume" shape={volumeShape} isAnimationActive={false} name="거래량" />
        </BarChart>
      </ResponsiveContainer>
    </>
  )
}
