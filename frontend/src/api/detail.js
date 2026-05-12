import { apiFetch } from './client'

export function fetchDetailFinancials(symbol, years = 10) {
  return apiFetch(`/api/detail/financials/${symbol}?years=${years}`)
}

export function fetchDetailValuation(symbol, years = 10) {
  return apiFetch(`/api/detail/valuation/${symbol}?years=${years}`)
}

export function fetchDetailReport(symbol, years = 10) {
  return apiFetch(`/api/detail/report/${symbol}?years=${years}`)
}

/**
 * DetailPage 마운트용 통합 응답 (2026-05-12).
 * 백엔드 ThreadPoolExecutor 병렬 수집 + 부분 실패 보존.
 * 응답: { basic, financials, valuation, forward_estimates, summary, partial_failure }
 *
 * @param {string} symbol 종목 코드
 * @param {string} market "auto"|"KR"|"US" (기본 auto)
 * @param {number} years 1~20 (기본 10)
 */
export function fetchDetailBundle(symbol, market = 'auto', years = 10) {
  const qs = new URLSearchParams({ market, years: String(years) })
  return apiFetch(`/api/detail/${symbol}/bundle?${qs.toString()}`)
}
