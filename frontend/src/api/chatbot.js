import { apiFetch } from './client'

export const chatAboutAdvisory = (code, market, reportId, messages) =>
  apiFetch(`/api/advisory/${encodeURIComponent(code)}/chat`, {
    method: 'POST',
    body: JSON.stringify({ market, report_id: reportId, messages }),
  })

export const chatAboutPortfolio = (reportId, messages) =>
  apiFetch('/api/portfolio-advisor/chat', {
    method: 'POST',
    body: JSON.stringify({ report_id: reportId, messages }),
  })
