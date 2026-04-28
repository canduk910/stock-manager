import { apiFetch } from './client'

export const fetchMacroIndices = () => apiFetch('/api/macro/indices')
export const fetchMacroNews = () => apiFetch('/api/macro/news')
export const fetchMacroSentiment = () => apiFetch('/api/macro/sentiment')
export const fetchMacroInvestorQuotes = () => apiFetch('/api/macro/investor-quotes')
export const fetchMacroSummary = () => apiFetch('/api/macro/summary')
export const fetchYieldCurve = () => apiFetch('/api/macro/yield-curve')
export const fetchCreditSpread = () => apiFetch('/api/macro/credit-spread')
export const fetchCurrencies = () => apiFetch('/api/macro/currencies')
export const fetchCommodities = () => apiFetch('/api/macro/commodities')
export const fetchSectorHeatmap = () => apiFetch('/api/macro/sector-heatmap')
export const fetchMacroCycle = () => apiFetch('/api/macro/macro-cycle')
