import { apiFetch } from './client'

export const runPipeline = (market = 'KR') =>
  apiFetch(`/api/pipeline/run?market=${market}`, { method: 'POST' })

export const runPipelineSync = (market = 'KR') =>
  apiFetch(`/api/pipeline/run-sync?market=${market}`, { method: 'POST' })

export const fetchPipelineStatus = () => apiFetch('/api/pipeline/status')
