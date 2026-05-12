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

// ── 데이터 새로고침 (동기 — 백워드 호환, 30초+ 시 504 위험) ───────────────
export const refreshAdvisoryData = (code, market = 'KR', name = null) => {
  const q = name ? `&name=${encodeURIComponent(name)}` : ''
  return apiFetch(`/api/advisory/${encodeURIComponent(code)}/refresh?market=${market}${q}`, {
    method: 'POST',
  })
}

// ── 데이터 새로고침 (비동기 — fire-and-poll, 504 회피) ────────────────────
// 즉시 {job_id, status:"running", message} 반환. 결과는 pollAdvisoryJob() 폴링.
export const refreshAdvisoryDataAsync = (code, market = 'KR', name = null) => {
  const q = name ? `&name=${encodeURIComponent(name)}` : ''
  return apiFetch(`/api/advisory/${encodeURIComponent(code)}/refresh?market=${market}&async=true${q}`, {
    method: 'POST',
  })
}

// ── 분석 데이터 조회 ───────────────────────────────────────────────────────
export const fetchAdvisoryData = (code, market = 'KR') =>
  apiFetch(`/api/advisory/${encodeURIComponent(code)}/data?market=${market}`)

// ── AI 리포트 생성 (동기 — 백워드 호환, 10초+ 시 504 위험) ────────────────
// userComment(2026-05-07): 사용자 가설을 백엔드에 전달, 양면 평가(user_commentary_evaluation) 트리거
export const generateReport = (code, market = 'KR', userComment = null) => {
  const cmt = (userComment || '').trim()
  const body = cmt ? { user_comment: cmt } : null
  return apiFetch(`/api/advisory/${encodeURIComponent(code)}/analyze?market=${market}`, {
    method: 'POST',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
}

// ── AI 리포트 생성 (비동기 — fire-and-poll) ────────────────────────────────
export const generateReportAsync = (code, market = 'KR', userComment = null) => {
  const cmt = (userComment || '').trim()
  const body = cmt ? { user_comment: cmt } : null
  return apiFetch(`/api/advisory/${encodeURIComponent(code)}/analyze?market=${market}&async=true`, {
    method: 'POST',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
}

// ── fire-and-poll 작업 폴링 ────────────────────────────────────────────────
// 응답: {status:"running"|"completed"|"failed", elapsed_seconds, message, result|error_message}
export const pollAdvisoryJob = (jobId) =>
  apiFetch(`/api/advisory/jobs/${encodeURIComponent(jobId)}`)

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

// ── 종목 수급(개인/외국인/기관) (REQ-SUPPLY-ROUTER-02) ─────────────────────
export const fetchStockSupplyDemand = (code, days = 30) =>
  apiFetch(`/api/advisory/${encodeURIComponent(code)}/supply-demand?days=${days}`)
