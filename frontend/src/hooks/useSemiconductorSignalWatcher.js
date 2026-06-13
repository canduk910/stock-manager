/**
 * 반도체 신호 60s 폴링 + 변경 감지 → notify().
 *
 * - 60초 간격 `GET /api/semiconductor/signals/recent?since=<ISO>`
 * - localStorage `semi:last_seen_signal_id` 저장 (재방문 시 중복 방지)
 * - 새 신호 토스트 (level별 색상: WARNING=warning, ALERT/RED=error, INFO/GREEN/YELLOW=info)
 * - WS 미사용 (KIS WS slot 회피)
 *
 * App.jsx 안쪽(ProtectedRoute 안) 1회만 마운트.
 */

import { useEffect, useRef } from 'react'
import { fetchSemiSignalsRecent } from '../api/semiconductor'

const POLL_INTERVAL_MS = 60_000
const STORAGE_KEY_TS = 'semi:last_seen_signal_ts'

function _levelToToastType(level) {
  if (level === 'RED' || level === 'ALERT') return 'error'
  if (level === 'WARNING' || level === 'YELLOW') return 'warning'
  return 'info'
}

export function useSemiconductorSignalWatcher(notify) {
  const lastSeenRef = useRef(localStorage.getItem(STORAGE_KEY_TS) || null)
  const timerRef = useRef(null)

  useEffect(() => {
    if (typeof notify !== 'function') return
    let cancelled = false

    async function tick() {
      try {
        const since = lastSeenRef.current
        const res = await fetchSemiSignalsRecent(since, 50)
        if (cancelled) return
        const signals = res?.signals || []
        if (signals.length === 0) return
        // 신호는 desc 정렬 → asc 처리하여 토스트 순서 보장
        const ordered = signals.slice().reverse()
        for (const s of ordered) {
          const ts = s.fired_at
          // since 비교는 초 단위 ISO, 이미 backend가 strict > 비교
          if (!lastSeenRef.current || ts > lastSeenRef.current) {
            const msg = s.message || `[반도체] ${s.indicator_name} → ${s.level}`
            const t = _levelToToastType(s.level)
            const duration = (s.level === 'RED' || s.level === 'ALERT') ? 12_000 : 8_000
            notify(msg, t, duration)
            lastSeenRef.current = ts
            localStorage.setItem(STORAGE_KEY_TS, ts)
          }
        }
      } catch (e) {
        // 인증/네트워크 오류는 silent — 다른 매크로 섹션과 동일 정책
        // 단, 콘솔에는 1회 로그
        if (!cancelled) console.warn('[useSemiconductorSignalWatcher] 폴링 실패:', e?.message || e)
      }
    }

    // 첫 호출 — 초기 last_seen 부재 시 현재 시각으로 셋팅하여 과거 신호 폭주 방지.
    if (!lastSeenRef.current) {
      const now = new Date().toISOString()
      lastSeenRef.current = now
      localStorage.setItem(STORAGE_KEY_TS, now)
    } else {
      tick()  // 즉시 1회
    }
    timerRef.current = setInterval(tick, POLL_INTERVAL_MS)
    return () => {
      cancelled = true
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [notify])
}
