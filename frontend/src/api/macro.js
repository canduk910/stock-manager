import { apiFetch } from './client'

export const fetchMacroIndices = () => apiFetch('/api/macro/indices')
export const fetchMacroNews = () => apiFetch('/api/macro/news')
export const fetchMacroSentiment = () => apiFetch('/api/macro/sentiment')
export const fetchMacroInvestorQuotes = () => apiFetch('/api/macro/investor-quotes')
export const fetchMacroSummary = () => apiFetch('/api/macro/summary')
