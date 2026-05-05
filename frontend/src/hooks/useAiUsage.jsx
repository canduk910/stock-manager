import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { fetchMyAiUsage } from '../api/admin'
import { useAuth } from './useAuth'

const AiUsageContext = createContext({
  usage: null,
  loading: false,
  refresh: async () => {},
})

export function AiUsageProvider({ children }) {
  const { user } = useAuth()
  const [usage, setUsage] = useState(null)
  const [loading, setLoading] = useState(false)

  const refresh = useCallback(async () => {
    if (!user) {
      setUsage(null)
      return
    }
    setLoading(true)
    try {
      const data = await fetchMyAiUsage()
      setUsage(data)
    } catch (_) {
      // 조용히 무시 — 게이지 단순 표시용
    } finally {
      setLoading(false)
    }
  }, [user])

  // 로그인 상태 변화 시 1회 fetch
  useEffect(() => {
    refresh()
  }, [refresh])

  // 'ai-usage-changed' 이벤트로 자동 갱신
  useEffect(() => {
    const handler = () => { refresh() }
    window.addEventListener('ai-usage-changed', handler)
    return () => window.removeEventListener('ai-usage-changed', handler)
  }, [refresh])

  return (
    <AiUsageContext.Provider value={{ usage, loading, refresh }}>
      {children}
    </AiUsageContext.Provider>
  )
}

export function useAiUsage() {
  return useContext(AiUsageContext)
}
