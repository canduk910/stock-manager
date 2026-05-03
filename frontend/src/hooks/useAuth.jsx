import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { login as apiLogin, register as apiRegister, fetchMe, refreshToken } from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      setLoading(false)
      return
    }
    fetchMe()
      .then((data) => setUser(data.user))
      .catch(async () => {
        // access_token 만료 시 refresh 시도
        const rt = localStorage.getItem('refresh_token')
        if (rt) {
          try {
            const res = await refreshToken(rt)
            localStorage.setItem('access_token', res.access_token)
            const me = await fetchMe()
            setUser(me.user)
            return
          } catch {}
        }
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
      })
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (username, password) => {
    const data = await apiLogin(username, password)
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    // login 응답의 user에는 has_kis가 없으므로 /api/auth/me로 재조회
    try {
      const me = await fetchMe()
      setUser(me.user)
      return me.user
    } catch {
      setUser(data.user)
      return data.user
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setUser(null)
  }, [])

  const registerUser = useCallback(async (username, name, password) => {
    const data = await apiRegister(username, name, password)
    return data.user
  }, [])

  const isAdmin = user?.role === 'admin'
  const hasKis = !!user?.has_kis

  const refreshUser = useCallback(async () => {
    try {
      const me = await fetchMe()
      setUser(me.user)
    } catch {}
  }, [])

  return (
    <AuthContext.Provider value={{
      user, loading, login, logout, register: registerUser,
      isAdmin, hasKis, refreshUser,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
