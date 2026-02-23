/**
 * 기본 fetch 래퍼.
 * baseURL: Vite proxy가 /api → localhost:8000으로 중계.
 */
export async function apiFetch(path, options = {}) {
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
