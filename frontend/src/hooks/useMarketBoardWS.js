/**
 * 다중심볼 실시간 시세 WebSocket 훅 (/ws/market-board).
 * subscribe(symbols[]) / unsubscribe(symbols[]) 제공.
 * prices 상태: { [symbol]: { price, change_pct, sign } }
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useWebSocket, buildWsUrl } from './useWebSocket'

// 함수 인스턴스는 모듈 스코프에 한 번만 생성(안정 reference) — 매 connect 시점마다 lazy 평가되어
// localStorage 의 갱신된 access_token 을 자동 반영한다(stale-token 무한 백오프 방지).
const buildMarketBoardUrl = () => buildWsUrl('/ws/market-board')

export function useMarketBoardWS() {
  const [prices, setPrices] = useState({})
  const subscribedRef = useRef(new Set())

  // rAF throttle refs
  const pendingRef = useRef(null)
  const rafRef = useRef(null)

  const flushState = useCallback(() => {
    if (!pendingRef.current) return
    const pending = pendingRef.current
    pendingRef.current = null
    rafRef.current = null
    setPrices(prev => ({ ...prev, ...pending }))
  }, [])

  const scheduleFlush = useCallback((updates) => {
    pendingRef.current = pendingRef.current
      ? { ...pendingRef.current, ...updates }
      : updates
    if (!rafRef.current) {
      rafRef.current = requestAnimationFrame(flushState)
    }
  }, [flushState])

  const sfRef = useRef(scheduleFlush)
  sfRef.current = scheduleFlush

  const onMessage = useCallback((msg) => {
    if (msg.type === 'prices' && msg.data) {
      sfRef.current(msg.data)
    }
  }, [])

  const onOpen = useCallback((ws) => {
    // 재연결 시 기존 구독 복원
    const syms = Array.from(subscribedRef.current)
    if (syms.length > 0) {
      ws.send(JSON.stringify({ action: 'subscribe', symbols: syms }))
    }
  }, [])

  const { connected, sendMessage } = useWebSocket(buildMarketBoardUrl, { onMessage, onOpen })

  const subscribe = useCallback((symbols) => {
    if (!symbols || symbols.length === 0) return
    const newSymbols = symbols.filter(s => !subscribedRef.current.has(s))
    if (newSymbols.length === 0) return
    newSymbols.forEach(s => subscribedRef.current.add(s))
    sendMessage({ action: 'subscribe', symbols: newSymbols })
  }, [sendMessage])

  const unsubscribe = useCallback((symbols) => {
    if (!symbols || symbols.length === 0) return
    symbols.forEach(s => subscribedRef.current.delete(s))
    sendMessage({ action: 'unsubscribe', symbols })
  }, [sendMessage])

  // cleanup rAF on unmount
  useEffect(() => {
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [])

  return { prices, connected, subscribe, unsubscribe }
}
