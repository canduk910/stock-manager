/**
 * 최소 fetch 래퍼 (macro_lite 패키지 단독 동작용).
 * 토큰/refresh 로직 없음. 호스트 프로젝트에 인증 래퍼가 있다면
 * ../api/macro.js 상단의 `import { apiFetch } from './client'` 한 줄을
 * 호스트 프로젝트의 apiFetch import로 교체한다.
 */
export async function apiFetch(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers }

  const res = await fetch(path, { ...options, headers })

  if (!res.ok) {
    let detail = res.statusText || `HTTP ${res.status}`
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
