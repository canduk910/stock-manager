import { apiFetch } from './client'

/**
 * 공시 조회 API.
 *
 * @param {string} startDate - YYYY-MM-DD
 * @param {string} endDate - YYYY-MM-DD
 * @param {string} market - 'KR' | 'US'
 * @param {string[]} categories - DART pblntf_ty 코드 배열 (예: ['A','B','D','F']).
 *                                미지정/빈 배열 → A(정기공시)만 (백워드 호환). KR 한정, US는 무시.
 */
export function fetchFilings(startDate, endDate, market = 'KR', categories = null) {
  const params = new URLSearchParams()
  if (startDate) params.set('start_date', startDate)
  if (endDate) params.set('end_date', endDate)
  if (market) params.set('market', market)
  if (Array.isArray(categories) && categories.length > 0) {
    params.set('categories', categories.join(','))
  }
  const qs = params.toString() ? `?${params.toString()}` : ''
  return apiFetch(`/api/earnings/filings${qs}`)
}
