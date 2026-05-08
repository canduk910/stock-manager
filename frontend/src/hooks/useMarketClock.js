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
 *   3차: /ws/market-status 메시지 도착 시 override (정밀 trigger)
 *
 * 폴링: 1분 setInterval로 phase 재계산.
 *   phase 변경 시 React state 갱신 → 의존하는 훅(useQuote)의 buildUrl 함수 인스턴스가
 *   갱신되어 자동 재연결.
 *
 * 반환:
 *   { exchange, label, isHoliday, isClosed, phase }
 *   - exchange: 'UN' | 'KRX' | 'NXT' (CLOSED 시 마지막 phase 보존)
 *   - label: 사용자 표시용 한글 라벨
 *   - isHoliday: 휴장 여부 (주말/공휴일/장 마감)
 *   - isClosed: 거래 시간 외 여부
 *   - phase: 4구간 키 'NXT_PRE' | 'UN' | 'KRX_CLOSE' | 'NXT_AFTER' | 'CLOSED'
 */
import { useEffect, useState, useRef } from 'react'
import { useWebSocket, buildWsUrl } from './useWebSocket'

const KST_OFFSET_MIN = 9 * 60

function toKstDate(now) {
  const utcMs = now.getTime() + now.getTimezoneOffset() * 60000
  return new Date(utcMs + KST_OFFSET_MIN * 60000)
}

export function resolvePhaseByClock(now = new Date()) {
  const kst = toKstDate(now)
  const day = kst.getUTCDay() // toKstDate가 UTC 시각으로 KST 시간을 채워둠
  const minutes = kst.getUTCHours() * 60 + kst.getUTCMinutes()
  if (day === 0 || day === 6) {
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

const buildMarketStatusUrl = () => buildWsUrl('/ws/market-status')

export function useMarketClock() {
  const [phase, setPhase] = useState(() => resolvePhaseByClock(new Date()))

  // 1분 주기 시계 기반 재계산
  useEffect(() => {
    const id = setInterval(() => {
      setPhase(resolvePhaseByClock(new Date()))
    }, 60 * 1000)
    return () => clearInterval(id)
  }, [])

  // /ws/market-status 메시지 override
  // KIS 응답이 오면 백엔드가 정밀 phase 를 알려준다(휴장/장개시/장종료 등).
  const phaseRef = useRef(phase)
  phaseRef.current = phase

  const onMessage = (msg) => {
    if (msg && msg.type === 'market_status' && msg.exchange) {
      // 백엔드 메시지는 거래소(UN/KRX/NXT)만 보낸다 — 시계 기반 phase 라벨은 유지하되
      // exchange 만 갱신. 이로써 실제 KIS 가 알려주는 거래소 분기를 우선시한다.
      setPhase(prev => prev.exchange === msg.exchange ? prev : { ...prev, exchange: msg.exchange })
    }
  }

  useWebSocket(buildMarketStatusUrl, { onMessage })

  return phase
}
