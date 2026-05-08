/**
 * useUsMarketClock — 미국 거래세션 4구간 자동 판정 훅 (REQ-FE-09 + REQ-FE-02).
 *
 * 4구간 (ET 기준, DST 자동 처리):
 *   - 프리(pre):     04:00 ~ 09:30
 *   - 정규(regular): 09:30 ~ 16:00
 *   - 애프터(after): 16:00 ~ 20:00
 *   - 휴장(closed):  나머지 + 주말(토/일) + NYSE/NASDAQ 정규 공휴일(REQ-FE-02)
 *
 * - 1분 setInterval 폴링
 * - DST 자동 — Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York' })
 * - 단축 거래일(Black Friday 13:00 ET 조기마감 등)은 v3 (본 phase 제외)
 *
 * 반환:
 *   { phase: 'pre'|'regular'|'after'|'closed',
 *     label: '🟢 정규' 등,
 *     etTime: 'HH:MM',
 *     kstTime: 'HH:MM' }
 *
 * 순수 함수 export:
 *   resolveUsPhaseByClock(now: Date) — 단위 테스트용
 *   isUsHoliday(etDateStr) — ET 기준 'YYYY-MM-DD' 문자열 → 공휴일 여부
 */
import { useState, useEffect } from 'react'

const PHASE_LABELS = {
  pre: '🟡 프리',
  regular: '🟢 정규',
  after: '🔵 애프터',
  closed: '⚪ 휴장',
}

/**
 * NYSE/NASDAQ 정규 공휴일 (ET 기준 'YYYY-MM-DD').
 * 출처: NYSE 공식 캘린더 https://www.nyse.com/markets/hours-calendars
 *
 * 휴장 종목:
 *   - New Year's Day (1/1, 주말이면 다음 평일/전 금요일 observed)
 *   - MLK Day (1월 셋째 월요일)
 *   - Presidents Day (2월 셋째 월요일)
 *   - Good Friday (부활절 직전 금요일)
 *   - Memorial Day (5월 마지막 월요일)
 *   - Juneteenth (6/19, observed)
 *   - Independence Day (7/4, observed)
 *   - Labor Day (9월 첫째 월요일)
 *   - Thanksgiving (11월 넷째 목요일)
 *   - Christmas Day (12/25, observed)
 *
 * 단축 거래일은 v3 (본 phase 제외) — 주석으로만 표시.
 */
export const US_HOLIDAYS_ET = new Set([
  // ── 2026 ────────────────────────────────────────────
  '2026-01-01', // New Year's Day (Thu)
  '2026-01-19', // MLK Day (3rd Mon Jan)
  '2026-02-16', // Presidents Day (3rd Mon Feb)
  '2026-04-03', // Good Friday
  '2026-05-25', // Memorial Day (last Mon May)
  '2026-06-19', // Juneteenth (Fri)
  '2026-07-03', // Independence Day observed (7/4=Sat → Fri)
  '2026-09-07', // Labor Day (1st Mon Sep)
  '2026-11-26', // Thanksgiving (4th Thu Nov)
  '2026-12-25', // Christmas Day (Fri)

  // ── 2027 ────────────────────────────────────────────
  '2027-01-01', // New Year's Day (Fri)
  '2027-01-18', // MLK Day
  '2027-02-15', // Presidents Day
  '2027-03-26', // Good Friday
  '2027-05-31', // Memorial Day
  '2027-06-18', // Juneteenth observed (6/19=Sat → Fri)
  '2027-07-05', // Independence Day observed (7/4=Sun → Mon)
  '2027-09-06', // Labor Day
  '2027-11-25', // Thanksgiving
  '2027-12-24', // Christmas observed (12/25=Sat → Fri)

  // ── 2028 ────────────────────────────────────────────
  '2028-01-03', // New Year's Day observed (1/1=Sat → Mon)
  '2028-01-17', // MLK Day
  '2028-02-21', // Presidents Day
  '2028-04-14', // Good Friday
  '2028-05-29', // Memorial Day
  '2028-06-19', // Juneteenth (Mon)
  '2028-07-04', // Independence Day (Tue)
  '2028-09-04', // Labor Day
  '2028-11-23', // Thanksgiving
  '2028-12-25', // Christmas (Mon)

  // 단축 거래일(13:00 ET 조기 마감)은 v3 — 본 phase에서는 정규 휴장만 처리.
  // (예: Black Friday, 7/3 또는 12/24 일부 — 본 phase에서는 정규 거래일로 처리)
])

/**
 * 한글 라벨 매핑 — closed 사유 표기용.
 */
const HOLIDAY_LABELS_KO = {
  '01-01': "New Year's Day",
  // MLK/Presidents/Memorial/Labor/Thanksgiving 등은 매년 변동되므로 월/일 매핑이 부정확.
  // 단순화: 월별 대표 라벨만 — 정밀 라벨은 v3.
}

/**
 * ET 기준 'YYYY-MM-DD' 문자열을 추출.
 *
 * @param {Date} now
 * @returns {string} 'YYYY-MM-DD'
 */
function _etDateStr(now) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/New_York',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(now)
  const get = (t) => parts.find((p) => p.type === t)?.value
  return `${get('year')}-${get('month')}-${get('day')}`
}

/**
 * ET 기준 날짜가 NYSE/NASDAQ 정규 공휴일인지 검사.
 *
 * @param {Date|string} input - Date 또는 'YYYY-MM-DD'
 * @returns {boolean}
 */
export function isUsHoliday(input) {
  const ds = input instanceof Date ? _etDateStr(input) : String(input || '')
  return US_HOLIDAYS_ET.has(ds)
}

/**
 * 주어진 시각의 미국 거래세션을 판정.
 *
 * @param {Date} now - 현재 시각
 * @returns {{phase: string, etTime: string, kstTime: string}} 거래세션 정보
 */
export function resolveUsPhaseByClock(now = new Date()) {
  // ET 시각 추출 (DST 자동)
  const etParts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York',
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(now)

  const get = (type) => etParts.find((p) => p.type === type)?.value
  const weekday = get('weekday') // 'Sun', 'Mon' ...
  let hour = parseInt(get('hour') ?? '0', 10)
  const minute = parseInt(get('minute') ?? '0', 10)
  // Intl 'en-US' 24h hour 'hour12: false'에서 가끔 24를 반환하는 케이스 보정
  if (hour === 24) hour = 0

  const etTime = `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`

  // KST 시각 (UTC+9 고정)
  const kstParts = new Intl.DateTimeFormat('ko-KR', {
    timeZone: 'Asia/Seoul',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(now)
  const kstHour = parseInt(kstParts.find((p) => p.type === 'hour')?.value ?? '0', 10)
  const kstMinute = parseInt(kstParts.find((p) => p.type === 'minute')?.value ?? '0', 10)
  const kstTime = `${String(kstHour === 24 ? 0 : kstHour).padStart(2, '0')}:${String(kstMinute).padStart(2, '0')}`

  // 주말 → closed
  if (weekday === 'Sat' || weekday === 'Sun') {
    return { phase: 'closed', etTime, kstTime, holiday: null }
  }

  // 공휴일 → closed (REQ-FE-02)
  const etDate = _etDateStr(now)
  if (US_HOLIDAYS_ET.has(etDate)) {
    return { phase: 'closed', etTime, kstTime, holiday: etDate }
  }

  const minutesOfDay = hour * 60 + minute

  // 04:00=240 / 09:30=570 / 16:00=960 / 20:00=1200
  if (minutesOfDay >= 240 && minutesOfDay < 570) {
    return { phase: 'pre', etTime, kstTime }
  }
  if (minutesOfDay >= 570 && minutesOfDay < 960) {
    return { phase: 'regular', etTime, kstTime }
  }
  if (minutesOfDay >= 960 && minutesOfDay < 1200) {
    return { phase: 'after', etTime, kstTime }
  }
  return { phase: 'closed', etTime, kstTime }
}

function _buildLabel(r) {
  const base = `${PHASE_LABELS[r.phase]} (ET ${r.etTime} / KST ${r.kstTime})`
  if (r.phase === 'closed' && r.holiday) {
    return `${PHASE_LABELS.closed} 휴장 (${r.holiday})`
  }
  return base
}

export function useUsMarketClock() {
  const [info, setInfo] = useState(() => {
    const r = resolveUsPhaseByClock(new Date())
    return { ...r, label: _buildLabel(r) }
  })

  useEffect(() => {
    const tick = () => {
      const r = resolveUsPhaseByClock(new Date())
      setInfo({
        phase: r.phase,
        etTime: r.etTime,
        kstTime: r.kstTime,
        holiday: r.holiday ?? null,
        label: _buildLabel(r),
      })
    }
    // 즉시 1회 + 60초 폴링
    tick()
    const id = setInterval(tick, 60_000)
    return () => clearInterval(id)
  }, [])

  return info
}
