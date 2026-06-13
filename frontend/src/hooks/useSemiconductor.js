import { useCallback, useEffect, useState } from 'react'
import {
  fetchSemiDashboard,
  fetchSemiIndicatorHistory,
  fetchSemiSignals,
  fetchSemiThresholds,
  upsertSemiThreshold,
} from '../api/semiconductor'

export function useSemiconductorDashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchSemiDashboard()
      setData(res)
    } catch (e) {
      setError(e)
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => { reload() }, [reload])
  return { data, loading, error, reload }
}

export function useSemiconductorHistory(name, days = 180) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const reload = useCallback(async () => {
    if (!name) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetchSemiIndicatorHistory(name, days)
      setData(res)
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [name, days])
  useEffect(() => { reload() }, [reload])
  return { data, loading, error, reload }
}

export function useSemiconductorSignals({ indicatorName, limit = 50 } = {}) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchSemiSignals({ indicatorName, limit })
      setData(res)
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [indicatorName, limit])
  useEffect(() => { reload() }, [reload])
  return { data, loading, error, reload }
}

export function useSemiconductorThresholds() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchSemiThresholds()
      setData(res)
    } catch (e) { setError(e) } finally { setLoading(false) }
  }, [])
  useEffect(() => { reload() }, [reload])
  const upsert = useCallback(async (indicatorName, thresholdKey, value, comment) => {
    await upsertSemiThreshold(indicatorName, thresholdKey, value, comment)
    await reload()
  }, [reload])
  return { data, loading, error, reload, upsert }
}
