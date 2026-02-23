import { apiFetch } from './client'

/**
 * @param {Object} params
 * @param {string} [params.date]
 * @param {string} [params.sort_by]
 * @param {number} [params.top]
 * @param {number} [params.per_min]
 * @param {number} [params.per_max]
 * @param {number} [params.pbr_max]
 * @param {number} [params.roe_min]
 * @param {string} [params.market]
 * @param {boolean} [params.include_negative]
 * @param {boolean} [params.earnings_only]
 */
export function fetchStocks(params = {}) {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') qs.set(k, v)
  })
  return apiFetch(`/api/screener/stocks?${qs}`)
}
