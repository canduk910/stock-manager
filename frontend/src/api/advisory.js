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

// ── AI 리포트 히스토리 목록 ────────────────────────────────────────────────
export const fetchReportHistory = (code, market = 'KR', limit = 20) =>
  apiFetch(`/api/advisory/${encodeURIComponent(code)}/reports?market=${market}&limit=${limit}`)

// ── 특정 ID 리포트 조회 ────────────────────────────────────────────────────
export const fetchReportById = (code, reportId, market = 'KR') =>
  apiFetch(`/api/advisory/${encodeURIComponent(code)}/reports/${reportId}?market=${market}`)

// ── 최신 AI 리포트 조회 ────────────────────────────────────────────────────
export const fetchReport = (code, market = 'KR') =>
  apiFetch(`/api/advisory/${encodeURIComponent(code)}/report?market=${market}`)

// ── 리서치 데이터 수집 (입력정보 획득) ──────────────────────────────────────
export const collectResearchData = (code, market = 'KR', name = null) => {
  const q = name ? `&name=${encodeURIComponent(name)}` : ''
  return apiFetch(`/api/advisory/${encodeURIComponent(code)}/research?market=${market}${q}`, {
    method: 'POST',
  })
}

// ── OHLCV 타임프레임별 조회 ────────────────────────────────────────────────
export const fetchAdvisoryOhlcv = (code, market = 'KR', interval = '15m', period = '60d') =>
  apiFetch(`/api/advisory/${encodeURIComponent(code)}/ohlcv?market=${market}&interval=${interval}&period=${period}`)

// ── 증권사별 목표가 + 리포트 ──────────────────────────────────────────────
export const fetchAnalystReports = (code, market = 'KR') =>
  apiFetch(`/api/advisory/${encodeURIComponent(code)}/analyst-reports?market=${market}`)
