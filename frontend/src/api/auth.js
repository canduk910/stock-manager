/**
 * 인증 API 모듈.
 */

// auth API는 apiFetch를 사용하지 않음 (401 리다이렉트 루프 방지)
async function authFetch(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {}
    const err = new Error(detail)
    err.status = res.status
    throw err
  }
  return res.json()
}

export const login = (username, password) =>
  authFetch('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })

export const register = (username, name, password) =>
  authFetch('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, name, password }),
  })

export const refreshToken = (refresh_token) =>
  authFetch('/api/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token }),
  })

export const changePassword = (old_password, new_password) => {
  const token = localStorage.getItem('access_token')
  return authFetch('/api/auth/change-password', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ old_password, new_password }),
  })
}

export const fetchMe = () => {
  const token = localStorage.getItem('access_token')
  return authFetch('/api/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  })
}
