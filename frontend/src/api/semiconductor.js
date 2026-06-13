import { apiFetch } from './client'

export const fetchSemiDashboard = () =>
  apiFetch('/api/semiconductor/dashboard')

export const fetchSemiIndicatorHistory = (name, days = 180) =>
  apiFetch(`/api/semiconductor/indicators/${encodeURIComponent(name)}/history?days=${days}`)

export const fetchSemiSignalsRecent = (sinceIso, limit = 50) => {
  const q = new URLSearchParams()
  if (sinceIso) q.set('since', sinceIso)
  q.set('limit', String(limit))
  return apiFetch(`/api/semiconductor/signals/recent?${q.toString()}`)
}

export const fetchSemiSignals = ({ indicatorName, from, to, limit = 50 } = {}) => {
  const q = new URLSearchParams()
  if (indicatorName) q.set('indicator_name', indicatorName)
  if (from) q.set('from', from)
  if (to) q.set('to', to)
  q.set('limit', String(limit))
  return apiFetch(`/api/semiconductor/signals?${q.toString()}`)
}

export const ackSemiSignal = (signalId) =>
  apiFetch(`/api/semiconductor/signals/${signalId}/ack`, { method: 'POST' })

export const fetchSemiThresholds = (indicatorName) => {
  const q = new URLSearchParams()
  if (indicatorName) q.set('indicator_name', indicatorName)
  const tail = q.toString()
  return apiFetch(`/api/semiconductor/thresholds${tail ? `?${tail}` : ''}`)
}

export const upsertSemiThreshold = (indicatorName, thresholdKey, value, comment = null) =>
  apiFetch(
    `/api/semiconductor/thresholds/${encodeURIComponent(indicatorName)}/${encodeURIComponent(thresholdKey)}`,
    {
      method: 'PUT',
      body: JSON.stringify({ value, comment }),
    },
  )

export const adminRefreshSemi = (indicatorName, evaluate = true) => {
  const q = new URLSearchParams()
  if (indicatorName) q.set('indicator_name', indicatorName)
  q.set('evaluate', String(evaluate))
  return apiFetch(`/api/semiconductor/admin/refresh?${q.toString()}`, {
    method: 'POST',
  })
}
