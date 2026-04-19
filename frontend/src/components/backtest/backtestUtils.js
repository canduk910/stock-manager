/**
 * 백테스트 결과 분석 유틸리티 — equity_curve / trades 에서 파생 지표 계산.
 */

/**
 * 연간 수익률 계산.
 * @param {Array<{date: string, equity: number}>} equityCurve
 * @returns {Array<{year: number, return_pct: number, start_equity: number, end_equity: number}>}
 */
export function computeAnnualReturns(equityCurve) {
  if (!equityCurve?.length) return []

  const byYear = new Map()
  for (const e of equityCurve) {
    const y = parseInt((e.date || '').slice(0, 4), 10)
    if (isNaN(y)) continue
    if (!byYear.has(y)) byYear.set(y, { first: e.equity, last: e.equity })
    else byYear.get(y).last = e.equity
  }

  return [...byYear.entries()]
    .sort(([a], [b]) => a - b)
    .map(([year, { first, last }]) => ({
      year,
      return_pct: first ? ((last - first) / first) * 100 : 0,
      start_equity: first,
      end_equity: last,
    }))
}

/**
 * 월별 수익률 계산.
 * @param {Array<{date: string, equity: number}>} equityCurve
 * @returns {{ data: Array<{year: number, month: number, return_pct: number}>, years: number[] }}
 */
export function computeMonthlyReturns(equityCurve) {
  if (!equityCurve?.length) return { data: [], years: [] }

  const byYM = new Map()
  for (const e of equityCurve) {
    const d = (e.date || '').slice(0, 7) // YYYY-MM
    if (d.length < 7) continue
    const y = parseInt(d.slice(0, 4), 10)
    const m = parseInt(d.slice(5, 7), 10)
    const key = `${y}-${m}`
    if (!byYM.has(key)) byYM.set(key, { y, m, first: e.equity, last: e.equity })
    else byYM.get(key).last = e.equity
  }

  const data = []
  const yearSet = new Set()
  for (const { y, m, first, last } of byYM.values()) {
    yearSet.add(y)
    data.push({
      year: y,
      month: m,
      return_pct: first ? ((last - first) / first) * 100 : 0,
    })
  }

  return { data, years: [...yearSet].sort((a, b) => a - b) }
}

/**
 * 포지션 요약 통계 계산.
 * @param {Array} trades — raw trade records
 * @returns {{
 *   avgHoldingDays: number|null,
 *   avgWinPct: number|null,
 *   avgLossPct: number|null,
 *   maxConsecutiveWins: number,
 *   maxConsecutiveLosses: number,
 *   winCount: number,
 *   lossCount: number,
 *   longestHoldingDays: number|null,
 *   shortestHoldingDays: number|null,
 * }}
 */
export function computePositionSummary(trades) {
  if (!trades?.length) return null

  // Buy/Sell 페어링
  const pairs = []
  let pendingBuy = null

  for (const t of trades) {
    const side = (t.direction || t.side || '').toLowerCase()
    const rawDate = t.date || t.entry_date || t.timestamp || t.time || ''
    const dateStr = rawDate.slice(0, 10)

    if (side === 'buy') {
      pendingBuy = { date: dateStr, price: t.price }
    } else if (side === 'sell' && pendingBuy) {
      const profitPct = t.profit_pct ?? t.return_pct ??
        (pendingBuy.price && t.price ? ((t.price - pendingBuy.price) / pendingBuy.price) * 100 : null)

      let holdingDays = null
      if (pendingBuy.date && dateStr) {
        const diff = new Date(dateStr) - new Date(pendingBuy.date)
        if (!isNaN(diff)) holdingDays = Math.max(Math.round(diff / 86400000), 1)
      }

      pairs.push({ profitPct, holdingDays })
      pendingBuy = null
    }
  }

  if (!pairs.length) return null

  // 통계 계산
  const wins = pairs.filter((p) => p.profitPct != null && p.profitPct > 0)
  const losses = pairs.filter((p) => p.profitPct != null && p.profitPct <= 0)
  const holdingDays = pairs.map((p) => p.holdingDays).filter((d) => d != null)

  const avg = (arr) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null

  // 최대 연속 승/패
  let maxConsWins = 0, maxConsLosses = 0, consWins = 0, consLosses = 0
  for (const p of pairs) {
    if (p.profitPct != null && p.profitPct > 0) {
      consWins++
      consLosses = 0
      maxConsWins = Math.max(maxConsWins, consWins)
    } else {
      consLosses++
      consWins = 0
      maxConsLosses = Math.max(maxConsLosses, consLosses)
    }
  }

  return {
    avgHoldingDays: avg(holdingDays),
    avgWinPct: avg(wins.map((w) => w.profitPct)),
    avgLossPct: avg(losses.map((l) => l.profitPct)),
    maxConsecutiveWins: maxConsWins,
    maxConsecutiveLosses: maxConsLosses,
    winCount: wins.length,
    lossCount: losses.length,
    longestHoldingDays: holdingDays.length ? Math.max(...holdingDays) : null,
    shortestHoldingDays: holdingDays.length ? Math.min(...holdingDays) : null,
  }
}
