/**
 * useMarketClock — KST 시계 기반 KR 거래소 4구간 자동 판정 훅.
 *
 * 4구간 (사용자 결정 2026-05-08):
 *   08:00~09:00 → NXT 단독 (프리오픈)
 *   09:00~15:30 → UN  통합(KRX+NXT)
 *   15:30~15:40 → KRX 단독 (동시호가/마감)
 *   15:40~20:00 → NXT 단독 (시간외)
 *   그 외       → CLOSED (장 마감)
 *
 * 휴장 판정:
 *   1차: 주말 (토/일)
 *   2차: 공휴일은 v2에서 KIS API CTCA0903R 또는 백엔드 휴일 헬퍼 연동(현재 v1은 미반영)
 *
 * NOTE: /ws/market-status (장운영정보 WS) override 분기는 2026-05-12 폐지됨.
 *       KIS WS slot 잠식(자동매매 41건 제한) 회수를 위해 시계 기반 폴백만 사용.
 *       정밀 trigger(휴장/장개시/장종료)는 사용자가 필요시 새로고침으로 해결.
 *
 * 폴링: 1분 setInterval로 phase 재계산.
 *
 * 반환:
 *   { exchange, label, isHoliday, isClosed, phase }
 *   - exchange: 'UN' | 'KRX' | 'NXT' (CLOSED 시 마지막 phase 보존)
 *   - label: 사용자 표시용 한글 라벨
 *   - isHoliday: 휴장 여부 (주말/공휴일/장 마감)
 *   - isClosed: 거래 시간 외 여부
 *   - phase: 4구간 키 'NXT_PRE' | 'UN' | 'KRX_CLOSE' | 'NXT_AFTER' | 'CLOSED'
 */
import { useEffect, useState } from 'react'

// KST wall clock을 브라우저 timezone과 무관하게 추출 (Intl.DateTimeFormat 기준).
// 2026-05-18 수정: 기존 `now.getTimezoneOffset()` 기반 변환은 KST 브라우저에서
//   `getTimezoneOffset() = -540` 부호 합산으로 시간을 9시간 뒤로 돌려 평일 장중을
//   휴장으로 잘못 분류 (예: 14:50 → 05:50 → CLOSED). Intl.DateTimeFormat은 DST/locale 무관.
const KST_PARTS_FMT = new Intl.DateTimeFormat('en-US', {
  timeZone: 'Asia/Seoul',
  weekday: 'short',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

function kstParts(now) {
  const parts = KST_PARTS_FMT.formatToParts(now)
  const weekday = parts.find((p) => p.type === 'weekday')?.value // 'Sun'~'Sat'
  let hour = parseInt(parts.find((p) => p.type === 'hour')?.value, 10)
  const minute = parseInt(parts.find((p) => p.type === 'minute')?.value, 10)
  if (hour === 24) hour = 0 // en-US hour12:false → 자정 24 가능성 정규화
  return { weekday, minutes: hour * 60 + minute }
}

const WEEKEND_DAYS = new Set(['Sat', 'Sun'])

export function resolvePhaseByClock(now = new Date()) {
  const { weekday, minutes } = kstParts(now)
  if (WEEKEND_DAYS.has(weekday)) {
    return { phase: 'CLOSED', exchange: 'UN', label: '휴장 (주말)', isHoliday: true, isClosed: true }
  }
  if (minutes >= 480 && minutes < 540) {
    return { phase: 'NXT_PRE', exchange: 'NXT', label: 'NXT 프리오픈 08:00~09:00', isHoliday: false, isClosed: false }
  }
  if (minutes >= 540 && minutes < 930) {
    return { phase: 'UN', exchange: 'UN', label: '통합(KRX+NXT) 09:00~15:30', isHoliday: false, isClosed: false }
  }
  if (minutes >= 930 && minutes < 940) {
    return { phase: 'KRX_CLOSE', exchange: 'KRX', label: 'KRX 동시호가/마감 15:30~15:40', isHoliday: false, isClosed: false }
  }
  if (minutes >= 940 && minutes < 1200) {
    return { phase: 'NXT_AFTER', exchange: 'NXT', label: 'NXT 시간외 15:40~20:00', isHoliday: false, isClosed: false }
  }
  return { phase: 'CLOSED', exchange: 'UN', label: '장 마감', isHoliday: false, isClosed: true }
}

export function useMarketClock() {
  const [phase, setPhase] = useState(() => resolvePhaseByClock(new Date()))

  // 1분 주기 시계 기반 재계산
  useEffect(() => {
    const id = setInterval(() => {
      setPhase(resolvePhaseByClock(new Date()))
    }, 60 * 1000)
    return () => clearInterval(id)
  }, [])

  return phase
}
