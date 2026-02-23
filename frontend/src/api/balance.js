import { apiFetch } from './client'

export function fetchBalance() {
  return apiFetch('/api/balance')
}
