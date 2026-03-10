import { apiFetch } from './client'

// ── 자문종목 목록 ──────────────────────────────────────────────────────────
export const fetchAdvisoryStocks = () =>
  apiFetch('/api/advisory')

// ── 종목 추가 ──────────────────────────────────────────────────────────────
export const addAdvisoryStock = (code, market = 'KR', memo = '') =>
  apiFetch('/api/advisory', {
    method: 'POST',
    body: JSON.stringify({ code, market, memo }),
  })

// ── 종목 삭제 ──────────────────────────────────────────────────────────────
export const removeAdvisoryStock = (code, market = 'KR') =>
  apiFetch(`/api/advisory/${encodeURIComponent(code)}?market=${market}`, {
    method: 'DELETE',
  })

// ── 데이터 새로고침 ────────────────────────────────────────────────────────
export const refreshAdvisoryData = (code, market = 'KR', name = null) => {
  const q = name ? `&name=${encodeURIComponent(name)}` : ''
  return apiFetch(`/api/advisory/${encodeURIComponent(code)}/refresh?market=${market}${q}`, {
    method: 'POST',
  })
}

// ── 분석 데이터 조회 ───────────────────────────────────────────────────────
export const fetchAdvisoryData = (code, market = 'KR') =>
  apiFetch(`/api/advisory/${encodeURIComponent(code)}/data?market=${market}`)

// ── AI 리포트 생성 ─────────────────────────────────────────────────────────
export const generateReport = (code, market = 'KR') =>
  apiFetch(`/api/advisory/${encodeURIComponent(code)}/analyze?market=${market}`, {
    method: 'POST',
  })

// ── 최신 AI 리포트 조회 ────────────────────────────────────────────────────
export const fetchReport = (code, market = 'KR') =>
  apiFetch(`/api/advisory/${encodeURIComponent(code)}/report?market=${market}`)

// ── OHLCV 타임프레임별 조회 ────────────────────────────────────────────────
export const fetchAdvisoryOhlcv = (code, market = 'KR', interval = '15m', period = '60d') =>
  apiFetch(`/api/advisory/${encodeURIComponent(code)}/ohlcv?market=${market}&interval=${interval}&period=${period}`)
