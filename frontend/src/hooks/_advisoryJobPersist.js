/**
 * AI 자문 진행 중 작업의 클라이언트 영속화.
 *
 * 2026-05-10: fire-and-poll 폴링 중 페이지 이동 → 폴링 hook unmount → 사용자가
 * 다시 페이지 진입 시 이전 작업 미인지 → 중복 클릭 → 백엔드 중복 실행 우려.
 *
 * 해결: localStorage에 active job_id 저장. 마운트 시 복원 → 폴링 재개 +
 * "자문 응답 대기중" 표시 + 버튼 비활성화. 백엔드 변경 0건(기존 in-memory job
 * 1시간 retention + GET /jobs/{job_id} 폴링 인프라 그대로 활용).
 *
 * 한계:
 * - 다중 디바이스/브라우저 동기화 없음 (본인 한 브라우저 케이스 95%+ 커버).
 * - 5분 TTL — 서버는 1시간 보존하지만 사용자 입장에서 5분 초과 시 그만.
 *   (필요 시 TTL_MS 상향 또는 active-jobs 백엔드 API로 확장)
 */

const KEY = (code, market, kind) => `dk_advisory_job:${kind}:${market}:${code}`
const TTL_MS = 5 * 60 * 1000  // 5분

/** 진행 중 작업 저장 (submit 직후 호출). */
export function saveActiveJob(code, market, kind, jobId, message = null) {
  try {
    localStorage.setItem(KEY(code, market, kind), JSON.stringify({
      job_id: jobId,
      kind, code, market,
      started_at_ms: Date.now(),
      expires_at_ms: Date.now() + TTL_MS,
      message,
    }))
  } catch (_) { /* 사파리 시크릿 모드 등 graceful */ }
}

/** 진행 중 작업 조회. 만료 시 자동 정리 후 null 반환. */
export function loadActiveJob(code, market, kind) {
  try {
    const raw = localStorage.getItem(KEY(code, market, kind))
    if (!raw) return null
    const obj = JSON.parse(raw)
    if (Date.now() > (obj.expires_at_ms || 0)) {
      localStorage.removeItem(KEY(code, market, kind))
      return null
    }
    return obj
  } catch (_) {
    return null
  }
}

/** 진행 중 작업 삭제 (완료/실패/취소 시). */
export function clearActiveJob(code, market, kind) {
  try { localStorage.removeItem(KEY(code, market, kind)) } catch (_) { /* graceful */ }
}
