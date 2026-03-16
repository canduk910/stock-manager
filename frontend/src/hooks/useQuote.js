/**
 * 실시간 호가/체결 WebSocket 훅.
 * - 국내(KR): KIS WS 브릿지 (price + orderbook 메시지)
 * - 해외(US): yfinance 2초 polling (price 메시지만)
 *
 * symbol 변경 시 기존 WS 닫고 재연결 + state 초기화.
 * 비정상 종료 시 지수 백오프 재연결 (500ms → 최대 10초).
 * rAF throttle로 고빈도 리렌더링 방지.
 */
import { useState, useEffect, useRef, useCallback } from 'react'

const EMPTY_STATE = {
  price: null,
  change: null,
  changeRate: null,
  sign: null,
  asks: [],
  bids: [],
  totalAskVolume: null,
  totalBidVolume: null,
  connected: false,
}

export function useQuote(symbol) {
  const [state, setState] = useState(EMPTY_STATE)
  const wsRef = useRef(null)
  const mountedRef = useRef(true)
  const retryRef = useRef(null)
  // rAF throttle refs
  const pendingRef = useRef(null)
  const rafRef = useRef(null)
  // 지수 백오프
  const backoffRef = useRef(500)

  const flushState = useCallback(() => {
    if (!mountedRef.current || !pendingRef.current) return
    const pending = pendingRef.current
    pendingRef.current = null
    rafRef.current = null
    setState(prev => ({ ...prev, ...pending }))
  }, [])

  const scheduleFlush = useCallback((updates) => {
    pendingRef.current = pendingRef.current
      ? { ...pendingRef.current, ...updates }
      : updates
    if (!rafRef.current) {
      rafRef.current = requestAnimationFrame(flushState)
    }
  }, [flushState])

  const connect = useCallback((sym) => {
    if (!sym) {
      setState(EMPTY_STATE)
      return
    }

    // 이전 WS 정리
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close(1000)
      wsRef.current = null
    }
    if (retryRef.current) {
      clearTimeout(retryRef.current)
      retryRef.current = null
    }

    // state 초기화
    if (mountedRef.current) {
      setState(EMPTY_STATE)
      pendingRef.current = null
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current)
        rafRef.current = null
      }
    }

    // WebSocket URL 생성 (개발: Vite proxy /ws, 프로덕션: 같은 호스트)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/ws/quote/${sym}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      if (!mountedRef.current) return
      backoffRef.current = 500 // 연결 성공 시 백오프 리셋
      setState((prev) => ({ ...prev, connected: true }))
    }

    ws.onmessage = (event) => {
      if (!mountedRef.current) return
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'price') {
          scheduleFlush({
            price: msg.price,
            change: msg.change,
            changeRate: msg.change_rate,
            sign: msg.sign,
          })
        } else if (msg.type === 'orderbook') {
          scheduleFlush({
            asks: msg.asks || [],
            bids: msg.bids || [],
            totalAskVolume: msg.total_ask_volume,
            totalBidVolume: msg.total_bid_volume,
          })
        } else if (msg.type === 'disconnected') {
          // 서버가 KIS WS 끊김 알림
          setState((prev) => ({ ...prev, connected: false }))
        }
        // ping은 무시
      } catch (e) {
        // JSON 파싱 오류 무시
      }
    }

    ws.onerror = () => {
      if (!mountedRef.current) return
      setState((prev) => ({ ...prev, connected: false }))
    }

    ws.onclose = (event) => {
      if (!mountedRef.current) return
      setState((prev) => ({ ...prev, connected: false }))
      // 비정상 종료 시 지수 백오프 재연결
      if (event.code !== 1000 && mountedRef.current) {
        const delay = backoffRef.current
        backoffRef.current = Math.min(delay * 2, 10000)
        retryRef.current = setTimeout(() => {
          if (mountedRef.current) connect(sym)
        }, delay)
      }
    }
  }, [scheduleFlush])

  // 탭 복귀 시 WS 끊겼으면 즉시 재연결
  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === 'visible' && symbol) {
        const ws = wsRef.current
        if (!ws || ws.readyState === WebSocket.CLOSED || ws.readyState === WebSocket.CLOSING) {
          backoffRef.current = 500
          connect(symbol)
        }
      }
    }
    document.addEventListener('visibilitychange', handleVisibility)
    return () => document.removeEventListener('visibilitychange', handleVisibility)
  }, [symbol, connect])

  useEffect(() => {
    mountedRef.current = true
    connect(symbol)
    return () => {
      mountedRef.current = false
      if (retryRef.current) clearTimeout(retryRef.current)
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.close(1000)
        wsRef.current = null
      }
    }
  }, [symbol, connect])

  return state
}
