/**
 * 실시간 호가/체결 WebSocket 훅.
 * - 국내(KR): KIS WS 브릿지 (price + orderbook 메시지)
 * - 해외(US): yfinance 2초 polling (price 메시지만)
 *
 * symbol 변경 시 기존 WS 닫고 재연결 + state 초기화.
 * 비정상 종료 시 지수 백오프 재연결 (500ms → 최대 10초).
 * rAF throttle로 고빈도 리렌더링 방지.
 */
import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { useWebSocket, buildWsUrl } from './useWebSocket'

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

  // rAF throttle refs
  const pendingRef = useRef(null)
  const rafRef = useRef(null)

  const flushState = useCallback(() => {
    if (!pendingRef.current) return
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

  // scheduleFlush를 ref로 잡아 onMessage 안정성 보장
  const sfRef = useRef(scheduleFlush)
  sfRef.current = scheduleFlush

  const onMessage = useCallback((msg) => {
    if (msg.type === 'price') {
      sfRef.current({
        price: msg.price,
        change: msg.change,
        changeRate: msg.change_rate,
        sign: msg.sign,
      })
    } else if (msg.type === 'orderbook') {
      sfRef.current({
        asks: msg.asks || [],
        bids: msg.bids || [],
        totalAskVolume: msg.total_ask_volume,
        totalBidVolume: msg.total_bid_volume,
      })
    } else if (msg.type === 'disconnected') {
      setState(prev => ({ ...prev, connected: false }))
    }
  }, [])

  const url = useMemo(
    () => symbol ? buildWsUrl(`/ws/quote/${symbol}`) : null,
    [symbol]
  )

  const { connected } = useWebSocket(url, { onMessage })

  // symbol 변경 시 state 초기화
  useEffect(() => {
    setState(EMPTY_STATE)
    pendingRef.current = null
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
  }, [symbol])

  // cleanup rAF on unmount
  useEffect(() => {
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [])

  return { ...state, connected }
}
