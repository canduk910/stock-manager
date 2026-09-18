// 통합 시 이 import 한 줄을 호스트 프로젝트의 apiFetch 로 교체
import { apiFetch } from './client'

export const fetchYieldCurve = () => apiFetch('/api/macro/yield-curve')
export const fetchCreditSpread = () => apiFetch('/api/macro/credit-spread')
export const fetchCurrencies = () => apiFetch('/api/macro/currencies')
export const fetchCommodities = () => apiFetch('/api/macro/commodities')
export const fetchMacroCycle = () => apiFetch('/api/macro/macro-cycle')
