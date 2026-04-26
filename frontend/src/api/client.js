/**
 * 기본 fetch 래퍼.
 * baseURL: Vite proxy가 /api → localhost:8000으로 중계.
 */

let _refreshing = null // 동시 refresh 방지

async function _tryRefresh() {
  const rt = localStorage.getItem('refresh_token')
  if (!rt) return false
  try {
    const res = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: rt }),
    })
    if (!res.ok) return false
    const data = await res.json()
    localStorage.setItem('access_token', data.access_token)
    return true
  } catch {
    return false
  }
}

export async function apiFetch(path, options = {}) {
  const token = localStorage.getItem('access_token')
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(path, { ...options, headers })

  // 401 → refresh 시도
  if (res.status === 401 && token) {
    if (!_refreshing) {
      _refreshing = _tryRefresh().finally(() => { _refreshing = null })
    }
    const ok = await _refreshing
    if (ok) {
      // 새 토큰으로 재시도
      const newToken = localStorage.getItem('access_token')
      headers['Authorization'] = `Bearer ${newToken}`
      const retryRes = await fetch(path, { ...options, headers })
      if (retryRes.ok) return retryRes.json()
      // 재시도도 실패
      let detail = `HTTP ${retryRes.status}`
      try { const b = await retryRes.json(); detail = b.detail || detail } catch {}
      const err = new Error(detail); err.status = retryRes.status; throw err
    }
    // refresh 실패 → 로그아웃
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    window.location.href = '/login'
    return
  }

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
