import { useState, useCallback } from 'react'

/**
 * 비동기 데이터 fetch 공통 상태 관리.
 * run(asyncFn) 호출 시 loading/error/data를 자동 관리한다.
 * 에러 시 항상 throw — 호출측에서 .catch(() => {}) 로 삼킴 선택.
 */
export function useAsyncState(initialData = null) {
  const [data, setData] = useState(initialData)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const run = useCallback(async (fn) => {
    setLoading(true)
    setError(null)
    try {
      const result = await fn()
      setData(result)
      return result
    } catch (e) {
      setError(e.message)
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  return { data, setData, loading, error, setError, run }
}
